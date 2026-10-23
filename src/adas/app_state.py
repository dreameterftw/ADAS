"""Lazily initialized in-memory simulation state shared by API routes."""

import math
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
from adas.simulation.network import load_bundled_road_network, load_city_network


_graph: nx.MultiDiGraph | None = None
_state: SimulationState | None = None
_orchestrator: Orchestrator | None = None
_hospitals: list[Hospital] | None = None
_decision_log = {"qaoa": 0, "fallback": 0}
_decision_log_lock = Lock()
_request_log: list[dict[str, object]] = []
_request_log_lock = Lock()
_traffic_mode = "normal"


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


def init_showcase_scenario() -> None:
	"""Load a repeatable response scenario whose positions snap to real OSM roads."""
	global _graph, _state, _orchestrator, _hospitals, _traffic_mode
	graph = load_bundled_road_network()
	used_nodes: set[int] = set()
	def road_node(latitude: float, longitude: float) -> int:
		cosine = math.cos(math.radians(latitude))
		node = min(
			(node_id for node_id in graph if node_id not in used_nodes),
			key=lambda node_id: (
				(graph.nodes[node_id]["y"] - latitude) ** 2
				+ ((graph.nodes[node_id]["x"] - longitude) * cosine) ** 2
			),
		)
		used_nodes.add(node)
		return node

	ambulance_nodes = [
		road_node(*point)
		for point in (
			(19.116, 72.840), (19.121, 72.842), (19.123, 72.850),
			(19.118, 72.852), (19.1145, 72.847), (19.122, 72.846),
		)
	]
	incident_nodes = [
		road_node(*point)
		for point in (
			(19.115, 72.851), (19.120, 72.840),
			(19.122, 72.845), (19.117, 72.848),
		)
	]
	hospital_nodes = [
		road_node(*point)
		for point in (
			(19.123, 72.848), (19.115, 72.843),
			(19.120, 72.852), (19.116, 72.847),
		)
	]
	incidents = [
		Incident(incident_id, node, severity, 0.0)
		for incident_id, node, severity in zip((101, 102, 103, 104), incident_nodes, (5, 4, 3, 5))
	]
	ambulances = [
		Ambulance(unit_id, node)
		for unit_id, node in zip((10, 11, 12, 13, 14, 15), ambulance_nodes)
	]
	state = SimulationState(active_incidents=incidents, ambulances=ambulances)
	orchestrator = Orchestrator(graph, max_nodes_per_zone=12, timeout_sec_per_zone=0.5)
	hospitals = [
		Hospital("H-A", hospital_nodes[0], {"general", "cardiac"}, 3, 24),
		Hospital("H-B", hospital_nodes[1], {"general", "trauma"}, 2, 18),
		Hospital("H-C", hospital_nodes[2], {"general", "cardiac"}, 5, 32),
		Hospital("H-D", hospital_nodes[3], {"trauma"}, 1, 12),
	]
	_graph, _state, _orchestrator, _hospitals = graph, state, orchestrator, hospitals
	_traffic_mode = "normal"
	clear_request_log()


def set_traffic_mode(mode: str) -> None:
	global _traffic_mode
	if mode not in {"normal", "peak", "event"}:
		raise ValueError("Traffic mode must be normal, peak, or event.")
	graph = get_graph()
	for _source, _target, _key, data in graph.edges(keys=True, data=True):
		base = float(data.get("base_travel_time", data.get("travel_time", 60.0)))
		major = bool(data.get("major_corridor", False))
		axis = data.get("axis")
		if mode == "normal":
			factor = 1.0
		elif mode == "peak":
			factor = 3.2 if major else 1.25
		else:
			factor = 7.0 if major else 1.1
		data["travel_time"] = base * factor
		data["traffic_level"] = "closed" if data.get("closed") else "heavy" if factor >= 3 else "moderate" if factor > 1 else "normal"
		if mode == "event" and major and axis == "horizontal" and not data.get("closed"):
			data["traffic_level"] = "blocked"
	_traffic_mode = mode


def set_road_closure(source: int, target: int, closed: bool) -> None:
	"""Apply a temporary bidirectional corridor closure and preserve its base cost."""
	graph = get_graph()
	if source not in graph or target not in graph or not (graph.has_edge(source, target) or graph.has_edge(target, source)):
		raise ValueError("The selected road segment does not exist in the active network.")
	for left, right in ((source, target), (target, source)):
		if not graph.has_edge(left, right):
			continue
		for _key, data in graph[left][right].items():
			data["closed"] = closed
			base = float(data.get("base_travel_time", data.get("travel_time", 60.0)))
			factor = 1.0 if _traffic_mode == "normal" else 3.2 if _traffic_mode == "peak" and data.get("major_corridor") else 1.25 if _traffic_mode == "peak" else 7.0 if data.get("major_corridor") else 1.1
			data["travel_time"] = base * factor
			if closed:
				data["traffic_level"] = "closed"
			elif _traffic_mode != "normal":
				data["traffic_level"] = "heavy" if factor >= 3 else "moderate"
			else:
				data["traffic_level"] = "normal"


def get_traffic_mode() -> str:
	return _traffic_mode


def get_simulation_state() -> SimulationState:
	if _state is None:
		try:
			init_simulation()
		except Exception:
			# External OSM providers may fail with transport or library-specific
			# exceptions. Keep the API usable with the bundled response graph.
			init_showcase_scenario()
	assert _state is not None
	return _state


def get_graph() -> nx.MultiDiGraph:
	"""Return the graph used by the shared simulation, initializing if needed."""
	if _graph is None:
		try:
			init_simulation()
		except Exception:
			# External OSM providers may fail with transport or library-specific
			# exceptions. Keep the API usable with the bundled response graph.
			init_showcase_scenario()
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
