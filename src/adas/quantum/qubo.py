"""Build a dispatch-only assignment model for QUBO-based optimization."""

import networkx as nx
from qiskit_optimization import QuadraticProgram

from adas.simulation.incidents import Ambulance, Incident


def build_dispatch_qubo(
	graph: nx.MultiDiGraph,
	incidents: list[Incident],
	ambulances: list[Ambulance],
) -> QuadraticProgram:
	"""Build a maximum-cardinality, severity-weighted dispatch model."""
	incident_ids = [incident.id for incident in incidents]
	ambulance_ids = [ambulance.id for ambulance in ambulances]
	if len(set(incident_ids)) != len(incident_ids):
		raise ValueError("incident IDs must be unique")
	if len(set(ambulance_ids)) != len(ambulance_ids):
		raise ValueError("ambulance IDs must be unique")

	qp = QuadraticProgram(name="dispatch_assignment")
	var_names: dict[tuple[int, int], str] = {}
	for incident in incidents:
		for ambulance in ambulances:
			name = f"x_{incident.id}_{ambulance.id}"
			qp.binary_var(name)
			var_names[(incident.id, ambulance.id)] = name

	pair_costs: dict[tuple[int, int], float] = {}
	unreachable_pairs: list[tuple[int, int]] = []
	for incident in incidents:
		for ambulance in ambulances:
			try:
				travel_time = nx.shortest_path_length(
					graph,
					ambulance.current_node,
					incident.location_node,
					weight="travel_time",
				)
			except (nx.NetworkXNoPath, nx.NodeNotFound):
				unreachable_pairs.append((incident.id, ambulance.id))
				continue
			pair_costs[(incident.id, ambulance.id)] = (
				float(travel_time) * incident.severity
			)

	max_assignments = min(len(incidents), len(ambulances))
	max_pair_cost = max(pair_costs.values(), default=0.0)
	assignment_reward = max_assignments * max_pair_cost + 1.0
	linear = {
		var_names[pair]: cost - assignment_reward
		for pair, cost in pair_costs.items()
	}
	linear.update(
		{var_names[pair]: 1e6 for pair in unreachable_pairs}
	)
	qp.minimize(linear=linear)

	for incident_id, ambulance_id in unreachable_pairs:
		qp.linear_constraint(
			linear={var_names[(incident_id, ambulance_id)]: 1},
			sense="==",
			rhs=0,
			name=f"unreachable_{incident_id}_{ambulance_id}",
		)

	for incident in incidents:
		coefficients = {
			var_names[(incident.id, ambulance.id)]: 1
			for ambulance in ambulances
		}
		if coefficients:
			qp.linear_constraint(
				linear=coefficients,
				sense="<=",
				rhs=1,
				name=f"incident_{incident.id}_atmost1",
			)

	for ambulance in ambulances:
		coefficients = {
			var_names[(incident.id, ambulance.id)]: 1
			for incident in incidents
		}
		if coefficients:
			qp.linear_constraint(
				linear=coefficients,
				sense="<=",
				rhs=1,
				name=f"ambulance_{ambulance.id}_atmost1",
			)

	return qp
