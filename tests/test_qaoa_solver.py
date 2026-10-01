"""QAOA solver tests."""

import networkx as nx
import pytest

from adas.quantum.qaoa_solver import _effective_penalty, solve_with_qaoa
from adas.quantum.qubo import build_dispatch_qubo
from adas.quantum.verify import brute_force_solve
from adas.simulation.incidents import Ambulance, Incident


@pytest.mark.parametrize("use_warm_start", [False, True])
def test_qaoa_matches_brute_force_on_tiny_case(use_warm_start: bool):
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 3, travel_time=10.0)
	graph.add_edge(1, 4, travel_time=30.0)
	graph.add_edge(2, 3, travel_time=20.0)
	graph.add_edge(2, 4, travel_time=10.0)
	incidents = [Incident(1, 3, 5, 0), Incident(2, 4, 2, 1)]
	fleet = [Ambulance(10, 1), Ambulance(11, 2)]
	qp = build_dispatch_qubo(graph, incidents, fleet)

	_, brute_force_value = brute_force_solve(qp)
	qaoa_result = solve_with_qaoa(qp, use_warm_start=use_warm_start)
	bits = [round(float(value)) for value in qaoa_result.x]

	assert abs(qaoa_result.fval - brute_force_value) < abs(brute_force_value) * 0.3 + 1.0
	assert sum(bits) == 2
	assert all(sum(bits[row * 2 : (row + 1) * 2]) <= 1 for row in range(2))
	assert all(sum(bits[row * 2 + column] for row in range(2)) <= 1 for column in range(2))


def test_qaoa_respects_assignment_constraints_on_three_by_three_case():
	graph = nx.MultiDiGraph()
	for ambulance_node in range(3):
		for incident_node in range(3, 6):
			graph.add_edge(ambulance_node, incident_node, travel_time=1.0)
	incidents = [Incident(index, index + 3, 3, index) for index in range(3)]
	fleet = [Ambulance(index, index) for index in range(3)]
	qp = build_dispatch_qubo(graph, incidents, fleet)

	_, brute_force_value = brute_force_solve(qp)
	qaoa_result = solve_with_qaoa(qp, use_warm_start=False)
	bits = [round(float(value)) for value in qaoa_result.x]

	assert sum(bits) == 3
	assert all(sum(bits[row * 3 : (row + 1) * 3]) <= 1 for row in range(3))
	assert all(sum(bits[row * 3 + column] for row in range(3)) <= 1 for column in range(3))
	assert abs(qaoa_result.fval - brute_force_value) < abs(brute_force_value) * 0.3 + 1.0


def test_constraint_penalty_scales_with_dispatch_objective():
	graph = nx.MultiDiGraph()
	for ambulance_node in (1, 2):
		for incident_node in (3, 4):
			graph.add_edge(ambulance_node, incident_node, travel_time=10_000.0)
	incidents = [Incident(1, 3, 5, 0), Incident(2, 4, 5, 1)]
	fleet = [Ambulance(10, 1), Ambulance(11, 2)]
	qp = build_dispatch_qubo(graph, incidents, fleet)

	assert _effective_penalty(qp, 1000.0) > 1000.0
