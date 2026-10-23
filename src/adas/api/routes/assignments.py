"""Live dispatch-assignment API routes."""

from typing import Any

import networkx as nx
from fastapi import APIRouter

from adas.app_state import get_graph, get_hospitals, get_orchestrator, get_simulation_state, get_traffic_mode
from adas.baselines.closest_idle import ClosestIdleDispatch
from adas.simulation.incidents import Ambulance
from adas.hospitals.matching import best_hospital_for_incident
from adas.simulation.network import get_node_latlon, get_route_latlon, open_road_travel_time


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
	# A solver may return a partial valid plan after a zone timeout. Fill every
	# remaining reachable call with a unique idle unit using the classical baseline.
	assigned_incident_ids = {assignment.incident_id for assignment in assignments}
	remaining_incidents = [incident for incident in state.active_incidents if incident.id not in assigned_incident_ids]
	if remaining_incidents:
		idle_ambulances = [ambulance for ambulance in state.ambulances if ambulance.available]
		gap_assignments = ClosestIdleDispatch().solve(graph, remaining_incidents, idle_ambulances)
		for assignment in gap_assignments:
			assignments.append(assignment)
			state.assignments[assignment.incident_id] = assignment
			ambulance = next((unit for unit in idle_ambulances if unit.id == assignment.ambulance_id), None)
			if ambulance is not None:
				ambulance.available = False
			solver_method[assignment.incident_id] = "closest_idle_recovery"
			fallback_reasons[assignment.incident_id] = "The primary planner returned a partial plan."
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
					weight=open_road_travel_time,
				)
				route = get_route_latlon(graph, path)
			except (nx.NetworkXNoPath, nx.NodeNotFound):
				pass
		hospital_latitude = hospital_longitude = None
		hospital_beds = None
		hospital_specialties: list[str] = []
		if hospital is not None:
			hospital_latitude, hospital_longitude = get_node_latlon(graph, hospital.node)
			hospital_beds = hospital.available_beds
			hospital_specialties = sorted(hospital.specialties)
		if hospital is None:
			hospital_rationale = "No reachable hospital currently reports available beds."
		elif match_reason == "specialty_and_capacity":
			hospital_rationale = f"Hospital {hospital.id} has a preferred specialty and {hospital.available_beds} reported available beds."
		else:
			hospital_rationale = f"Hospital {hospital.id} is the nearest reachable facility reporting {hospital.available_beds} available beds; no preferred specialty match was available."
		method = solver_method.get(assignment.incident_id, "closest_idle")
		method_label = "QAOA" if method == "qaoa" else method.replace("_", " ")
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
			"assignment_reason": (
				f"Severity {incident.severity if incident is not None else 'unknown'} priority was considered; "
				f"{method_label} selected this available unit "
				f"for an estimated {max(1, round(assignment.travel_time_sec / 60))}-minute response under "
				f"{get_traffic_mode()} traffic conditions. {hospital_rationale}"
			),
			"hospital_id": hospital.id if hospital is not None else None,
			"hospital_match_reason": match_reason,
			"hospital_available_beds": hospital_beds,
			"hospital_specialties": hospital_specialties,
			"hospital_lat": hospital_latitude,
			"hospital_lon": hospital_longitude,
			"route": route,
		})
	return response


@router.get("/comparison")
def compare_dispatch_baseline() -> dict[str, Any]:
	"""Compare the current coordinated plan with a nearest-idle dispatch baseline."""
	state = get_simulation_state()
	graph = get_graph()
	active_ids = {incident.id for incident in state.active_incidents}
	optimized = [assignment for incident_id, assignment in state.assignments.items() if incident_id in active_ids]
	# Compare both planners from the same fleet snapshot, independent of the
	# availability flags changed when the optimized plan was committed.
	assigned_ambulance_ids = {assignment.ambulance_id for assignment in optimized}
	baseline_fleet = [
		Ambulance(unit.id, unit.current_node, unit.available or unit.id in assigned_ambulance_ids)
		for unit in state.ambulances
	]
	baseline = ClosestIdleDispatch().solve(graph, list(state.active_incidents), baseline_fleet)
	optimized_total = sum(float(item.travel_time_sec) for item in optimized)
	baseline_total = sum(item.travel_time_sec for item in baseline)
	optimized_count, baseline_count = len(optimized), len(baseline)
	return {
		"baseline": "nearest available ambulance, greedily assigned",
		"optimized": {
			"assigned": optimized_count,
			"unassigned": max(0, len(state.active_incidents) - optimized_count),
			"combined_eta_sec": round(optimized_total, 1),
		},
		"baseline_result": {
			"assigned": baseline_count,
			"unassigned": max(0, len(state.active_incidents) - baseline_count),
			"combined_eta_sec": round(baseline_total, 1),
		},
		"eta_delta_sec": round(baseline_total - optimized_total, 1) if optimized_count == baseline_count else None,
		"same_coverage": optimized_count == baseline_count,
		"note": "Combined estimated dispatch travel time; comparison uses the same incident and ambulance snapshot.",
	}
