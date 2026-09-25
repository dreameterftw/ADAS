"""Simulated annealing dispatch baseline."""

import math
import random

import networkx as nx

from adas.baselines.base import Assignment, DispatchStrategy
from adas.simulation.incidents import Ambulance, Incident


class SimulatedAnnealingDispatch(DispatchStrategy):
	"""Optimize a severity-weighted one-to-one dispatch assignment."""

	name = "simulated_annealing"

	def __init__(self, iterations: int = 2000, seed: int | None = None):
		if iterations < 0:
			raise ValueError("iterations must be non-negative")
		self.iterations = iterations
		self.rng = random.Random(seed)

	@staticmethod
	def _total_cost(
		assignment: dict[int, int],
		travel_times: dict[tuple[int, int], float],
		incidents_by_id: dict[int, Incident],
	) -> float:
		return sum(
			travel_times[(incident_id, ambulance_id)]
			* (6 - incidents_by_id[incident_id].severity)
			for incident_id, ambulance_id in assignment.items()
		)

	def solve(
		self,
		graph: nx.MultiDiGraph,
		incidents: list[Incident],
		ambulances: list[Ambulance],
	) -> list[Assignment]:
		available = [ambulance for ambulance in ambulances if ambulance.available]
		incidents_by_id = {incident.id: incident for incident in incidents}
		selected_incidents = incidents[: len(available)]
		selected_ambulances = available[: len(selected_incidents)]
		if not selected_incidents:
			return []

		travel_times: dict[tuple[int, int], float] = {}
		for incident in selected_incidents:
			for ambulance in selected_ambulances:
				try:
					travel_time = nx.shortest_path_length(
						graph,
						ambulance.current_node,
						incident.location_node,
						weight="travel_time",
					)
				except nx.NetworkXNoPath:
					travel_time = float("inf")
				travel_times[(incident.id, ambulance.id)] = float(travel_time)

		current = {
			incident.id: ambulance.id
			for incident, ambulance in zip(selected_incidents, selected_ambulances)
		}
		current_cost = self._total_cost(current, travel_times, incidents_by_id)
		temperature = max(current_cost, 1.0)

		for _ in range(self.iterations):
			incident_ids = list(current)
			if len(incident_ids) < 2:
				break
			first, second = self.rng.sample(incident_ids, 2)
			candidate = current.copy()
			candidate[first], candidate[second] = candidate[second], candidate[first]
			candidate_cost = self._total_cost(
				candidate,
				travel_times,
				incidents_by_id,
			)
			delta = candidate_cost - current_cost
			if delta < 0 or self.rng.random() < math.exp(
				-delta / max(temperature, 1e-9)
			):
				current, current_cost = candidate, candidate_cost
			temperature *= 0.995

		return [
			Assignment(
				incident_id=incident_id,
				ambulance_id=ambulance_id,
				travel_time_sec=travel_times[(incident_id, ambulance_id)],
			)
			for incident_id, ambulance_id in current.items()
			if math.isfinite(travel_times[(incident_id, ambulance_id)])
		]
