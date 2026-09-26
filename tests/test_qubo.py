"""QUBO correctness tests."""

import networkx as nx

from adas.quantum.qubo import build_dispatch_qubo
from adas.quantum.verify import brute_force_solve
from adas.simulation.incidents import Ambulance, Incident


def make_assignment_case() -> tuple[
	nx.MultiDiGraph, list[Incident], list[Ambulance]
]:
	graph = nx.MultiDiGraph()
	for source, target, travel_time in [
		(1, 3, 2.0),
		(1, 4, 5.0),
		(2, 3, 7.0),
		(2, 4, 1.0),
	]:
		graph.add_edge(source, target, travel_time=travel_time)
	incidents = [Incident(1, 3, 5, 0), Incident(2, 4, 1, 1)]
	ambulances = [Ambulance(10, 1), Ambulance(11, 2)]
	return graph, incidents, ambulances


def test_dispatch_qubo_uses_severity_and_at_most_one_constraints():
	graph, incidents, ambulances = make_assignment_case()
	qp = build_dispatch_qubo(graph, incidents, ambulances)

	assert qp.get_num_vars() == 4
	assert qp.objective.linear.to_dict() == {
		0: -61.0,
		1: -36.0,
		2: -66.0,
		3: -70.0,
	}
	assert len(qp.linear_constraints) == 4
	assert all(constraint.sense.name == "LE" for constraint in qp.linear_constraints)
	assert all(constraint.rhs == 1 for constraint in qp.linear_constraints)


def test_brute_force_finds_maximum_cardinality_minimum_cost_dispatch():
	graph, incidents, ambulances = make_assignment_case()
	qp = build_dispatch_qubo(graph, incidents, ambulances)

	best_x, best_value = brute_force_solve(qp)

	assert best_x == [1, 0, 0, 1]
	assert best_value == -131.0


def test_brute_force_checks_three_by_three_constraints():
	graph = nx.MultiDiGraph()
	for ambulance_node in range(3):
		for incident_node in range(3, 6):
			graph.add_edge(ambulance_node, incident_node, travel_time=1.0)
	incidents = [Incident(index, index + 3, 3, index) for index in range(3)]
	ambulances = [Ambulance(index, index) for index in range(3)]
	qp = build_dispatch_qubo(graph, incidents, ambulances)

	best_x, best_value = brute_force_solve(qp)

	assert qp.get_num_vars() == 9
	assert len(qp.linear_constraints) == 6
	assert best_x is not None
	assert sum(best_x) == 3
	assert best_value == -21.0
	assert all(sum(best_x[row * 3 : (row + 1) * 3]) <= 1 for row in range(3))
	assert all(
		sum(best_x[row * 3 + column] for row in range(3)) <= 1
		for column in range(3)
	)


def test_unreachable_ambulance_incident_pair_cannot_be_selected():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 3, travel_time=1.0)
	graph.add_node(2)
	incidents = [Incident(1, 3, 5, 0)]
	ambulances = [Ambulance(10, 1), Ambulance(11, 2)]
	qp = build_dispatch_qubo(graph, incidents, ambulances)

	best_x, _ = brute_force_solve(qp)

	assert best_x == [1, 0]
	assert any(constraint.name == "unreachable_1_11" for constraint in qp.linear_constraints)
