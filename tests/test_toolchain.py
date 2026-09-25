"""Phase 2: Toolchain verification.

Run: pytest tests/test_toolchain.py -v -s
If any of these fail, fix versions before proceeding to Phase 3+.
"""

import numpy as np


def test_aer_basic_execution():
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])

    sim = AerSimulator()
    result = sim.run(qc, shots=1000).result()
    counts = result.get_counts()
    print("Aer basic execution counts:", counts)
    assert "00" in counts or "11" in counts


def test_qubo_build_and_classical_solve():
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_algorithms import NumPyMinimumEigensolver

    qp = QuadraticProgram(name="toy_dispatch")
    qp.binary_var("x0")
    qp.binary_var("x1")
    qp.binary_var("x2")
    qp.minimize(linear={"x0": -1, "x1": -2, "x2": -1})
    qp.linear_constraint(
        linear={"x0": 1, "x1": 1, "x2": 1},
        sense="==",
        rhs=1,
        name="one_hot",
    )

    solver = MinimumEigenOptimizer(NumPyMinimumEigensolver())
    result = solver.solve(qp)
    print("Classical QUBO solve result:", result.x, result.fval)
    assert result.x[1] == 1


def test_qaoa_on_aer():
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit_aer.primitives import Sampler as AerSampler

    qp = QuadraticProgram(name="toy_qaoa")
    qp.binary_var("x0")
    qp.binary_var("x1")
    qp.binary_var("x2")
    qp.minimize(linear={"x0": -1, "x1": -2, "x2": -1})
    qp.linear_constraint(
        linear={"x0": 1, "x1": 1, "x2": 1},
        sense="==",
        rhs=1,
        name="one_hot",
    )

    qaoa = QAOA(sampler=AerSampler(), optimizer=COBYLA(maxiter=100), reps=2)
    solver = MinimumEigenOptimizer(qaoa)
    result = solver.solve(qp)
    print("QAOA solve result:", result.x, result.fval)
    assert result.x is not None


def test_amplitude_estimation_runs():
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import RYGate
    from qiskit_algorithms import EstimationProblem, IterativeAmplitudeEstimation
    from qiskit_aer.primitives import Sampler as AerSampler

    p_true = 0.3
    theta = 2 * np.arcsin(np.sqrt(p_true))

    state_preparation = QuantumCircuit(1)
    state_preparation.append(RYGate(theta), [0])

    problem = EstimationProblem(
        state_preparation=state_preparation,
        objective_qubits=[0],
    )

    iae = IterativeAmplitudeEstimation(
        epsilon_target=0.01,
        alpha=0.05,
        sampler=AerSampler(),
    )
    result = iae.estimate(problem)
    print(f"QAE estimate: {result.estimation:.4f} (true: {p_true})")
    assert abs(result.estimation - p_true) < 0.05
