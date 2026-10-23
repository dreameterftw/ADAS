"""Operator controls and integration readiness for the response service."""

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from adas.app_state import get_traffic_mode, init_showcase_scenario, set_traffic_mode
from adas.integrations import sync_ambulances, sync_hospitals

router = APIRouter()


class TrafficRequest(BaseModel):
	mode: str


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


@router.get("/integrations")
def integration_status() -> dict[str, object]:
	"""Report configured connectors without implying a live feed exists."""
	fhir_url = os.getenv("HOSPITAL_FHIR_BASE_URL", "").strip()
	ambulance_url = os.getenv("AMBULANCE_FEED_URL", "").strip()
	return {
		"hospital": {
			"standard": "FHIR R4 Location / HealthcareService",
			"configured": bool(fhir_url),
			"status": "configured" if fhir_url else "awaiting_provider_endpoint",
			"bed_capacity_extension_configured": bool(os.getenv("FHIR_BED_COUNT_EXTENSION_URL", "").strip()),
		},
		"ambulance": {
			"standard": "AVL adapter (SensorThings or provider JSON)",
			"configured": bool(ambulance_url),
			"status": "configured" if ambulance_url else "awaiting_provider_endpoint",
		},
		"traffic": {
			"provider": "Google Routes API" if os.getenv("GOOGLE_MAPS_API_KEY", "").strip() else "scenario traffic model",
			"configured": bool(os.getenv("GOOGLE_MAPS_API_KEY", "").strip()),
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
	if any(isinstance(result, dict) and result.get("updated", 0) for result in results.values()):
		from adas.api.routes.assignments import replan_assignments
		replan_assignments()
	return {"results": results}
