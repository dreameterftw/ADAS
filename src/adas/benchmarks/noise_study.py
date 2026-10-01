"""Illustrative Aer noise study for QAOA dispatch problems."""

import math

from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_aer.primitives import Sampler as AerSampler
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import (
	MinimumEigenOptimizer,
	OptimizationResultStatus,
)

def build_simple_noise_model(
	single_qubit_error: float = 0.001,
	two_qubit_error: float = 0.01,
) -> NoiseModel:
	"""Build a simplified depolarizing and readout noise model, not a device calibration."""
	for rate in (single_qubit_error, two_qubit_error):
		if not math.isfinite(rate) or not 0 <= rate <= 1:
			raise ValueError("noise rates must be finite and between 0 and 1")

	noise_model = NoiseModel()
	noise_model.add_all_qubit_quantum_error(
		depolarizing_error(single_qubit_error, 1),
		["u"],
	)
	noise_model.add_all_qubit_quantum_error(
		depolarizing_error(two_qubit_error, 2),
		["cx"],
	)
	readout_error = ReadoutError(
		[
			[1 - single_qubit_error, single_qubit_error],
			[single_qubit_error, 1 - single_qubit_error],
		]
	)
	noise_model.add_all_qubit_readout_error(readout_error)
	return noise_model


def solve_with_noisy_qaoa(
	program: QuadraticProgram,
	noise_model: NoiseModel,
	reps: int = 2,
):
	"""Solve one QUBO with noisy QAOA using Aer-supported u/cx basis gates."""
	if reps < 1:
		raise ValueError("reps must be at least 1")
	noisy_sampler = AerSampler(
		backend_options={"noise_model": noise_model},
		run_options={"seed": 1},
	)
	qaoa = QAOA(
		sampler=noisy_sampler,
		optimizer=COBYLA(maxiter=100),
		reps=reps,
		initial_point=[0.1] * (2 * reps),
		aggregation=0.25,
	)
	linear_bound = sum(abs(value) for value in program.objective.linear.to_dict().values())
	quadratic_bound = sum(
		abs(value) for value in program.objective.quadratic.to_dict().values()
	)
	penalty = max(1000.0, linear_bound + quadratic_bound + 1.0)
	return MinimumEigenOptimizer(qaoa, penalty=penalty).solve(program)


def run_noise_degradation_study(
	program: QuadraticProgram,
	error_rates: list[tuple[float, float]],
) -> list[dict[str, float]]:
	"""Run noiseless and noisy QAOA for (single-qubit, two-qubit) error rates."""
	if not error_rates:
		raise ValueError("error_rates must contain at least one pair")
	results: list[dict[str, float]] = []
	for single_error, two_error in error_rates:
		if single_error == 0 and two_error == 0:
			noise_model = NoiseModel()
		else:
			noise_model = build_simple_noise_model(single_error, two_error)
		result = solve_with_noisy_qaoa(program, noise_model)
		if result.fval is None:
			raise RuntimeError("QAOA returned no objective value")
		feasible_samples = [
			sample
			for sample in (result.samples or [])
			if sample.status == OptimizationResultStatus.SUCCESS
		]
		feasible_probability = sum(sample.probability for sample in feasible_samples)
		if feasible_probability <= 0:
			raise RuntimeError("QAOA produced no feasible sampled solutions")
		best_feasible_cost = min(sample.fval for sample in feasible_samples)
		optimal_solution_probability = sum(
			sample.probability
			for sample in feasible_samples
			if math.isclose(sample.fval, best_feasible_cost, abs_tol=1e-9)
		)
		expected_regret = sum(
			(sample.fval - best_feasible_cost) * sample.probability
			for sample in feasible_samples
		) / feasible_probability
		results.append(
			{
				"single_qubit_error": single_error,
				"two_qubit_error": two_error,
				"cost": float(expected_regret),
				"best_feasible_cost": float(best_feasible_cost),
				"feasible_probability": float(feasible_probability),
				"optimal_solution_probability": float(optimal_solution_probability),
			}
		)
	return results