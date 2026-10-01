"""Simulation clock and active-incident API routes."""

import math

from fastapi import APIRouter, HTTPException, Query

from adas.app_state import get_simulation_state


router = APIRouter()


@router.get("/active")
def get_active_incidents() -> list[dict[str, int | float]]:
	state = get_simulation_state()
	return [
		{
			"id": incident.id,
			"location_node": incident.location_node,
			"severity": incident.severity,
			"timestamp": incident.timestamp,
		}
		for incident in state.active_incidents
	]


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
