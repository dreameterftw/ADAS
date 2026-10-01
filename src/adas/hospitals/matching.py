"""Match incidents to reachable hospitals with capacity and specialty checks."""

from dataclasses import dataclass
import random

import networkx as nx


@dataclass
class Hospital:
	id: int
	node: int
	specialties: set[str]
	available_beds: int
	total_beds: int

	def __post_init__(self) -> None:
		if self.total_beds < 0:
			raise ValueError("total_beds must be non-negative")
		if self.available_beds < 0 or self.available_beds > self.total_beds:
			raise ValueError("available_beds must be between zero and total_beds")


SEVERITY_SPECIALTY_MAP = {
	5: {"trauma", "cardiac"},
	4: {"trauma", "cardiac", "general"},
	3: {"general"},
	2: {"general"},
	1: {"general"},
}


def best_hospital_for_incident(
	graph: nx.MultiDiGraph,
	incident_node: int,
	incident_severity: int,
	hospitals: list[Hospital],
) -> Hospital | None:
	"""Return the nearest reachable hospital with beds and a matching specialty.

	If no reachable hospital offers a preferred specialty, choose the nearest
	reachable hospital with capacity rather than returning no destination.
	"""
	candidates = [hospital for hospital in hospitals if hospital.available_beds > 0]
	preferred_specialties = SEVERITY_SPECIALTY_MAP.get(incident_severity, {"general"})
	preferred = [
		hospital
		for hospital in candidates
		if hospital.specialties & preferred_specialties
	]

	def reachable(items: list[Hospital]) -> list[tuple[float, Hospital]]:
		matches = []
		for hospital in items:
			try:
				travel_time = float(
					nx.shortest_path_length(
						graph,
						incident_node,
						hospital.node,
						weight="travel_time",
					)
				)
			except (nx.NetworkXNoPath, nx.NodeNotFound):
				continue
			matches.append((travel_time, hospital))
		return matches

	preferred_reachable = reachable(preferred)
	if preferred_reachable:
		return min(preferred_reachable, key=lambda item: item[0])[1]
	any_reachable = reachable(candidates)
	if any_reachable:
		return min(any_reachable, key=lambda item: item[0])[1]
	return None


def generate_hospital_fleet(
	graph: nx.MultiDiGraph,
	count: int,
	seed: int = 42,
) -> list[Hospital]:
	"""Generate a seeded synthetic hospital fleet for demos and tests."""
	if count < 0:
		raise ValueError("count must be non-negative")
	nodes = list(graph.nodes)
	if count and not nodes:
		raise ValueError("graph must contain nodes when generating hospitals")
	rng = random.Random(seed)
	specialty_pool = [
		{"general"},
		{"general", "cardiac"},
		{"general", "trauma"},
		{"trauma", "cardiac"},
	]
	return [
		Hospital(
			id=hospital_id,
			node=rng.choice(nodes),
			specialties=rng.choice(specialty_pool),
			available_beds=rng.randint(0, 20),
			total_beds=20,
		)
		for hospital_id in range(count)
	]