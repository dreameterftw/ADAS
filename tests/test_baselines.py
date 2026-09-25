"""Classical dispatch baseline tests."""

import networkx as nx
import pytest

from adas.baselines.base import Assignment
from adas.baselines.closest_idle import ClosestIdleDispatch
from adas.baselines.fixed_time import fixed_time_delay_penalty
from adas.baselines.sim_annealing import SimulatedAnnealingDispatch
from adas.simulation.incidents import Ambulance, Incident


def make_test_graph() -> nx.MultiDiGraph:
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=10.0)
	graph.add_edge(2, 1, travel_time=10.0)
	graph.add_edge(2, 3, travel_time=10.0)
	graph.add_edge(3, 2, travel_time=10.0)
	graph.add_edge(3, 4, travel_time=10.0)
	graph.add_edge(4, 3, travel_time=10.0)
	return graph


def test_closest_idle_assigns_nearest_and_skips_busy_units():
	graph = make_test_graph()
	incidents = [Incident(1, 2, 3, 0), Incident(2, 4, 2, 1)]
	ambulances = [Ambulance(10, 1), Ambulance(11, 4, available=False)]

	result = ClosestIdleDispatch().solve(graph, incidents, ambulances)

	assert result == [Assignment(1, 10, 10.0)]


def test_sim_annealing_produces_valid_unique_assignments():
	graph = make_test_graph()
	incidents = [Incident(1, 2, 5, 0), Incident(2, 4, 1, 1)]
	ambulances = [Ambulance(10, 1), Ambulance(11, 4)]

	result = SimulatedAnnealingDispatch(iterations=200, seed=1).solve(
		graph,
		incidents,
		ambulances,
	)

	assert len(result) == len(incidents)
	assert len({assignment.ambulance_id for assignment in result}) == len(result)
	assert all(assignment.travel_time_sec >= 0 for assignment in result)


def test_fixed_time_penalty_is_seeded_and_validates_input():
	assert fixed_time_delay_penalty(3, seed=1) == fixed_time_delay_penalty(3, seed=1)
	assert fixed_time_delay_penalty(0, seed=1) == 0.0
	with pytest.raises(ValueError):
		fixed_time_delay_penalty(-1)
