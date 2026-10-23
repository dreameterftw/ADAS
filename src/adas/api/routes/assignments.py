"""Live dispatch-assignment API routes."""

from typing import Any

import networkx as nx
from fastapi import APIRouter

from adas.app_state import get_graph, get_hospitals, get_orchestrator, get_simulation_state
from adas.baselines.closest_idle import ClosestIdleDispatch
from adas.hospitals.matching import best_hospital_for_incident
from adas.simulation.network import get_node_latlon, get_route_latlon


router = APIRouter()


@router.post("/replan")
def replan_assignments() -> list[dict[str, Any]]:
	state = get_simulation_state()
	orchestrator = get_orchestrator()
	graph = get_graph()
	try:
		assignments = orchestrator.replan(state)
		solver_method = orchestrator.last_solver_methods
		fallback_reasons = orchestrator.last_fallback_reasons
	except Exception as error:
		# Keep dispatch available when the optional quantum runtime is unavailable.
		assignments = ClosestIdleDispatch().solve(graph, state.active_incidents, state.ambulances)
		state.assignments = {assignment.incident_id: assignment for assignment in assignments}
		assigned_ambulances = {assignment.ambulance_id for assignment in assignments}
		for ambulance in state.ambulances:
			if ambulance.id in assigned_ambulances:
				ambulance.available = False
		solver_method = {}
		fallback_reasons = {assignment.incident_id: f"Quantum planner unavailable: {error.__class__.__name__}" for assignment in assignments}
	incidents_by_id = {incident.id: incident for incident in state.active_incidents}
	ambulances_by_id = {ambulance.id: ambulance for ambulance in state.ambulances}
	hospitals = get_hospitals()
	response = []
	for assignment in assignments:
		incident = incidents_by_id.get(assignment.incident_id)
		ambulance = ambulances_by_id.get(assignment.ambulance_id)
		hospital, match_reason = best_hospital_for_incident(
			graph,
			incident.location_node if incident is not None else -1,
			incident.severity if incident is not None else 0,
			hospitals,
		)
		route = []
		if incident is not None and ambulance is not None:
			try:
				path = nx.shortest_path(
					graph,
					ambulance.current_node,
					incident.location_node,
					weight="travel_time",
				)
				route = get_route_latlon(graph, path)
			except (nx.NetworkXNoPath, nx.NodeNotFound):
				pass
		hospital_latitude = hospital_longitude = None
		if hospital is not None:
			hospital_latitude, hospital_longitude = get_node_latlon(graph, hospital.node)
		response.append({
			"incident_id": assignment.incident_id,
			"ambulance_id": assignment.ambulance_id,
			"travel_time_sec": assignment.travel_time_sec,
			"coordination_reason": assignment.coordination_reason,
			"solver_method": solver_method.get(
				assignment.incident_id,
				"closest_idle",
			),
			"fallback_reason": fallback_reasons.get(
				assignment.incident_id
			),
			"hospital_id": hospital.id if hospital is not None else None,
			"hospital_match_reason": match_reason,
			"hospital_lat": hospital_latitude,
			"hospital_lon": hospital_longitude,
			"route": route,
		})
	return response
