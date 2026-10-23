"""Operator controls and integration readiness for the response service."""

import os
import secrets
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException, Query
from pydantic import BaseModel

from adas.app_state import get_graph, get_traffic_mode, init_showcase_scenario, set_road_closure, set_traffic_mode
from adas.integrations import apply_ambulance_positions, import_hospital_fhir_bundle, sync_ambulances, sync_hospitals

router = APIRouter()


class TrafficRequest(BaseModel):
	mode: str


class RoadClosureRequest(BaseModel):
	source: int
	target: int
	closed: bool = True


@router.post("/scenario/showcase")
def load_showcase_scenario() -> dict[str, object]:
	init_showcase_scenario()
	return {"status": "loaded", "incidents": 4, "ambulances": 6, "traffic_mode": get_traffic_mode()}


@router.put("/traffic")
def update_traffic(request: TrafficRequest) -> dict[str, str]:
	try:
		set_traffic_mode(request.mode)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	return {"status": "updated", "traffic_mode": get_traffic_mode()}


@router.get("/closures")
def road_closures() -> dict[str, object]:
	graph = get_graph()
	segments: dict[tuple[int, int], dict[str, object]] = {}
	for source, target, _key, data in graph.edges(keys=True, data=True):
		pair = (min(int(source), int(target)), max(int(source), int(target)))
		start, end = graph.nodes[pair[0]], graph.nodes[pair[1]]
		start_position = {"lat": float(start["y"]), "lon": float(start["x"])} if "x" in start and "y" in start else None
		end_position = {"lat": float(end["y"]), "lon": float(end["x"])} if "x" in end and "y" in end else None
		row = segments.setdefault(pair, {
			"source": pair[0], "target": pair[1], "major": False, "closed": False,
			"source_position": start_position, "target_position": end_position,
		})
		row["major"] = bool(row["major"] or data.get("major_corridor"))
		row["closed"] = bool(row["closed"] or data.get("closed"))
	choices = sorted(segments.values(), key=lambda row: (not row["closed"], not row["major"], row["source"], row["target"]))
	return {"segments": choices[:100], "closed_count": sum(1 for row in choices if row["closed"])}


@router.put("/closures")
def update_road_closure(request: RoadClosureRequest, replan: bool = Query(default=True)) -> dict[str, object]:
	try:
		set_road_closure(request.source, request.target, request.closed)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	if replan:
		from adas.api.routes.assignments import replan_assignments
		replan_assignments()
	return {"status": "updated", "source": request.source, "target": request.target, "closed": request.closed, "replanned": replan}


@router.post("/hospitals/fhir-bundle")
def import_fhir_hospital_bundle(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
	try:
		result = import_hospital_fhir_bundle(payload)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	from adas.api.routes.assignments import replan_assignments
	replan_assignments()
	return result


@router.post("/ambulances/positions")
def receive_ambulance_positions(
	payload: Any = Body(...),
	authorization: str | None = Header(default=None),
) -> dict[str, Any]:
	secret = os.getenv("AMBULANCE_WEBHOOK_BEARER_TOKEN", "").strip()
	if not secret:
		raise HTTPException(status_code=503, detail="Ambulance position webhook is disabled until its bearer token is configured.")
	if not authorization or not secrets.compare_digest(authorization, f"Bearer {secret}"):
		raise HTTPException(status_code=401, detail="Valid ambulance webhook bearer token required.", headers={"WWW-Authenticate": "Bearer"})
	try:
		result = apply_ambulance_positions(payload)
	except ValueError as error:
		raise HTTPException(status_code=422, detail=str(error)) from error
	from adas.api.routes.assignments import replan_assignments
	replan_assignments()
	return result


@router.get("/integrations")
def integration_status() -> dict[str, object]:
	"""Report configured connectors without implying a live feed exists."""
	fhir_url = os.getenv("HOSPITAL_FHIR_BASE_URL", "").strip()
	ambulance_url = os.getenv("AMBULANCE_FEED_URL", "").strip()
	ambulance_webhook = os.getenv("AMBULANCE_WEBHOOK_BEARER_TOKEN", "").strip()
	return {
		"hospital": {
			"standard": "FHIR R4 Location / HealthcareService",
			"configured": bool(fhir_url),
			"bundle_import_supported": True,
			"status": "configured" if fhir_url else "awaiting_provider_endpoint",
			"bed_capacity_extension_configured": bool(os.getenv("FHIR_BED_COUNT_EXTENSION_URL", "").strip()),
		},
		"ambulance": {
			"standard": "AVL JSON feed or authenticated GPS webhook",
			"configured": bool(ambulance_url or ambulance_webhook),
			"feed_configured": bool(ambulance_url),
			"webhook_configured": bool(ambulance_webhook),
			"webhook_path": "/operations/ambulances/positions",
			"status": "configured" if ambulance_url or ambulance_webhook else "awaiting_provider_endpoint",
		},
		"traffic": {
			"provider": "scenario traffic model",
			"configured": False,
			"status": "scenario_only",
			"live_provider_adapter_available": False,
			"road_closure_controls_available": True,
			"mode": get_traffic_mode(),
		},
	}


@router.post("/sync")
def sync_integrations() -> dict[str, object]:
	results: dict[str, object] = {}
	for name, sync in (("hospital", sync_hospitals), ("ambulance", sync_ambulances)):
		try:
			results[name] = sync()
		except Exception as error:
			results[name] = {"status": "error", "message": f"{error.__class__.__name__}: provider sync failed"}
	if any(isinstance(result, dict) and result.get("status") == "synced" and "updated" in result for result in results.values()):
		from adas.api.routes.assignments import replan_assignments
		replan_assignments()
	return {"results": results}
