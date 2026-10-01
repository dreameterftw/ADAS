"""Lazily initialized in-memory simulation state shared by API routes."""

import networkx as nx

from adas.orchestrator import Orchestrator
from adas.simulation.clock import SimulationState
from adas.simulation.incidents import generate_ambulance_fleet, generate_incidents
from adas.simulation.network import load_city_network


_graph: nx.MultiDiGraph | None = None
_state: SimulationState | None = None
_orchestrator: Orchestrator | None = None


def init_simulation(
	place_name: str = "Andheri, Mumbai, India",
	seed: int = 42,
) -> None:
	"""Load a network and initialize a seeded demo simulation."""
	global _graph, _state, _orchestrator
	graph = load_city_network(place_name)
	incidents = generate_incidents(
		graph,
		count=15,
		sim_duration_sec=3600,
		seed=seed,
	)
	ambulances = generate_ambulance_fleet(graph, fleet_size=6, seed=seed)
	state = SimulationState(pending_incidents=incidents, ambulances=ambulances)
	orchestrator = Orchestrator(graph)
	_graph, _state, _orchestrator = graph, state, orchestrator


def get_simulation_state() -> SimulationState:
	if _state is None:
		init_simulation()
	assert _state is not None
	return _state


def get_orchestrator() -> Orchestrator:
	if _orchestrator is None:
		init_simulation()
	assert _orchestrator is not None
	return _orchestrator