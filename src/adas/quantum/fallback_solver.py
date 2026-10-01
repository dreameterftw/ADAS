"""Run QAOA with a bounded wait and a classical simulated-annealing fallback."""

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import math
from time import perf_counter
from typing import TypedDict

import networkx as nx
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import OptimizationResultStatus

from adas.baselines.base import Assignment
from adas.baselines.sim_annealing import SimulatedAnnealingDispatch
from adas.quantum.qaoa_solver import solve_with_qaoa
from adas.simulation.incidents import Ambulance, Incident


class FallbackResult(TypedDict, total=False):
	method: str
	cost: float
	assignment: list[Assignment]
	solve_time_sec: float
	fallback_reason: str


class SolverTimeout(TimeoutError):
	"""Raised when QAOA exceeds the caller's time budget."""


def _decode_qaoa_result(
	program: QuadraticProgram,
	graph: nx.MultiDiGraph,
	incidents: list[Incident],
	ambulances: list[Ambulance],
	result,
) -> list[Assignment]:
	if result.status != OptimizationResultStatus.SUCCESS or result.fval is None:
		raise ValueError("QAOA did not return a successful result with an objective value")
	expected_variable_names = [variable.name for variable in program.variables]
	if (
		result.x is None
		or len(result.x) != program.get_num_vars()
		or result.variable_names != expected_variable_names
	):
		raise ValueError("QAOA returned no complete solution vector")
	incident_by_id = {incident.id: incident for incident in incidents}
	ambulance_by_id = {ambulance.id: ambulance for ambulance in ambulances}
	assignments: list[Assignment] = []
	used_incidents: set[int] = set()
	used_ambulances: set[int] = set()
	for name, value in zip(result.variable_names, result.x, strict=True):
		if min(abs(float(value)), abs(float(value) - 1.0)) > 1e-5:
			raise ValueError("QAOA returned a non-binary assignment value")
		if float(value) < 0.5:
			continue
		parts = name.split("_")
		if len(parts) != 3 or parts[0] != "x":
			raise ValueError(f"unexpected assignment variable name: {name}")
		incident_id, ambulance_id = int(parts[1]), int(parts[2])
		if incident_id not in incident_by_id or ambulance_id not in ambulance_by_id:
			raise ValueError("QAOA selected an unknown incident or ambulance")
		if incident_id in used_incidents or ambulance_id in used_ambulances:
			raise ValueError("QAOA returned conflicting assignments")
		ambulance = ambulance_by_id[ambulance_id]
		if not ambulance.available:
			raise ValueError("QAOA selected an unavailable ambulance")
		incident = incident_by_id[incident_id]
		try:
			travel_time = float(
				nx.shortest_path_length(
					graph,
					ambulance.current_node,
					incident.location_node,
					weight="travel_time",
				)
			)
		except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
			raise ValueError("QAOA selected an unreachable assignment") from error
		used_incidents.add(incident_id)
		used_ambulances.add(ambulance_id)
		assignments.append(Assignment(incident_id, ambulance_id, travel_time))
	if not assignments and incidents and ambulances:
		for incident in incidents:
			for ambulance in ambulances:
				try:
					nx.shortest_path_length(
						graph,
						ambulance.current_node,
						incident.location_node,
						weight="travel_time",
					)
				except (nx.NetworkXNoPath, nx.NodeNotFound):
					continue
				raise ValueError("QAOA returned an empty dispatch despite reachable routes")
	return assignments


def _weighted_cost(
	assignments: list[Assignment],
	incidents: list[Incident],
) -> float:
	incidents_by_id = {incident.id: incident for incident in incidents}
	return sum(
	assignment.travel_time_sec * (6 - incidents_by_id[assignment.incident_id].severity)
		for assignment in assignments
	)


def _run_fallback(
	graph: nx.MultiDiGraph,
	incidents: list[Incident],
	ambulances: list[Ambulance],
	reason: str,
	started_at: float,
) -> FallbackResult:
	assignments = SimulatedAnnealingDispatch(iterations=1500, seed=42).solve(
		graph,
		incidents,
		ambulances,
	)
	return {
		"method": "simulated_annealing_fallback",
		"fallback_reason": reason,
		"cost": _weighted_cost(assignments, incidents),
		"assignment": assignments,
		"solve_time_sec": perf_counter() - started_at,
	}


def solve_with_fallback(
	program: QuadraticProgram,
	graph: nx.MultiDiGraph,
	incidents: list[Incident],
	ambulances: list[Ambulance],
	timeout_sec: float = 10.0,
) -> FallbackResult:
	"""Run QAOA with a timeout, falling back on errors or invalid output.

	The timeout bounds how long this caller waits. Python cannot forcibly stop a
	QAOA call already executing in the worker thread, so it may finish in the
	background after the classical fallback has returned.
	"""
	if not math.isfinite(timeout_sec) or timeout_sec <= 0:
		raise ValueError("timeout_sec must be finite and positive")
	started_at = perf_counter()
	executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="adas-qaoa")
	future: Future = executor.submit(solve_with_qaoa, program, use_warm_start=True)
	try:
		result = future.result(timeout=timeout_sec)
		assignments = _decode_qaoa_result(
			program,
			graph,
			incidents,
			ambulances,
			result,
		)
	except FutureTimeoutError:
		future.cancel()
		executor.shutdown(wait=False, cancel_futures=True)
		return _run_fallback(
			graph,
			incidents,
			ambulances,
			"timeout",
			started_at,
		)
	except Exception as error:
		executor.shutdown(wait=True)
		return _run_fallback(
			graph,
			incidents,
			ambulances,
			f"{type(error).__name__}: {error}",
			started_at,
		)
	executor.shutdown(wait=True)
	return {
		"method": "qaoa",
		"cost": _weighted_cost(assignments, incidents),
		"assignment": assignments,
		"solve_time_sec": perf_counter() - started_at,
	}