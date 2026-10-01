"""Tests for the rolling simulation API."""

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from adas import app_state
from adas.api.main import app
from adas.baselines.base import Assignment
from adas.orchestrator import Orchestrator
from adas.simulation.clock import SimulationState
from adas.simulation.incidents import Ambulance, Incident


@pytest.fixture
def client_and_state(monkeypatch: pytest.MonkeyPatch):
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=15.0)
	graph.add_edge(2, 1, travel_time=15.0)
	state = SimulationState(
		pending_incidents=[
			Incident(100, 2, 5, 120.0),
			Incident(101, 2, 4, 900.0),
		],
		ambulances=[Ambulance(10, 1)],
	)
	orchestrator = Orchestrator(graph)
	monkeypatch.setattr(app_state, "_graph", graph)
	monkeypatch.setattr(app_state, "_state", state)
	monkeypatch.setattr(app_state, "_orchestrator", orchestrator)
	with TestClient(app) as client:
		yield client, state


def test_health_check(client_and_state):
	client, _ = client_and_state

	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_tick_and_replan_flow(client_and_state):
	client, state = client_and_state

	tick_response = client.post("/incidents/tick", params={"dt_seconds": 600})

	assert tick_response.status_code == 200
	assert tick_response.json() == {
		"current_time": 600.0,
		"newly_active_count": 1,
	}
	assert [incident["id"] for incident in client.get("/incidents/active").json()] == [100]

	replan_response = client.post("/assignments/replan")

	assert replan_response.status_code == 200
	assert replan_response.json() == [
		{
			"incident_id": 100,
			"ambulance_id": 10,
			"travel_time_sec": 15.0,
		}
	]
	assert state.ambulances[0].available is False

	second_replan = client.post("/assignments/replan")
	assert second_replan.status_code == 200
	assert len(second_replan.json()) == 1
	assert state.ambulances[0].available is False

	state.resolve_incident(100, 10)
	assert state.resolved_incident_ids == {100}
	assert state.active_incidents == []
	assert state.ambulances[0].available is True


def test_tick_rejects_negative_duration(client_and_state):
	client, _ = client_and_state

	response = client.post("/incidents/tick", params={"dt_seconds": -1})

	assert response.status_code == 422


def test_simulation_clock_activates_due_incidents_in_time_order():
	state = SimulationState(
		pending_incidents=[
			Incident(2, 2, 2, 20.0),
			Incident(1, 1, 3, 10.0),
		],
	)

	first_tick = state.tick(10.0)
	second_tick = state.tick(10.0)

	assert [incident.id for incident in first_tick] == [1]
	assert [incident.id for incident in second_tick] == [2]
	assert state.current_time == 20.0


def test_resolve_releases_only_the_assigned_ambulance():
	state = SimulationState(
		active_incidents=[Incident(1, 2, 3, 0.0)],
		ambulances=[Ambulance(10, 1, available=False)],
		assignments={1: Assignment(1, 10, 15.0)},
	)

	state.resolve_incident(1, 10)

	assert state.assignments == {}
	assert state.ambulances[0].available is True
	assert state.resolved_incident_ids == {1}


def test_resolve_rejects_mismatched_ambulance():
	state = SimulationState(
		active_incidents=[Incident(1, 2, 3, 0.0)],
		ambulances=[Ambulance(10, 1, available=False), Ambulance(11, 2)],
		assignments={1: Assignment(1, 10, 15.0)},
	)

	with pytest.raises(ValueError, match="assigned to another ambulance"):
		state.resolve_incident(1, 11)
