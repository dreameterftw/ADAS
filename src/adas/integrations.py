"""Optional server-side adapters for hospital directories and ambulance AVL feeds.

The AVL adapter accepts the normalized provider-neutral JSON contract documented
in docs/integrations.md. Credentials are read only from backend environment vars.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import networkx as nx

from adas.app_state import get_graph, get_hospitals, get_simulation_state
from adas.hospitals.matching import Hospital
from adas.simulation.incidents import Ambulance

_provider_ambulance_ids: dict[str, int] = {}


def _token_headers(variable: str) -> dict[str, str]:
	token = os.getenv(variable, "").strip()
	return {"Authorization": f"Bearer {token}"} if token else {}


def _nearest_node(graph: nx.MultiDiGraph, latitude: float, longitude: float) -> int:
	return min(
		graph.nodes,
		key=lambda node: (graph.nodes[node].get("y", 1000) - latitude) ** 2
		+ (graph.nodes[node].get("x", 1000) - longitude) ** 2,
	)


def _bundle_resources(payload: dict[str, Any]) -> list[dict[str, Any]]:
	return [
		entry.get("resource", {})
		for entry in payload.get("entry", [])
		if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
	]


def _extension_number(resource: dict[str, Any], extension_url: str) -> int | None:
	if not extension_url:
		return None
	for extension in resource.get("extension", []):
		if extension.get("url") == extension_url:
			for key, value in extension.items():
				if key.startswith("value") and isinstance(value, (int, float)):
					return max(0, int(value))
	return None


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
	locations = _bundle_resources(location_response.json())
	services = _bundle_resources(service_response.json())
	services_by_location: dict[str, list[dict[str, Any]]] = {}
	for service in services:
		for reference in service.get("location", []):
			ref = reference.get("reference", "").split("/")[-1]
			services_by_location.setdefault(ref, []).append(service)
	graph = get_graph()
	extension_url = os.getenv("FHIR_BED_COUNT_EXTENSION_URL", "").strip()
	updated: list[Hospital] = []
	for location in locations:
		position = location.get("position") or {}
		latitude, longitude = position.get("latitude"), position.get("longitude")
		if latitude is None or longitude is None:
			continue
		resource_id = str(location.get("id", ""))
		if not resource_id:
			continue
		available = _extension_number(location, extension_url)
		if available is None:
			available = 0
		matching_services = services_by_location.get(resource_id, [])
		specialties = {
			tag
			for service in matching_services
			for item in service.get("specialty", [])
			for coding in item.get("coding", [])
			for term in (coding.get("code", ""), coding.get("display", ""), item.get("text", ""))
			for tag in ({"trauma"} if "trauma" in term.lower() else {"cardiac"} if any(word in term.lower() for word in ("cardiac", "cardio", "heart")) else {"general"} if any(word in term.lower() for word in ("general", "emergency", "acute")) else set())
		}
		total_url = os.getenv("FHIR_TOTAL_BED_COUNT_EXTENSION_URL", "").strip()
		total = max(available, _extension_number(location, total_url) or available)
		updated.append(Hospital(f"FHIR-{resource_id}", _nearest_node(graph, float(latitude), float(longitude)), specialties, available, total))
	if updated:
		from adas import app_state
		app_state._hospitals = updated
	return {"status": "synced", "updated": len(updated), "services": len(services), "beds_source": "provider_extension" if extension_url else "unavailable_without_extension"}


def sync_ambulances() -> dict[str, Any]:
	feed_url = os.getenv("AMBULANCE_FEED_URL", "").strip()
	if not feed_url:
		return {"status": "not_configured", "updated": 0}
	response = httpx.get(feed_url, timeout=httpx.Timeout(10.0, connect=4.0), headers=_token_headers("AMBULANCE_FEED_BEARER_TOKEN"), follow_redirects=False)
	response.raise_for_status()
	payload = response.json()
	items = payload if isinstance(payload, list) else next((payload.get(key) for key in ("ambulances", "vehicles", "items", "value") if isinstance(payload.get(key), list)), [])
	graph = get_graph()
	state = get_simulation_state()
	current_by_id = {unit.id: unit for unit in state.ambulances}
	connected_units: list[Ambulance] = []
	updated = 0
	for item in items:
		if not isinstance(item, dict):
			continue
		unit_id = item.get("id", item.get("vehicleId"))
		latitude = item.get("latitude", item.get("lat"))
		longitude = item.get("longitude", item.get("lon", item.get("lng")))
		if unit_id is None or latitude is None or longitude is None:
			continue
		if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
			continue
		provider_key = str(unit_id)
		try:
			local_id = int(unit_id)
		except (TypeError, ValueError):
			local_id = _provider_ambulance_ids.setdefault(provider_key, max([0, *current_by_id]) + len(_provider_ambulance_ids) + 1)
		status = str(item.get("status", "available")).lower()
		connected_units.append(Ambulance(local_id, _nearest_node(graph, float(latitude), float(longitude)), status in {"available", "idle", "ready", "active"}))
		updated += 1
	if updated:
		state.ambulances = connected_units
		state.assignments.clear()
	return {"status": "synced", "updated": updated, "received": len(items)}
