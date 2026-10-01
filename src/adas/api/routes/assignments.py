"""Live dispatch-assignment API routes."""

from fastapi import APIRouter

from adas.app_state import get_orchestrator, get_simulation_state


router = APIRouter()


@router.post("/replan")
def replan_assignments() -> list[dict[str, int | float]]:
	state = get_simulation_state()
	orchestrator = get_orchestrator()
	assignments = orchestrator.replan(state)
	return [
		{
			"incident_id": assignment.incident_id,
			"ambulance_id": assignment.ambulance_id,
			"travel_time_sec": assignment.travel_time_sec,
		}
		for assignment in assignments
	]
