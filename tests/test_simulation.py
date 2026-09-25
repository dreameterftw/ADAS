"""Tests for road-network helpers and synthetic traffic scenarios."""

import networkx as nx
import pytest

from adas.simulation.incidents import generate_ambulance_fleet, generate_incidents
from adas.simulation.lightweight_sim import congestion_factor, travel_time_at
from adas.simulation.network import get_intersections, shortest_travel_time


def make_test_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.add_edge(1, 2, travel_time=10.0)
    graph.add_edge(2, 3, travel_time=20.0)
    graph.add_edge(1, 3, travel_time=40.0)
    graph.add_edge(2, 1, travel_time=10.0)
    return graph


def test_incidents_and_fleet_are_seeded_and_in_bounds():
    graph = make_test_graph()
    incidents = generate_incidents(graph, count=5, sim_duration_sec=1000, seed=1)
    fleet = generate_ambulance_fleet(graph, fleet_size=3, seed=1)

    assert incidents == generate_incidents(graph, 5, 1000, seed=1)
    assert all(0 <= incident.timestamp <= 1000 for incident in incidents)
    assert all(incident.location_node in graph for incident in incidents)
    assert all(ambulance.current_node in graph for ambulance in fleet)


def test_network_helpers_and_lightweight_travel_time():
    graph = make_test_graph()

    assert shortest_travel_time(graph, 1, 3) == 30.0
    assert get_intersections(graph) == [1, 2]
    assert get_intersections(graph, limit=1) == [1]
    assert congestion_factor(500, 1000) > congestion_factor(0, 1000)
    assert travel_time_at(graph, 1, 3, 500, 1000) == 75.0


def test_generators_reject_invalid_empty_graph_requests():
    graph = nx.MultiDiGraph()

    with pytest.raises(ValueError):
        generate_incidents(graph, count=1, sim_duration_sec=100)
    with pytest.raises(ValueError):
        generate_ambulance_fleet(graph, fleet_size=1)


@pytest.mark.integration
def test_network_loads_with_sane_size():
    from adas.simulation.incidents import generate_incidents
    from adas.simulation.network import load_city_network

    graph = load_city_network("Andheri, Mumbai, India")
    incidents = generate_incidents(graph, count=5, sim_duration_sec=1000, seed=1)

    assert 100 < len(graph.nodes) < 20000
    assert all(0 <= incident.timestamp <= 1000 for incident in incidents)
    assert all(incident.location_node in graph for incident in incidents)