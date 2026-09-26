"""Exhaustive verifier for small constrained quadratic programs."""

import itertools

from qiskit_optimization import QuadraticProgram


def brute_force_solve(qp: QuadraticProgram) -> tuple[list[int] | None, float]:
	"""Return the best feasible bit vector and objective for a small program."""
	num_vars = qp.get_num_vars()
	best_x: list[int] | None = None
	best_value = float("inf")

	for bits in itertools.product([0, 1], repeat=num_vars):
		x = list(bits)
		feasible = True
		for constraint in qp.linear_constraints:
			lhs = sum(
				constraint.linear.to_dict().get(index, 0) * x[index]
				for index in range(num_vars)
			)
			if constraint.sense.name == "LE" and lhs > constraint.rhs:
				feasible = False
				break
			if constraint.sense.name == "GE" and lhs < constraint.rhs:
				feasible = False
				break
			if constraint.sense.name == "EQ" and lhs != constraint.rhs:
				feasible = False
				break
		if not feasible:
			continue

		value = float(qp.objective.evaluate(x))
		if value < best_value:
			best_x, best_value = x, value

	return best_x, best_value