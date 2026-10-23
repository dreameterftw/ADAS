"""Optional server-side adapters for FHIR hospital and ambulance AVL data."""

from __future__ import annotations

import math
import os
from typing import Any

import httpx
import networkx as nx

from adas.app_state import get_graph, get_simulation_state
from adas.hospitals.matching import Hospital
from adas.simulation.incidents import Ambulance

FHIR_AVAILABLE_BEDS_EXTENSION = "https://adas.example/fhir/StructureDefinition/available-beds"
FHIR_TOTAL_BEDS_EXTENSION = "https://adas.example/fhir/StructureDefinition/total-beds"
_provider_ambulance_ids: dict[str, int] = {}


def _token_headers(variable: str) -> dict[str, str]:
	token = os.getenv(variable, "").strip()
	return {"Authorization": f"Bearer {token}"} if token else {}


def _nearest_node(graph: nx.MultiDiGraph, latitude: float, longitude: float) -> int:
	if not graph.nodes:
		raise ValueError("The active road network has no nodes.")
	return min(
		graph.nodes,
		key=lambda node: (graph.nodes[node].get("y", 1000) - latitude) ** 2
		+ (graph.nodes[node].get("x", 1000) - longitude) ** 2,
	)


def _bundle_resources(payload: dict[str, Any]) -> list[dict[str, Any]]:
	entries = payload.get("entry", [])
	if not isinstance(entries, list):
		return []
	return [
		entry["resource"]
		for entry in entries
		if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
	]


def _extension_number(resource: dict[str, Any], extension_url: str) -> int | None:
	if not extension_url:
		return None
	for extension in resource.get("extension", []):
		if not isinstance(extension, dict) or extension.get("url") != extension_url:
			continue
		for key, value in extension.items():
			if key.startswith("value") and isinstance(value, (int, float)) and math.isfinite(value):
				return max(0, int(value))
	return None


def import_hospital_fhir_bundle(payload: dict[str, Any]) -> dict[str, Any]:
	"""Import active Location and HealthcareService resources from an R4 Bundle."""
	if not isinstance(payload, dict) or payload.get("resourceType") != "Bundle":
		raise ValueError("Expected a FHIR R4 Bundle resource.")
	resources = _bundle_resources(payload)
	locations = [resource for resource in resources if resource.get("resourceType") == "Location"]
	services = [
		resource for resource in resources
		if resource.get("resourceType") == "HealthcareService" and resource.get("active", True) is not False
	]
	if not locations:
		raise ValueError("The bundle must include at least one Location resource.")
	return _apply_hospital_resources(
		locations,
		services,
		os.getenv("FHIR_BED_COUNT_EXTENSION_URL", "").strip() or FHIR_AVAILABLE_BEDS_EXTENSION,
		os.getenv("FHIR_TOTAL_BED_COUNT_EXTENSION_URL", "").strip() or FHIR_TOTAL_BEDS_EXTENSION,
		status="imported",
	)


def _apply_hospital_resources(
	locations: list[dict[str, Any]],
	services: list[dict[str, Any]],
	available_extension_url: str,
	total_extension_url: str,
	*,
	status: str,
) -> dict[str, Any]:
	services_by_location: dict[str, list[dict[str, Any]]] = {}
	for service in services:
		for reference in service.get("location", []):
			if isinstance(reference, dict):
				ref = str(reference.get("reference", "")).split("/")[-1]
				if ref:
					services_by_location.setdefault(ref, []).append(service)

	graph = get_graph()
	updated: list[Hospital] = []
	for location in locations:
		if location.get("status", "active") != "active":
			continue
		position = location.get("position") or {}
		latitude, longitude = position.get("latitude"), position.get("longitude")
		resource_id = str(location.get("id", ""))
		if not resource_id or not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
			continue
		if not math.isfinite(latitude) or not math.isfinite(longitude) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
			continue
		available = _extension_number(location, available_extension_url) or 0
		matching_services = services_by_location.get(resource_id, [])
		specialties = {
			tag
			for service in matching_services
			for item in service.get("specialty", [])
			if isinstance(item, dict)
			for coding in item.get("coding", [])
			if isinstance(coding, dict)
			for term in (str(coding.get("code", "")), str(coding.get("display", "")), str(item.get("text", "")))
			for tag in (
				{"trauma"} if "trauma" in term.lower()
				else {"cardiac"} if any(word in term.lower() for word in ("cardiac", "cardio", "heart"))
				else {"general"} if any(word in term.lower() for word in ("general", "emergency", "acute"))
				else set()
			)
		}
		total = max(available, _extension_number(location, total_extension_url) or available)
		updated.append(Hospital(f"FHIR-{resource_id}", _nearest_node(graph, float(latitude), float(longitude)), specialties, available, total))
	if not updated:
		raise ValueError("No active Location resources had a valid ID and WGS84 position; no hospitals were changed.")
	from adas import app_state
	app_state._hospitals = updated
	return {
		"status": status,
		"updated": len(updated),
		"services": len(services),
		"beds_source": "configured_fhir_extension" if available_extension_url else "unavailable_without_extension",
		"capacity_note": "Bed counts are only used when the configured capacity extension is present.",
	}


def sync_hospitals() -> dict[str, Any]:
	base_url = os.getenv("HOSPITAL_FHIR_BASE_URL", "").strip().rstrip("/")
	if not base_url:
		return {"status": "not_configured", "updated": 0}
	timeout = httpx.Timeout(10.0, connect=4.0)
	with httpx.Client(timeout=timeout, headers=_token_headers("HOSPITAL_FHIR_BEARER_TOKEN"), follow_redirects=False) as client:
		location_response = client.get(f"{base_url}/Location", params={"_count": "200", "status": "active"})
		location_response.raise_for_status()
		service_response = client.get(f"{base_url}/HealthcareService", params={"_count": "200", "active": "true"})
		service_response.raise_for_status()
	locations = [resource for resource in _bundle_resources(location_response.json()) if resource.get("resourceType") == "Location"]
	services = [
		resource for resource in _bundle_resources(service_response.json())
		if resource.get("resourceType") == "HealthcareService" and resource.get("active", True) is not False
	]
	return _apply_hospital_resources(
		locations,
		services,
		os.getenv("FHIR_BED_COUNT_EXTENSION_URL", "").strip(),
		os.getenv("FHIR_TOTAL_BED_COUNT_EXTENSION_URL", "").strip(),
		status="synced",
	)


def apply_ambulance_positions(payload: Any) -> dict[str, Any]:
	"""Normalize an AVL JSON feed and replace the current ambulance positions."""
	if isinstance(payload, list):
		items = payload
	elif isinstance(payload, dict):
		items = next((payload.get(key) for key in ("ambulances", "vehicles", "items", "value") if isinstance(payload.get(key), list)), None)
	else:
		items = None
	if items is None:
		raise ValueError("Expected an array of ambulances or an object containing an ambulances array.")
	graph = get_graph()
	state = get_simulation_state()
	current_by_id = {unit.id: unit for unit in state.ambulances}
	connected_units: list[Ambulance] = []
	seen_provider_ids: set[str] = set()
	used_local_ids: set[int] = set()
	reserved_numeric_ids: set[int] = set()
	for candidate in items:
		if isinstance(candidate, dict):
			try:
				reserved_numeric_ids.add(int(candidate.get("id", candidate.get("vehicleId"))))
			except (TypeError, ValueError, OverflowError):
				pass
	next_custom_id = max([0, *current_by_id, *reserved_numeric_ids]) + 1
	for item in items:
		if not isinstance(item, dict):
			continue
		unit_id = item.get("id", item.get("vehicleId"))
		latitude = item.get("latitude", item.get("lat"))
		longitude = item.get("longitude", item.get("lon", item.get("lng")))
		if unit_id is None or latitude is None or longitude is None:
			continue
		try:
			latitude, longitude = float(latitude), float(longitude)
			numeric_id = int(unit_id)
		except (TypeError, ValueError, OverflowError):
			numeric_id = None
			try:
				latitude, longitude = float(latitude), float(longitude)
			except (TypeError, ValueError, OverflowError):
				continue
		if not math.isfinite(latitude) or not math.isfinite(longitude) or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
			continue
		provider_key = str(unit_id)
		if provider_key in seen_provider_ids:
			continue
		seen_provider_ids.add(provider_key)
		local_id = numeric_id
		if local_id is None:
			local_id = _provider_ambulance_ids.get(provider_key)
			if local_id is None or local_id in reserved_numeric_ids or local_id in used_local_ids:
				while next_custom_id in reserved_numeric_ids or next_custom_id in used_local_ids:
					next_custom_id += 1
				local_id = next_custom_id
				_provider_ambulance_ids[provider_key] = local_id
				next_custom_id += 1
		elif local_id in used_local_ids:
			continue
		used_local_ids.add(local_id)
		status = str(item.get("status", "available")).lower()
		connected_units.append(Ambulance(local_id, _nearest_node(graph, latitude, longitude), status in {"available", "idle", "ready", "active"}))
	if items and not connected_units:
		raise ValueError("No valid ambulance positions were found; the current fleet was left unchanged.")
	state.ambulances = connected_units
	state.assignments.clear()
	return {"status": "ingested", "updated": len(connected_units), "received": len(items)}


def sync_ambulances() -> dict[str, Any]:
	feed_url = os.getenv("AMBULANCE_FEED_URL", "").strip()
	if not feed_url:
		return {"status": "not_configured", "updated": 0}
	response = httpx.get(
		feed_url,
		timeout=httpx.Timeout(10.0, connect=4.0),
		headers=_token_headers("AMBULANCE_FEED_BEARER_TOKEN"),
		follow_redirects=False,
	)
	response.raise_for_status()
	return apply_ambulance_positions(response.json()) | {"status": "synced"}
