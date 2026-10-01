"""Tests for zone partitioning, independent solving, and coordination."""

import networkx as nx
import pytest
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import OptimizationResult, OptimizationResultStatus

from adas.baselines.base import Assignment
from adas.simulation.incidents import Ambulance, Incident
from adas.zones.coordinator import reconcile_boundaries
from adas.zones.partition import (
	get_boundary_nodes,
	partition_into_zones,
	zone_members,
)
from adas.zones.zone_solver import solve_all_zones, solve_zone


def make_optimization_result(variable_names: list[str], values: list[float]):
	program = QuadraticProgram()
	for name in variable_names:
		program.binary_var(name)
	return OptimizationResult(
		x=values,
		fval=0.0,
		variables=program.variables,
		status=OptimizationResultStatus.SUCCESS,
	)


def test_partition_respects_zone_size_cap_and_includes_all_nodes():
	graph = nx.MultiDiGraph()
	graph.add_edges_from((node, node + 1) for node in range(9))

	zone_map = partition_into_zones(graph, max_nodes_per_zone=3)
	zone_sizes = {}
	for zone_id in zone_map.values():
		zone_sizes[zone_id] = zone_sizes.get(zone_id, 0) + 1

	assert all(size <= 3 for size in zone_sizes.values())
	assert set(zone_map) == set(graph.nodes)
	assert all(zone_members(zone_map, zone_id) for zone_id in zone_sizes)


def test_partition_handles_empty_and_isolated_networks():
	assert partition_into_zones(nx.MultiDiGraph()) == {}
	graph = nx.MultiDiGraph()
	graph.add_nodes_from((1, 2, 3))
	zone_map = partition_into_zones(graph, max_nodes_per_zone=2)

	assert set(zone_map) == {1, 2, 3}
	assert max(zone_map.values()) >= 1


def test_partition_rejects_invalid_zone_size():
	with pytest.raises(ValueError):
		partition_into_zones(nx.MultiDiGraph(), max_nodes_per_zone=0)


def test_boundary_nodes_are_endpoints_of_cross_zone_edges():
	graph = nx.MultiDiGraph()
	graph.add_edges_from(((1, 2), (2, 3), (3, 4)))
	zone_map = {1: 0, 2: 0, 3: 1, 4: 1}

	assert get_boundary_nodes(graph, zone_map) == {2, 3}


def test_solve_all_zones_runs_each_zone_independently():
	graph = nx.MultiDiGraph()
	graph.add_edges_from(
		(
			(1, 2, {"travel_time": 5.0}),
			(3, 4, {"travel_time": 7.0}),
		)
	)
	zone_map = {1: 0, 2: 0, 3: 1, 4: 1}
	incidents = [Incident(10, 2, 3, 0), Incident(11, 4, 3, 1)]
	ambulances = [Ambulance(20, 1), Ambulance(21, 3)]

	results = solve_all_zones(graph, zone_map, incidents, ambulances)

	assert set(results) == {0, 1}
	assert all(result.x is not None for result in results.values())
	assert all(len(result.x) <= 20 for result in results.values())
	assert all(result.variable_names == ["x_10_20"] or result.variable_names == ["x_11_21"] for result in results.values())


def test_zone_solver_rejects_qubo_over_qubit_budget():
	graph = nx.MultiDiGraph()
	for ambulance_node in range(5):
		for incident_node in range(5, 10):
			graph.add_edge(ambulance_node, incident_node, travel_time=1.0)
	incidents = [Incident(index, index + 5, 3, index) for index in range(5)]
	ambulances = [Ambulance(index, index) for index in range(5)]

	with pytest.raises(ValueError, match="25 variables.*limit of 20"):
		solve_zone(graph, list(range(10)), incidents, ambulances)


def test_reconcile_reassigns_boundary_incident_to_better_free_neighbor():
	graph = nx.MultiDiGraph()
	graph.add_edge(2, 3, travel_time=5.0)
	graph.add_edge(4, 3, travel_time=60.0)
	zone_map = {1: 0, 2: 0, 3: 1, 4: 1}
	incident = Incident(10, 3, 3, 0)
	ambulances = [Ambulance(20, 2), Ambulance(21, 4)]
	result = make_optimization_result(["x_10_21"], [1.0])

	assignments = reconcile_boundaries(
		graph,
		zone_map,
		{2, 3},
		{1: result},
		[incident],
		ambulances,
		improvement_threshold_sec=30.0,
	)

	assert assignments == [Assignment(10, 20, 5.0)]


def test_reconcile_selects_best_candidate_against_original_route():
	graph = nx.MultiDiGraph()
	graph.add_edge(2, 3, travel_time=50.0)
	graph.add_edge(1, 3, travel_time=30.0)
	graph.add_edge(4, 3, travel_time=100.0)
	zone_map = {1: 0, 2: 0, 3: 1, 4: 1}
	incident = Incident(10, 3, 3, 0)
	ambulances = [Ambulance(20, 2), Ambulance(22, 1), Ambulance(21, 4)]
	result = make_optimization_result(["x_10_21"], [1.0])

	assignments = reconcile_boundaries(
		graph,
		zone_map,
		{1, 2, 3},
		{1: result},
		[incident],
		ambulances,
		improvement_threshold_sec=30.0,
	)

	assert assignments == [Assignment(10, 22, 30.0)]


def test_reconcile_does_not_steal_an_assigned_ambulance():
	graph = nx.MultiDiGraph()
	graph.add_edge(2, 3, travel_time=5.0)
	graph.add_edge(4, 3, travel_time=60.0)
	graph.add_edge(2, 4, travel_time=2.0)
	zone_map = {1: 0, 2: 0, 3: 1, 4: 0}
	first_incident = Incident(10, 3, 3, 0)
	second_incident = Incident(11, 4, 3, 1)
	ambulances = [Ambulance(20, 2), Ambulance(21, 4)]
	result = make_optimization_result(
		["x_10_21", "x_11_20"],
		[1.0, 1.0],
	)

	assignments = reconcile_boundaries(
		graph,
		zone_map,
		{2, 3},
		{1: result},
		[first_incident, second_incident],
		ambulances,
		improvement_threshold_sec=30.0,
	)

	assert {assignment.incident_id: assignment.ambulance_id for assignment in assignments} == {
		10: 21,
		11: 20,
	}
	assert len({assignment.ambulance_id for assignment in assignments}) == 2