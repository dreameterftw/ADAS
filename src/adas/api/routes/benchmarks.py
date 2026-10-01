"""Placeholder benchmark API routes."""

import numpy as np
from fastapi import APIRouter

from adas.app_state import get_graph
from adas.baselines.monte_carlo_confidence import monte_carlo_on_time_probability
from adas.benchmarks.qae_efficiency import run_qae_efficiency_benchmark
from adas.benchmarks.scaling import run_scaling_benchmark
from adas.quantum.distribution import build_travel_time_distribution

router = APIRouter()
_cached_results: dict[str, list[dict[str, int | float]]] = {}


@router.get("/summary")
def benchmark_summary() -> dict[str, str]:
	return {"status": "not yet implemented; see Phase 9"}


@router.get("/scaling")
def get_scaling_benchmark() -> list[dict[str, int | float]]:
	if "scaling" not in _cached_results:
		_cached_results["scaling"] = run_scaling_benchmark(
			get_graph(),
			sizes=[2, 3, 4, 5],
		)
	return _cached_results["scaling"]


@router.get("/qae-efficiency")
def get_qae_efficiency() -> list[dict[str, float | int]]:
	if "qae_efficiency" not in _cached_results:
		graph = get_graph()
		origin, destination = next(iter(graph.edges()))
		bin_edges, probabilities = build_travel_time_distribution(
			graph,
			origin=origin,
			dest=destination,
			sim_duration_sec=3600,
			seed=1,
		)
		bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
		threshold_sec = float(np.median(bin_centers))
		true_probability = float(probabilities[bin_centers <= threshold_sec].sum())
		_cached_results["qae_efficiency"] = run_qae_efficiency_benchmark(
			bin_edges,
			probabilities,
			threshold_sec=threshold_sec,
			true_probability=true_probability,
		)
	return _cached_results["qae_efficiency"]
