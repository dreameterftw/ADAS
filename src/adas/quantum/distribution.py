"""Build a discretized route travel-time distribution from simulator samples."""

import math

import networkx as nx
import numpy as np

from adas.simulation.lightweight_sim import travel_time_at


def build_travel_time_distribution(
	graph: nx.MultiDiGraph,
	origin: int,
	dest: int,
	sim_duration_sec: float,
	num_bins: int = 8,
	num_samples: int = 200,
	seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
	"""Return histogram edges and probabilities from sampled simulator times."""
	if not math.isfinite(sim_duration_sec) or sim_duration_sec <= 0:
		raise ValueError("sim_duration_sec must be finite and positive")
	if isinstance(num_bins, bool) or not isinstance(num_bins, (int, np.integer)) or num_bins < 1:
		raise ValueError("num_bins must be a positive integer")
	if (
		isinstance(num_samples, bool)
		or not isinstance(num_samples, (int, np.integer))
		or num_samples < 1
	):
		raise ValueError("num_samples must be a positive integer")

	rng = np.random.default_rng(seed)
	sample_times = rng.uniform(0, sim_duration_sec, size=num_samples)
	samples = np.fromiter(
		(
			travel_time_at(
				graph,
				origin,
				dest,
				float(sample_time),
				sim_duration_sec,
			)
			for sample_time in sample_times
		),
		dtype=float,
		count=num_samples,
	)
	if not np.all(np.isfinite(samples)) or np.any(samples < 0):
		raise ValueError("simulator returned invalid travel times")

	counts, bin_edges = np.histogram(samples, bins=num_bins)
	probabilities = counts.astype(float) / num_samples
	return bin_edges, probabilities