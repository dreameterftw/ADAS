"""Rolling zone-based dispatch re-optimization."""

import math

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
		timeout_sec_per_zone: float = 10.0,
	) -> None:
		if not math.isfinite(timeout_sec_per_zone) or timeout_sec_per_zone <= 0:
			raise ValueError("timeout_sec_per_zone must be finite and positive")
		self.graph = graph
		self.max_qubits_per_zone = max_qubits_per_zone
		self.timeout_sec_per_zone = timeout_sec_per_zone
		self.zone_map = partition_into_zones(graph, max_nodes_per_zone)
		self.boundary_nodes = get_boundary_nodes(graph, self.zone_map)
		self.last_solver_methods: dict[int, str] = {}
		self.last_fallback_reasons: dict[int, str] = {}

	def replan(self, state: SimulationState) -> list[Assignment]:
		"""Re-solve active incidents and reserve ambulances in the new plan."""
		previous_assignments = state.assignments.copy()
		previous_solver_methods = self.last_solver_methods.copy()
		previous_fallback_reasons = self.last_fallback_reasons.copy()
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
				self.last_solver_methods = {}
				self.last_fallback_reasons = {}
				return []

			zone_results = solve_all_zones(
				self.graph,
				self.zone_map,
				state.active_incidents,
				available_ambulances,
				max_qubits=self.max_qubits_per_zone,
				timeout_sec=self.timeout_sec_per_zone,
			)
			self.last_solver_methods = {}
			self.last_fallback_reasons = {}
			for zone_id, result in zone_results.items():
				if isinstance(result, dict):
					method = result["method"]
					fallback_reason = result.get("fallback_reason")
				else:
					method = "qaoa"
					fallback_reason = None
				for incident in state.active_incidents:
					if self.zone_map.get(incident.location_node) == zone_id:
						self.last_solver_methods[incident.id] = method
						if fallback_reason is not None:
							self.last_fallback_reasons[incident.id] = fallback_reason
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
			self.last_solver_methods = previous_solver_methods
			self.last_fallback_reasons = previous_fallback_reasons
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