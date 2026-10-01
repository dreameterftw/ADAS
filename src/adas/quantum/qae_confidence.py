"""Estimate route on-time probability with iterative amplitude estimation."""

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from qiskit_algorithms import EstimationProblem, IterativeAmplitudeEstimation
from qiskit_aer.primitives import Sampler as AerSampler


def _normalize_probabilities(probabilities: np.ndarray) -> np.ndarray:
	values = np.asarray(probabilities, dtype=float)
	if values.ndim != 1 or values.size == 0:
		raise ValueError("probabilities must be a non-empty one-dimensional array")
	if not np.all(np.isfinite(values)) or np.any(values < 0):
		raise ValueError("probabilities must be finite and non-negative")
	total = float(values.sum())
	if not math.isfinite(total) or total <= 0:
		raise ValueError("probabilities must have a positive finite sum")
	return values / total


def build_distribution_loader(
	probabilities: np.ndarray,
	num_qubits: int,
) -> QuantumCircuit:
	"""Prepare amplitudes whose squared magnitudes match the probabilities."""
	if num_qubits < 1:
		raise ValueError("num_qubits must be at least 1")
	normalized = _normalize_probabilities(probabilities)
	target_length = 1 << num_qubits
	if normalized.size > target_length:
		raise ValueError("num_qubits cannot represent all probability bins")

	amplitudes = np.pad(
		np.sqrt(normalized),
		(0, target_length - normalized.size),
	)
	circuit = QuantumCircuit(num_qubits)
	circuit.append(StatePreparation(amplitudes), range(num_qubits))
	return circuit


def estimate_on_time_probability(
	bin_edges: np.ndarray,
	probabilities: np.ndarray,
	threshold_sec: float,
	epsilon_target: float = 0.01,
) -> float:
	"""Estimate the probability that a bin midpoint is within the threshold."""
	edges = np.asarray(bin_edges, dtype=float)
	if edges.ndim != 1 or edges.size < 2:
		raise ValueError("bin_edges must be a one-dimensional array with at least two values")
	if not np.all(np.isfinite(edges)) or np.any(np.diff(edges) <= 0):
		raise ValueError("bin_edges must be finite and strictly increasing")
	if edges.size != np.asarray(probabilities).size + 1:
		raise ValueError("bin_edges must contain exactly one more value than probabilities")
	if not math.isfinite(threshold_sec):
		raise ValueError("threshold_sec must be finite")
	if not math.isfinite(epsilon_target) or not 0 < epsilon_target < 0.5:
		raise ValueError("epsilon_target must be finite and between 0 and 0.5")

	probability_values = _normalize_probabilities(probabilities)
	num_qubits = max(1, math.ceil(math.log2(probability_values.size)))
	state_preparation = build_distribution_loader(probability_values, num_qubits)
	bin_centers = edges[:-1] + np.diff(edges) / 2
	good_indices = np.flatnonzero(bin_centers <= threshold_sec)

	# The comparator is reversible so amplitude estimation can invert the full
	# state-preparation circuit when constructing its Grover operator.
	circuit = QuantumCircuit(num_qubits + 1)
	circuit.compose(state_preparation, qubits=range(num_qubits), inplace=True)
	for index in good_indices:
		for qubit in range(num_qubits):
			if not (index >> qubit) & 1:
				circuit.x(qubit)
		circuit.mcx(list(range(num_qubits)), num_qubits)
		for qubit in range(num_qubits):
			if not (index >> qubit) & 1:
				circuit.x(qubit)

	problem = EstimationProblem(
		state_preparation=circuit.decompose(reps=10),
		objective_qubits=[num_qubits],
	)
	estimator = IterativeAmplitudeEstimation(
		epsilon_target=epsilon_target,
		alpha=0.05,
		sampler=AerSampler(run_options={"seed": 1}),
	)
	result = estimator.estimate(problem)
	return float(result.estimation)
