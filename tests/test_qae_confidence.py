"""Tests for QAE and its classical confidence baseline."""

import numpy as np
import networkx as nx
import pytest

from adas.baselines.monte_carlo_confidence import monte_carlo_on_time_probability
from adas.quantum.distribution import build_travel_time_distribution
from adas.quantum.qae_confidence import (
	build_distribution_loader,
	estimate_on_time_probability,
)


def test_qae_matches_known_distribution():
	bin_edges = np.array([0, 10, 20, 30, 40])
	probabilities = np.array([0.3, 0.3, 0.2, 0.2])

	result = estimate_on_time_probability(
		bin_edges,
		probabilities,
		threshold_sec=20,
		epsilon_target=0.02,
	)

	assert abs(result - 0.6) < 0.1


def test_qae_vs_monte_carlo_agree():
	bin_edges = np.array([0, 10, 20, 30])
	probabilities = np.array([0.5, 0.3, 0.2])

	qae_result = estimate_on_time_probability(
		bin_edges,
		probabilities,
		threshold_sec=15,
		epsilon_target=0.02,
	)
	monte_carlo_result = monte_carlo_on_time_probability(
		bin_edges,
		probabilities,
		threshold_sec=15,
		num_samples=5000,
	)

	assert abs(qae_result - monte_carlo_result) < 0.1


def test_distribution_loader_is_invertible():
	circuit = build_distribution_loader(np.array([0.3, 0.3, 0.2, 0.2]), 2)

	assert circuit.inverse().num_qubits == 2


@pytest.mark.parametrize(
	"probabilities, num_qubits",
	[
		(np.array([0.5, -0.1]), 1),
		(np.array([0.0, 0.0]), 1),
		(np.array([0.25, 0.25, 0.25, 0.25, 0.0]), 2),
	],
)
def test_distribution_loader_rejects_invalid_probabilities(
	probabilities: np.ndarray,
	num_qubits: int,
):
	with pytest.raises(ValueError):
		build_distribution_loader(probabilities, num_qubits)


def test_travel_time_distribution_uses_seeded_simulator_samples():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=10.0)
	arguments = (graph, 1, 2, 1000)

	bin_edges, probabilities = build_travel_time_distribution(
		*arguments,
		num_bins=8,
		num_samples=200,
		seed=7,
	)
	repeated_edges, repeated_probabilities = build_travel_time_distribution(
		*arguments,
		num_bins=8,
		num_samples=200,
		seed=7,
	)

	assert bin_edges.shape == (9,)
	assert probabilities.shape == (8,)
	assert probabilities.sum() == pytest.approx(1.0)
	assert np.count_nonzero(probabilities) > 1
	assert np.array_equal(bin_edges, repeated_edges)
	assert np.array_equal(probabilities, repeated_probabilities)


def test_qae_consumes_simulator_distribution():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=10.0)
	bin_edges, probabilities = build_travel_time_distribution(
		graph,
		1,
		2,
		1000,
		num_bins=8,
		num_samples=200,
		seed=7,
	)
	bin_centers = bin_edges[:-1] + np.diff(bin_edges) / 2
	expected_probability = float(probabilities[bin_centers <= 17.5].sum())

	result = estimate_on_time_probability(
		bin_edges,
		probabilities,
		threshold_sec=17.5,
		epsilon_target=0.03,
	)

	assert abs(result - expected_probability) < 0.1


def test_travel_time_distribution_rejects_invalid_sampling_parameters():
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=10.0)

	with pytest.raises(ValueError):
		build_travel_time_distribution(graph, 1, 2, 0)
	with pytest.raises(ValueError):
		build_travel_time_distribution(graph, 1, 2, 100, num_bins=0)
	with pytest.raises(ValueError):
		build_travel_time_distribution(graph, 1, 2, 100, num_samples=0)