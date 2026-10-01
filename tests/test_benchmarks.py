"""Tests for Phase 9 benchmark metrics and API routes."""

import networkx as nx
import numpy as np
from fastapi.testclient import TestClient

from adas.api.main import app
from adas.api.routes import benchmarks as benchmark_routes
from adas.benchmarks.noise_study import (
	build_simple_noise_model,
	run_noise_degradation_study,
)
from adas.benchmarks.qae_efficiency import run_qae_efficiency_benchmark
from adas.benchmarks.scaling import run_scaling_benchmark
from adas.quantum.qubo import build_dispatch_qubo
from adas.simulation.incidents import Ambulance, Incident


def make_complete_graph(size: int = 6) -> nx.MultiDiGraph:
	graph = nx.MultiDiGraph()
	for source in range(size):
		for target in range(size):
			if source != target:
				graph.add_edge(source, target, travel_time=5.0 + abs(source - target))
	return graph


def test_scaling_benchmark_runs_and_brute_force_agrees_at_small_n():
	graph = make_complete_graph()

	results = run_scaling_benchmark(graph, sizes=[2, 3], seed=7, sa_iterations=200)

	assert [row["n"] for row in results] == [2, 3]
	assert all(row["num_qubits"] == row["n"] ** 2 for row in results)
	for row in results:
		assert row["qaoa_time_sec"] >= 0
		assert row["sa_time_sec"] >= 0
		assert row["qaoa_cost"] >= 0
		assert row["sa_cost"] >= 0
		if "brute_force_cost" in row:
			assert abs(row["qaoa_cost"] - row["brute_force_cost"]) < abs(
				row["brute_force_cost"]
			) * 0.4 + 1.0


def test_qae_efficiency_reports_measured_queries_and_errors():
	bin_edges = np.array([0, 10, 20, 30, 40])
	probabilities = np.array([0.3, 0.3, 0.2, 0.2])

	results = run_qae_efficiency_benchmark(
		bin_edges,
		probabilities,
		threshold_sec=20,
		true_probability=0.6,
		epsilon_targets=[0.05, 0.03],
		mc_sample_counts=[100, 400],
	)

	assert len(results) == 2
	assert all(row["qae_grover_oracle_queries"] >= 0 for row in results)
	assert all(row["qae_sampler_shots"] > 0 for row in results)
	assert all(row["qae_error"] < 0.3 for row in results)
	assert all(row["mc_error"] < 0.3 for row in results)


def test_noise_model_targets_aer_basis_and_study_runs_three_levels():
	graph = make_complete_graph(4)
	incidents = [Incident(1, 2, 5, 0), Incident(2, 3, 3, 1)]
	ambulances = [Ambulance(10, 0), Ambulance(11, 1)]
	program = build_dispatch_qubo(graph, incidents, ambulances)
	noise_model = build_simple_noise_model()

	assert {"u", "cx"}.issubset(noise_model.noise_instructions)
	results = run_noise_degradation_study(
		program,
		error_rates=[(0.0, 0.0), (0.005, 0.02), (0.02, 0.08)],
	)

	assert len(results) == 3
	assert all(np.isfinite(row["cost"]) for row in results)
	assert results[0]["cost"] < results[1]["cost"] < results[2]["cost"]
	assert (
		results[0]["optimal_solution_probability"]
		> results[2]["optimal_solution_probability"]
	)


def test_benchmark_routes_use_graph_and_cache_results(monkeypatch):
	graph = make_complete_graph(3)
	calls: list[tuple[nx.MultiDiGraph, list[int]]] = []

	def scaling_stub(selected_graph, sizes):
		calls.append((selected_graph, sizes))
		return [{"n": 2, "qaoa_cost": 1.0}]

	monkeypatch.setattr(benchmark_routes, "get_graph", lambda: graph)
	monkeypatch.setattr(benchmark_routes, "run_scaling_benchmark", scaling_stub)
	benchmark_routes._cached_results.clear()
	with TestClient(app) as client:
		first = client.get("/benchmarks/scaling")
		second = client.get("/benchmarks/scaling")
	benchmark_routes._cached_results.clear()

	assert first.status_code == second.status_code == 200
	assert first.json() == second.json() == [{"n": 2, "qaoa_cost": 1.0}]
	assert calls == [(graph, [2, 3, 4, 5])]


def test_qae_benchmark_route_uses_simulator_distribution(monkeypatch):
	graph = make_complete_graph(3)
	captured: dict[str, object] = {}
	bin_edges = np.array([0, 10, 20, 30, 40])
	probabilities = np.array([0.3, 0.3, 0.2, 0.2])

	def distribution_stub(selected_graph, origin, dest, sim_duration_sec, seed):
		captured["route"] = (selected_graph, origin, dest, sim_duration_sec, seed)
		return bin_edges, probabilities

	def efficiency_stub(*args, **kwargs):
		captured["efficiency"] = (args, kwargs)
		return [{"epsilon_target": 0.05, "qae_error": 0.01}]

	monkeypatch.setattr(benchmark_routes, "get_graph", lambda: graph)
	monkeypatch.setattr(
		benchmark_routes,
		"build_travel_time_distribution",
		distribution_stub,
	)
	monkeypatch.setattr(
		benchmark_routes,
		"run_qae_efficiency_benchmark",
		efficiency_stub,
	)
	benchmark_routes._cached_results.clear()
	with TestClient(app) as client:
		response = client.get("/benchmarks/qae-efficiency")
	benchmark_routes._cached_results.clear()

	assert response.status_code == 200
	assert response.json() == [{"epsilon_target": 0.05, "qae_error": 0.01}]
	assert captured["route"] == (graph, 0, 1, 3600, 1)
	assert captured["efficiency"][1]["true_probability"] == 0.6
