"""Rolling zone-based dispatch re-optimization."""

import networkx as nx

from adas.baselines.base import Assignment
from adas.simulation.clock import SimulationState
from adas.zones.coordinator import reconcile_boundaries
from adas.zones.partition import get_boundary_nodes, partition_into_zones
from adas.zones.zone_solver import solve_all_zones


class Orchestrator:
	"""Partition a road network once and replan active dispatches on demand."""

	def __init__(
		self,
		graph: nx.MultiDiGraph,
		max_nodes_per_zone: int = 20,
		max_qubits_per_zone: int = 20,
	) -> None:
		self.graph = graph
		self.max_qubits_per_zone = max_qubits_per_zone
		self.zone_map = partition_into_zones(graph, max_nodes_per_zone)
		self.boundary_nodes = get_boundary_nodes(graph, self.zone_map)

	def replan(self, state: SimulationState) -> list[Assignment]:
		"""Re-solve active incidents and reserve ambulances in the new plan."""
		previous_assignments = state.assignments.copy()
		previous_availability = {
			ambulance.id: ambulance.available for ambulance in state.ambulances
		}
		previously_assigned_ids = {
			assignment.ambulance_id for assignment in previous_assignments.values()
		}
		for ambulance in state.ambulances:
			if ambulance.id in previously_assigned_ids:
				ambulance.available = True
		state.assignments.clear()

		try:
			available_ambulances = [
				ambulance for ambulance in state.ambulances if ambulance.available
			]
			if not state.active_incidents or not available_ambulances:
				return []

			zone_results = solve_all_zones(
				self.graph,
				self.zone_map,
				state.active_incidents,
				available_ambulances,
				max_qubits=self.max_qubits_per_zone,
			)
			assignments = reconcile_boundaries(
				self.graph,
				self.zone_map,
				self.boundary_nodes,
				zone_results,
				state.active_incidents,
				available_ambulances,
			)
		except Exception:
			state.assignments = previous_assignments
			for ambulance in state.ambulances:
				ambulance.available = previous_availability[ambulance.id]
			raise

		state.assignments = {
			assignment.incident_id: assignment for assignment in assignments
		}
		assigned_ids = {assignment.ambulance_id for assignment in assignments}
		for ambulance in state.ambulances:
			if ambulance.id in assigned_ids:
				ambulance.available = False
		return assignments