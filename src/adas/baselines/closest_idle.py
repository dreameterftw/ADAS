"""Closest-idle-unit dispatch baseline."""

import networkx as nx

from adas.baselines.base import Assignment, DispatchStrategy
from adas.simulation.incidents import Ambulance, Incident


class ClosestIdleDispatch(DispatchStrategy):
	"""Assign each incident to the nearest currently available ambulance."""

	name = "closest_idle"

	def solve(
		self,
		graph: nx.MultiDiGraph,
		incidents: list[Incident],
		ambulances: list[Ambulance],
	) -> list[Assignment]:
		available = {
			ambulance.id: ambulance
			for ambulance in ambulances
			if ambulance.available
		}
		assignments: list[Assignment] = []

		for incident in incidents:
			if not available:
				break

			best_id: int | None = None
			best_time = float("inf")
			for ambulance_id, ambulance in available.items():
				try:
					travel_time = nx.shortest_path_length(
						graph,
						ambulance.current_node,
						incident.location_node,
						weight="travel_time",
					)
				except nx.NetworkXNoPath:
					continue
				if travel_time < best_time:
					best_id = ambulance_id
					best_time = float(travel_time)

			if best_id is not None:
				assignments.append(
					Assignment(incident.id, best_id, best_time)
				)
				del available[best_id]

		return assignments
