"""Lazily initialized in-memory simulation state shared by API routes."""

from threading import Lock

import networkx as nx

from adas.orchestrator import Orchestrator
from adas.hospitals.matching import Hospital, generate_hospital_fleet
from adas.simulation.clock import SimulationState
from adas.simulation.incidents import (
	Ambulance,
	Incident,
	generate_ambulance_fleet,
	generate_incidents,
)
from adas.simulation.network import load_city_network


_graph: nx.MultiDiGraph | None = None
_state: SimulationState | None = None
_orchestrator: Orchestrator | None = None
_hospitals: list[Hospital] | None = None
_decision_log = {"qaoa": 0, "fallback": 0}
_decision_log_lock = Lock()
_request_log: list[dict[str, object]] = []
_request_log_lock = Lock()


def record_decision(method: str) -> None:
	key = "qaoa" if method == "qaoa" else "fallback"
	with _decision_log_lock:
		_decision_log[key] += 1


def get_decision_log() -> dict[str, int]:
	with _decision_log_lock:
		return dict(_decision_log)


def add_request_record(record: dict[str, object]) -> None:
	with _request_log_lock:
		_request_log.insert(0, record)
		del _request_log[100:]


def get_request_log() -> list[dict[str, object]]:
	with _request_log_lock:
		return [record.copy() for record in _request_log]


def clear_request_log() -> None:
	with _request_log_lock:
		_request_log.clear()


def init_simulation(
	place_name: str = "Andheri, Mumbai, India",
	seed: int = 42,
) -> None:
	"""Load a network and initialize a seeded demo simulation."""
	global _graph, _state, _orchestrator, _hospitals
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
	hospitals = generate_hospital_fleet(graph, count=6, seed=seed)
	_graph, _state, _orchestrator, _hospitals = graph, state, orchestrator, hospitals


def init_demo_scenario() -> None:
	"""Load a compact deterministic scenario for demonstrating dispatch behavior."""
	global _graph, _state, _orchestrator, _hospitals
	graph = nx.MultiDiGraph()
	for node, latitude, longitude in (
		(1, 19.1197, 72.8468),
		(2, 19.1200, 72.8472),
		(3, 19.1203, 72.8476),
		(4, 19.1206, 72.8480),
	):
		graph.add_node(node, y=latitude, x=longitude)
	for source, target, travel_time in (
		(1, 2, 100.0),
		(2, 1, 100.0),
		(2, 3, 5.0),
		(3, 2, 5.0),
		(3, 4, 100.0),
		(4, 3, 100.0),
	):
		graph.add_edge(source, target, travel_time=travel_time)
	state = SimulationState(
		active_incidents=[Incident(1, 2, 5, 0.0)],
		ambulances=[Ambulance(10, 1), Ambulance(11, 3)],
	)
	orchestrator = Orchestrator(
		graph,
		max_nodes_per_zone=2,
		timeout_sec_per_zone=0.000001,
	)
	hospitals = [
		Hospital(1, 4, {"trauma"}, 0, 10),
		Hospital(2, 3, {"general"}, 5, 10),
	]
	_graph, _state, _orchestrator, _hospitals = graph, state, orchestrator, hospitals


def get_simulation_state() -> SimulationState:
	if _state is None:
		try:
			init_simulation()
		except (ImportError, OSError, RuntimeError, ValueError):
			init_demo_scenario()
	assert _state is not None
	return _state


def get_graph() -> nx.MultiDiGraph:
	"""Return the graph used by the shared simulation, initializing if needed."""
	if _graph is None:
		try:
			init_simulation()
		except (ImportError, OSError, RuntimeError, ValueError):
			init_demo_scenario()
	assert _graph is not None
	return _graph


def get_orchestrator() -> Orchestrator:
	if _orchestrator is None:
		get_graph()
	assert _orchestrator is not None
	return _orchestrator


def get_hospitals() -> list[Hospital]:
	if _hospitals is None:
		get_graph()
	assert _hospitals is not None
	return _hospitals
