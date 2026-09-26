"""QAOA solver integration with CVaR and optional continuous warm start."""

import math

from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_aer.primitives import Sampler as AerSampler
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import (
	MinimumEigenOptimizer,
	WarmStartQAOAOptimizer,
)


def _effective_penalty(qp: QuadraticProgram, minimum_penalty: float) -> float:
	"""Choose a penalty larger than the objective's full binary range."""
	linear_bound = sum(abs(value) for value in qp.objective.linear.to_dict().values())
	quadratic_bound = sum(
		abs(value) for value in qp.objective.quadratic.to_dict().values()
	)
	return max(minimum_penalty, linear_bound + quadratic_bound + 1.0)


def solve_with_qaoa(
	qp: QuadraticProgram,
	reps: int = 2,
	use_warm_start: bool = True,
	penalty: float = 1000.0,
):
	"""Solve a constrained dispatch model with QAOA."""
	if reps < 1:
		raise ValueError("reps must be at least 1")
	if not math.isfinite(penalty) or penalty <= 0:
		raise ValueError("penalty must be a finite positive number")
	penalty = _effective_penalty(qp, penalty)

	qaoa = QAOA(
		sampler=AerSampler(run_options={"seed": 1}),
		optimizer=COBYLA(maxiter=150),
		reps=reps,
		aggregation=0.25,
	)

	if use_warm_start:
		from qiskit_optimization.algorithms import SlsqpOptimizer

		optimizer = WarmStartQAOAOptimizer(
			pre_solver=SlsqpOptimizer(),
			relax_for_pre_solver=True,
			qaoa=qaoa,
			epsilon=0.25,
			penalty=penalty,
		)
	else:
		optimizer = MinimumEigenOptimizer(qaoa, penalty=penalty)

	return optimizer.solve(qp)
