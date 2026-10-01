"""Tests for bounded solver fallback and hospital matching."""

import time

import networkx as nx
import pytest
from qiskit_optimization.algorithms import OptimizationResult, OptimizationResultStatus

from adas.hospitals.matching import Hospital, best_hospital_for_incident, generate_hospital_fleet
from adas.quantum import fallback_solver
from adas.quantum.fallback_solver import solve_with_fallback
from adas.quantum.qubo import build_dispatch_qubo
from adas.simulation.incidents import Ambulance, Incident


def make_fallback_problem():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=12.0)
	incidents = [Incident(1, 2, 5, 0.0)]
	ambulances = [Ambulance(10, 1)]
	program = build_dispatch_qubo(graph, incidents, ambulances)
	return graph, incidents, ambulances, program


def test_fallback_triggers_on_artificially_short_timeout(monkeypatch: pytest.MonkeyPatch):
	graph, incidents, ambulances, program = make_fallback_problem()

	def slow_qaoa(*args, **kwargs):
		time.sleep(0.05)
		raise RuntimeError("late optimizer failure")

	monkeypatch.setattr(fallback_solver, "solve_with_qaoa", slow_qaoa)
	result = solve_with_fallback(
		program,
		graph,
		incidents,
		ambulances,
		timeout_sec=0.005,
	)

	assert result["method"] == "simulated_annealing_fallback"
	assert result["fallback_reason"] == "timeout"
	assert len(result["assignment"]) == 1
	assert result["cost"] == 12.0


def test_fallback_handles_qaoa_exception(monkeypatch: pytest.MonkeyPatch):
	graph, incidents, ambulances, program = make_fallback_problem()

	def failed_qaoa(*args, **kwargs):
		raise RuntimeError("simulated QAOA error")

	monkeypatch.setattr(fallback_solver, "solve_with_qaoa", failed_qaoa)
	result = solve_with_fallback(program, graph, incidents, ambulances)

	assert result["method"] == "simulated_annealing_fallback"
	assert result["fallback_reason"] == "RuntimeError: simulated QAOA error"
	assert result["assignment"][0].ambulance_id == 10


def test_fallback_returns_valid_qaoa_solution(monkeypatch: pytest.MonkeyPatch):
	graph, incidents, ambulances, program = make_fallback_problem()
	qaoa_result = OptimizationResult(
		x=[1.0],
		fval=program.objective.evaluate([1.0]),
		variables=program.variables,
		status=OptimizationResultStatus.SUCCESS,
	)
	monkeypatch.setattr(fallback_solver, "solve_with_qaoa", lambda *args, **kwargs: qaoa_result)

	result = solve_with_fallback(program, graph, incidents, ambulances)

	assert result["method"] == "qaoa"
	assert result["assignment"][0].ambulance_id == 10
	assert result["cost"] == 12.0


def test_fallback_rejects_fractional_qaoa_solution(monkeypatch: pytest.MonkeyPatch):
	graph, incidents, ambulances, program = make_fallback_problem()
	invalid_result = OptimizationResult(
		x=[0.5],
		fval=0.0,
		variables=program.variables,
		status=OptimizationResultStatus.SUCCESS,
	)
	monkeypatch.setattr(fallback_solver, "solve_with_qaoa", lambda *args, **kwargs: invalid_result)

	result = solve_with_fallback(program, graph, incidents, ambulances)

	assert result["method"] == "simulated_annealing_fallback"
	assert "non-binary" in result["fallback_reason"]


def test_empty_qaoa_dispatch_falls_back_when_routes_are_reachable(
	monkeypatch: pytest.MonkeyPatch,
):
	graph, incidents, ambulances, program = make_fallback_problem()
	empty_result = OptimizationResult(
		x=[0.0],
		fval=0.0,
		variables=program.variables,
		status=OptimizationResultStatus.SUCCESS,
	)
	monkeypatch.setattr(fallback_solver, "solve_with_qaoa", lambda *args, **kwargs: empty_result)

	result = solve_with_fallback(program, graph, incidents, ambulances)

	assert result["method"] == "simulated_annealing_fallback"
	assert "empty dispatch" in result["fallback_reason"]
	assert len(result["assignment"]) == 1


def test_fallback_rejects_invalid_timeout():
	graph, incidents, ambulances, program = make_fallback_problem()

	with pytest.raises(ValueError, match="timeout_sec"):
		solve_with_fallback(program, graph, incidents, ambulances, timeout_sec=0)


def test_hospital_matching_respects_bed_capacity():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=1.0)
	graph.add_edge(1, 3, travel_time=20.0)
	full_hospital = Hospital(0, 2, {"trauma"}, 0, 20)
	open_hospital = Hospital(1, 3, {"trauma"}, 5, 20)

	result = best_hospital_for_incident(
		graph,
		1,
		incident_severity=5,
		hospitals=[full_hospital, open_hospital],
	)

	assert result is open_hospital


def test_hospital_matching_falls_back_to_reachable_capacity():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=8.0)
	hospitals = [
		Hospital(0, 2, {"orthopedics"}, 2, 10),
		Hospital(1, 3, {"trauma"}, 10, 10),
	]

	result = best_hospital_for_incident(graph, 1, 5, hospitals)

	assert result is hospitals[0]


def test_hospital_matching_returns_none_when_no_beds_are_reachable():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=8.0)
	hospitals = [
		Hospital(0, 2, {"general"}, 0, 10),
		Hospital(1, 3, {"trauma"}, 10, 10),
	]

	assert best_hospital_for_incident(graph, 1, 3, hospitals) is None


def test_hospital_fleet_generation_is_seeded():
	graph = nx.MultiDiGraph()
	graph.add_nodes_from((1, 2, 3))

	assert generate_hospital_fleet(graph, 4, seed=3) == generate_hospital_fleet(
		graph,
		4,
		seed=3,
	)
