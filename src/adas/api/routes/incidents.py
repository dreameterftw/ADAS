"""Simulation clock and active-incident API routes."""

import math
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import networkx as nx

from adas.app_state import add_request_record, get_graph, get_request_log, get_simulation_state, init_demo_scenario
from adas.simulation.incidents import Incident
from adas.simulation.network import get_node_latlon


router = APIRouter()


class IncomingRequest(BaseModel):
	caller: str = Field(default="Hospital intake", min_length=1, max_length=100)
	location: str = Field(min_length=2, max_length=160)
	severity: int = Field(ge=1, le=5)
	latitude: float = Field(ge=-90, le=90)
	longitude: float = Field(ge=-180, le=180)
	notes: str = Field(default="", max_length=500)


@router.get("/requests")
def get_requests() -> list[dict[str, object]]:
	return get_request_log()


@router.post("/requests", status_code=201)
def create_request(request: IncomingRequest) -> dict[str, object]:
	graph = get_graph()
	state = get_simulation_state()
	nodes = [node for node, data in graph.nodes(data=True) if "x" in data and "y" in data]
	if not nodes:
		raise HTTPException(status_code=503, detail="The response map has no geocoded road nodes.")
	node = min(nodes, key=lambda item: (graph.nodes[item]["y"] - request.latitude) ** 2 + (graph.nodes[item]["x"] - request.longitude) ** 2)
	incident_id = max((incident.id for incident in [*state.pending_incidents, *state.active_incidents]), default=0) + 1
	incident = Incident(incident_id, node, request.severity, state.current_time)
	state.active_incidents.append(incident)
	record = {
		"request_id": str(uuid4()),
		"incident_id": incident_id,
		"received_at": datetime.now(timezone.utc).isoformat(),
		"caller": request.caller,
		"location": request.location,
		"severity": request.severity,
		"latitude": float(graph.nodes[node]["y"]),
		"longitude": float(graph.nodes[node]["x"]),
		"notes": request.notes,
		"source": "operator_entry",
		"status": "received",
	}
	add_request_record(record)
	return record


@router.delete("/requests", status_code=204)
def clear_requests() -> None:
	from adas.app_state import clear_request_log
	clear_request_log()


@router.post("/demo/scenario")
def load_demo_scenario() -> dict[str, str]:
	init_demo_scenario()
	return {"status": "demo scenario loaded"}


@router.get("/active")
def get_active_incidents() -> list[dict[str, int | float]]:
	state = get_simulation_state()
	graph = get_graph()
	result = []
	for incident in state.active_incidents:
		latitude, longitude = get_node_latlon(graph, incident.location_node)
		result.append({
			"id": incident.id,
			"location_node": incident.location_node,
			"severity": incident.severity,
			"timestamp": incident.timestamp,
			"lat": latitude,
			"lon": longitude,
		})
	return result


@router.post("/{incident_id}/resolve")
def resolve_incident(
	incident_id: int,
	ambulance_id: int = Query(ge=0),
) -> dict[str, int | str]:
	"""Resolve an active incident and release its assigned ambulance."""
	state = get_simulation_state()
	try:
		state.resolve_incident(incident_id, ambulance_id)
	except ValueError as error:
		raise HTTPException(status_code=409, detail=str(error)) from error
	return {
		"incident_id": incident_id,
		"ambulance_id": ambulance_id,
		"status": "resolved",
	}


@router.post("/tick")
def advance_simulation(
	dt_seconds: float = Query(default=30.0, ge=0),
) -> dict[str, float | int]:
	if not math.isfinite(dt_seconds):
		raise HTTPException(status_code=422, detail="dt_seconds must be finite")
	state = get_simulation_state()
	newly_active = state.tick(dt_seconds)
	return {
		"current_time": state.current_time,
		"newly_active_count": len(newly_active),
	}
