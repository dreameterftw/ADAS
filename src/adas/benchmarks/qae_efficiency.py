"""Compare QAE's measured query use with classical Monte Carlo samples."""

import math

import numpy as np

from adas.baselines.monte_carlo_confidence import monte_carlo_on_time_probability
from adas.quantum.qae_confidence import estimate_on_time_probability_with_stats


def run_qae_efficiency_benchmark(
	bin_edges: np.ndarray,
	probabilities: np.ndarray,
	threshold_sec: float,
	true_probability: float,
	epsilon_targets: list[float] | None = None,
	mc_sample_counts: list[int] | None = None,
) -> list[dict[str, float | int]]:
	"""Measure estimation errors, QAE Grover queries, and sampler shots."""
	if not math.isfinite(true_probability) or not 0 <= true_probability <= 1:
		raise ValueError("true_probability must be finite and between 0 and 1")
	if not math.isfinite(threshold_sec):
		raise ValueError("threshold_sec must be finite")
	if epsilon_targets is None:
		epsilon_targets = [0.05, 0.03, 0.02, 0.01]
	if mc_sample_counts is None:
		mc_sample_counts = [100, 400, 1600, 6400]
	if not epsilon_targets or len(epsilon_targets) != len(mc_sample_counts):
		raise ValueError("epsilon_targets and mc_sample_counts must have equal non-zero length")
	if any(not math.isfinite(value) or not 0 < value < 0.5 for value in epsilon_targets):
		raise ValueError("epsilon targets must be finite and between 0 and 0.5")
	if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in mc_sample_counts):
		raise ValueError("Monte Carlo sample counts must be positive integers")

	results: list[dict[str, float | int]] = []
	for epsilon, sample_count in zip(epsilon_targets, mc_sample_counts, strict=True):
		qae_estimate, qae_grover_queries, qae_sampler_shots = (
			estimate_on_time_probability_with_stats(
				bin_edges,
				probabilities,
				threshold_sec,
				epsilon_target=epsilon,
			)
		)
		mc_estimate = monte_carlo_on_time_probability(
			bin_edges,
			probabilities,
			threshold_sec,
			num_samples=sample_count,
		)
		row: dict[str, float | int] = {
			"epsilon_target": epsilon,
			"qae_estimate": qae_estimate,
			"qae_error": abs(qae_estimate - true_probability),
			"qae_grover_oracle_queries": qae_grover_queries,
			"qae_sampler_shots": qae_sampler_shots,
			"mc_num_samples": sample_count,
			"mc_estimate": mc_estimate,
			"mc_error": abs(mc_estimate - true_probability),
		}
		results.append(row)
	return results