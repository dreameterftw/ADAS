"""Boundary conflict resolution across independently solved zones."""

import math

import networkx as nx
from qiskit_optimization.algorithms import OptimizationResult

from adas.baselines.base import Assignment
from adas.quantum.fallback_solver import FallbackResult
from adas.simulation.incidents import Ambulance, Incident


def _flatten_assignments(
	zone_assignments: dict[int, OptimizationResult | FallbackResult],
) -> dict[int, int]:
	current: dict[int, int] = {}
	for result in zone_assignments.values():
		if isinstance(result, dict):
			for assignment in result["assignment"]:
				current[assignment.incident_id] = assignment.ambulance_id
			continue
		if result.x is None:
			continue
		for name, value in zip(result.variable_names, result.x):
			if value < 0.5 or not name.startswith("x_"):
				continue
			prefix, incident_id, ambulance_id = name.split("_", maxsplit=2)
			if prefix == "x":
				current[int(incident_id)] = int(ambulance_id)
	return current


def _travel_time(
	graph: nx.MultiDiGraph,
	origin: int,
	destination: int,
) -> float | None:
	try:
		return float(
			nx.shortest_path_length(
				graph,
				origin,
				destination,
				weight="travel_time",
			)
		)
	except (nx.NetworkXNoPath, nx.NodeNotFound):
		return None


def reconcile_boundaries(
	graph: nx.MultiDiGraph,
	zone_map: dict[int, int],
	boundary_nodes: set[int],
	zone_assignments: dict[int, OptimizationResult | FallbackResult],
	incidents: list[Incident],
	ambulances: list[Ambulance],
	improvement_threshold_sec: float = 30.0,
) -> list[Assignment]:
	"""Improve boundary assignments using unassigned ambulances in adjacent zones."""
	if not math.isfinite(improvement_threshold_sec) or improvement_threshold_sec < 0:
		raise ValueError("improvement_threshold_sec must be finite and non-negative")

	current = _flatten_assignments(zone_assignments)
	incidents_by_id = {incident.id: incident for incident in incidents}
	ambulances_by_id = {ambulance.id: ambulance for ambulance in ambulances}
	neighboring_zones: dict[int, set[int]] = {}
	for source, target in graph.edges():
		if source not in zone_map or target not in zone_map:
			continue
		source_zone = zone_map[source]
		target_zone = zone_map[target]
		if source_zone != target_zone:
			neighboring_zones.setdefault(source_zone, set()).add(target_zone)
			neighboring_zones.setdefault(target_zone, set()).add(source_zone)

	occupied_ambulances = set(current.values())
	final_assignments: list[Assignment] = []
	for incident_id, ambulance_id in current.items():
		if incident_id not in incidents_by_id or ambulance_id not in ambulances_by_id:
			continue
		incident = incidents_by_id[incident_id]
		ambulance = ambulances_by_id[ambulance_id]
		best_ambulance = ambulance
		best_time = _travel_time(
			graph,
			ambulance.current_node,
			incident.location_node,
		)
		if best_time is None:
			continue
		in_zone_time = best_time

		incident_zone = zone_map.get(incident.location_node)
		if incident.location_node in boundary_nodes and incident_zone is not None:
			for candidate in ambulances:
				candidate_zone = zone_map.get(candidate.current_node)
				if (
					not candidate.available
					or candidate.id in occupied_ambulances
					or candidate_zone not in neighboring_zones.get(incident_zone, set())
				):
					continue
				candidate_time = _travel_time(
					graph,
					candidate.current_node,
					incident.location_node,
				)
				if (
					candidate_time is not None
					and in_zone_time - candidate_time > improvement_threshold_sec
					and candidate_time < best_time
				):
					best_ambulance = candidate
					best_time = candidate_time

		if best_ambulance.id != ambulance.id:
			occupied_ambulances.discard(ambulance.id)
			occupied_ambulances.add(best_ambulance.id)
		final_assignments.append(
			Assignment(incident_id, best_ambulance.id, best_time)
		)
	return final_assignments
