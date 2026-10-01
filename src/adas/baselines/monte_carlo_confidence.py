"""Classical Monte Carlo baseline for route on-time probability."""

import math

import numpy as np


def monte_carlo_on_time_probability(
	bin_edges: np.ndarray,
	probabilities: np.ndarray,
	threshold_sec: float,
	num_samples: int,
	seed: int = 1,
) -> float:
	"""Estimate the midpoint-based on-time probability by sampling bins."""
	edges = np.asarray(bin_edges, dtype=float)
	values = np.asarray(probabilities, dtype=float)
	if edges.ndim != 1 or edges.size < 2:
		raise ValueError("bin_edges must be a one-dimensional array with at least two values")
	if values.ndim != 1 or edges.size != values.size + 1:
		raise ValueError("bin_edges must contain exactly one more value than probabilities")
	if not np.all(np.isfinite(edges)) or np.any(np.diff(edges) <= 0):
		raise ValueError("bin_edges must be finite and strictly increasing")
	if not np.all(np.isfinite(values)) or np.any(values < 0):
		raise ValueError("probabilities must be finite and non-negative")
	probability_sum = float(values.sum())
	if not math.isfinite(probability_sum) or probability_sum <= 0:
		raise ValueError("probabilities must have a positive finite sum")
	if not math.isfinite(threshold_sec):
		raise ValueError("threshold_sec must be finite")
	if num_samples < 1:
		raise ValueError("num_samples must be at least 1")

	rng = np.random.default_rng(seed)
	bin_centers = edges[:-1] + np.diff(edges) / 2
	samples = rng.choice(bin_centers, size=num_samples, p=values / probability_sum)
	return float(np.mean(samples <= threshold_sec))