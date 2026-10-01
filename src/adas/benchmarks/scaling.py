"""Compare dispatch quality and runtime as assignment problems grow."""

from time import perf_counter

import networkx as nx
from qiskit_optimization.algorithms import OptimizationResultStatus

from adas.baselines.sim_annealing import SimulatedAnnealingDispatch
from adas.quantum.qubo import build_dispatch_qubo
from adas.quantum.qaoa_solver import solve_with_qaoa
from adas.quantum.verify import brute_force_solve
from adas.simulation.incidents import Ambulance, Incident, generate_ambulance_fleet, generate_incidents


def _weighted_assignment_cost(
	graph: nx.MultiDiGraph,
	incidents: list[Incident],
	ambulances: list[Ambulance],
	variable_names: list[str],
	values: list[float],
) -> float:
	incidents_by_id = {incident.id: incident for incident in incidents}
	ambulances_by_id = {ambulance.id: ambulance for ambulance in ambulances}
	cost = 0.0
	for name, value in zip(variable_names, values):
		if value < 0.5:
			continue
		_, incident_id, ambulance_id = name.split("_", maxsplit=2)
		incident = incidents_by_id[int(incident_id)]
		ambulance = ambulances_by_id[int(ambulance_id)]
		travel_time = nx.shortest_path_length(
			graph,
			ambulance.current_node,
			incident.location_node,
			weight="travel_time",
		)
		cost += float(travel_time) * (6 - incident.severity)
	return cost


def _is_feasible(program, values: list[float] | None) -> bool:
	if values is None or len(values) != program.get_num_vars():
		return False
	if any(min(abs(value), abs(value - 1)) > 1e-8 for value in values):
		return False
	for constraint in program.linear_constraints:
		lhs = sum(
			coefficient * values[index]
			for index, coefficient in constraint.linear.to_dict().items()
		)
		if constraint.sense.name == "LE" and lhs > constraint.rhs + 1e-8:
			return False
		if constraint.sense.name == "GE" and lhs < constraint.rhs - 1e-8:
			return False
		if constraint.sense.name == "EQ" and abs(lhs - constraint.rhs) > 1e-8:
			return False
	return True


def run_scaling_benchmark(
	graph: nx.MultiDiGraph,
	sizes: list[int],
	seed: int = 42,
	sa_iterations: int = 2000,
) -> list[dict[str, int | float]]:
	"""Return comparable severity-weighted costs and runtimes for each size."""
	if not sizes:
		raise ValueError("sizes must contain at least one problem size")
	if any(isinstance(size, bool) or not isinstance(size, int) or size < 1 for size in sizes):
		raise ValueError("sizes must contain positive integers")
	if sa_iterations < 0:
		raise ValueError("sa_iterations must be non-negative")
	if graph.number_of_nodes() == 0:
		raise ValueError("graph must contain nodes")

	results: list[dict[str, int | float]] = []
	for size in sizes:
		incidents = generate_incidents(graph, size, sim_duration_sec=3600, seed=seed)
		ambulances = generate_ambulance_fleet(graph, size, seed=seed)
		program = build_dispatch_qubo(graph, incidents, ambulances)

		start = perf_counter()
		qaoa_result = solve_with_qaoa(program, use_warm_start=True)
		qaoa_time = perf_counter() - start
		returned_feasible = _is_feasible(program, qaoa_result.x)
		returned_cost = (
			_weighted_assignment_cost(
				graph,
				incidents,
				ambulances,
				qaoa_result.variable_names,
				qaoa_result.x,
			)
			if qaoa_result.x is not None
			else None
		)
		feasible_samples = [
			sample
			for sample in (qaoa_result.samples or [])
			if sample.status == OptimizationResultStatus.SUCCESS
		]
		best_feasible_sample = min(feasible_samples, key=lambda sample: sample.fval, default=None)
		qaoa_cost = (
			_weighted_assignment_cost(
				graph,
				incidents,
				ambulances,
				qaoa_result.variable_names,
				best_feasible_sample.x,
			)
			if best_feasible_sample is not None
			else returned_cost if returned_feasible else None
		)

		start = perf_counter()
		sa_assignments = SimulatedAnnealingDispatch(
			iterations=sa_iterations,
			seed=seed,
		).solve(graph, incidents, ambulances)
		sa_time = perf_counter() - start
		incidents_by_id = {incident.id: incident for incident in incidents}
		sa_cost = sum(
			assignment.travel_time_sec
			* (6 - incidents_by_id[assignment.incident_id].severity)
			for assignment in sa_assignments
		)

		row: dict[str, int | float | bool | None] = {
			"n": size,
			"num_qubits": program.get_num_vars(),
			"qaoa_cost": qaoa_cost,
			"qaoa_objective_value": (
				float(best_feasible_sample.fval)
				if best_feasible_sample is not None
				else None
			),
			"qaoa_returned_cost": returned_cost,
			"qaoa_returned_feasible": returned_feasible,
			"qaoa_feasible_sample_probability": sum(
				sample.probability for sample in feasible_samples
			),
			"qaoa_time_sec": qaoa_time,
			"sa_cost": sa_cost,
			"sa_time_sec": sa_time,
		}
		if size <= 3:
			start = perf_counter()
			brute_force_x, _ = brute_force_solve(program)
			brute_force_time = perf_counter() - start
			if brute_force_x is None:
				raise RuntimeError(f"brute force found no feasible solution for size {size}")
			row["brute_force_cost"] = _weighted_assignment_cost(
				graph,
				incidents,
				ambulances,
				[variable.name for variable in program.variables],
				brute_force_x,
			)
			row["brute_force_time_sec"] = brute_force_time
		results.append(row)
	return results