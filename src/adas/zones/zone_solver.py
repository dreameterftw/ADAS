"""Solve dispatch assignments independently within each zone."""

import networkx as nx
from qiskit_optimization.algorithms import OptimizationResult

from adas.quantum.qaoa_solver import solve_with_qaoa
from adas.quantum.qubo import build_dispatch_qubo
from adas.simulation.incidents import Ambulance, Incident
from adas.zones.partition import zone_members


def solve_zone(
	graph: nx.MultiDiGraph,
	zone_nodes: list[int],
	incidents: list[Incident],
	ambulances: list[Ambulance],
) -> OptimizationResult | None:
	"""Solve dispatch for incidents and available ambulances in one zone."""
	zone_node_set = set(zone_nodes)
	zone_incidents = [
		incident for incident in incidents if incident.location_node in zone_node_set
	]
	zone_ambulances = [
		ambulance
		for ambulance in ambulances
		if ambulance.available and ambulance.current_node in zone_node_set
	]
	if not zone_incidents or not zone_ambulances:
		return None

	program = build_dispatch_qubo(graph, zone_incidents, zone_ambulances)
	return solve_with_qaoa(program, use_warm_start=True)


def solve_all_zones(
	graph: nx.MultiDiGraph,
	zone_map: dict[int, int],
	incidents: list[Incident],
	ambulances: list[Ambulance],
) -> dict[int, OptimizationResult]:
	"""Solve every non-empty zone and return results keyed by zone ID."""
	results: dict[int, OptimizationResult] = {}
	for zone_id in sorted(set(zone_map.values())):
		result = solve_zone(
			graph,
			zone_members(zone_map, zone_id),
			incidents,
			ambulances,
		)
		if result is not None:
			results[zone_id] = result
	return results