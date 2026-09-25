"""Generate synthetic emergency incidents and ambulance fleets."""

from dataclasses import dataclass
import random

import networkx as nx


@dataclass
class Incident:
	"""An emergency event occurring at a graph node."""

	id: int
	location_node: int
	severity: int
	timestamp: float


@dataclass
class Ambulance:
	"""An ambulance and its current availability state."""

	id: int
	current_node: int
	available: bool = True


def generate_incidents(
	graph: nx.MultiDiGraph,
	count: int,
	sim_duration_sec: float,
	seed: int | None = None,
) -> list[Incident]:
	"""Generate timestamp-sorted incidents located on graph nodes."""
	if count < 0:
		raise ValueError("count must be non-negative")
	if sim_duration_sec < 0:
		raise ValueError("sim_duration_sec must be non-negative")

	nodes = list(graph.nodes)
	if count and not nodes:
		raise ValueError("graph must contain nodes when generating incidents")

	rng = random.Random(seed)
	incidents = [
		Incident(
			id=incident_id,
			location_node=rng.choice(nodes),
			severity=rng.randint(1, 5),
			timestamp=rng.uniform(0, sim_duration_sec),
		)
		for incident_id in range(count)
	]
	incidents.sort(key=lambda incident: incident.timestamp)
	return incidents


def generate_ambulance_fleet(
	graph: nx.MultiDiGraph,
	fleet_size: int,
	seed: int | None = None,
) -> list[Ambulance]:
	"""Generate available ambulances positioned on graph nodes."""
	if fleet_size < 0:
		raise ValueError("fleet_size must be non-negative")

	nodes = list(graph.nodes)
	if fleet_size and not nodes:
		raise ValueError("graph must contain nodes when generating a fleet")

	rng = random.Random(seed)
	return [
		Ambulance(id=ambulance_id, current_node=rng.choice(nodes))
		for ambulance_id in range(fleet_size)
	]
