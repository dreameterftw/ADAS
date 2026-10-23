"""Tests for the rolling simulation API."""

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from adas import app_state
from adas.api import main as main_module
from adas.api.main import app
from adas.api.routes import benchmarks as benchmark_routes
from adas.api.routes import map_data as map_data_routes
from adas.api.routes import operations as operations_routes
from adas.baselines.base import Assignment
from adas.hospitals.matching import Hospital
from adas.orchestrator import Orchestrator
from adas.simulation.clock import SimulationState
from adas.simulation.incidents import Ambulance, Incident
from adas.simulation.network import open_road_travel_time
from adas.zones import zone_solver


@pytest.fixture
def client_and_state(monkeypatch: pytest.MonkeyPatch):
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=15.0)
	graph.add_edge(2, 1, travel_time=15.0)
	graph.nodes[1].update(x=72.8, y=19.1)
	graph.nodes[2].update(x=72.9, y=19.2)
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
	monkeypatch.setattr(
		app_state,
		"_hospitals",
		[Hospital(7, 2, {"trauma"}, 3, 10)],
	)
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
	active_incidents = client.get("/incidents/active").json()
	assert [incident["id"] for incident in active_incidents] == [100]
	assert active_incidents[0]["lat"] == 19.2
	assert active_incidents[0]["lon"] == 72.9
	decision_counts_before = client.get("/benchmarks/decisions").json()

	replan_response = client.post("/assignments/replan")

	assert replan_response.status_code == 200
	assert replan_response.json() == [
		{
			"incident_id": 100,
			"ambulance_id": 10,
			"travel_time_sec": 15.0,
			"coordination_reason": "in_zone",
			"solver_method": "qaoa",
			"fallback_reason": None,
			"assignment_reason": "Severity 5 priority was considered; QAOA selected this available unit for an estimated 1-minute response under normal traffic conditions. Hospital 7 has a preferred specialty and 3 reported available beds.",
			"hospital_id": 7,
			"hospital_match_reason": "specialty_and_capacity",
			"hospital_available_beds": 3,
			"hospital_specialties": ["trauma"],
			"hospital_lat": 19.2,
			"hospital_lon": 72.9,
			"route": [[19.1, 72.8], [19.2, 72.9]],
		}
	]
	decision_counts_after = client.get("/benchmarks/decisions").json()
	decision_key = (
		"qaoa"
		if replan_response.json()[0]["solver_method"] == "qaoa"
		else "fallback"
	)
	assert decision_counts_after[decision_key] == decision_counts_before[decision_key] + 1
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


def test_resolve_incident_releases_its_ambulance(client_and_state):
	client, state = client_and_state
	state.active_incidents.append(Incident(102, 2, 3, 0.0))
	state.assignments[102] = Assignment(102, 10, 15.0)
	state.ambulances[0].available = False

	response = client.post("/incidents/102/resolve", params={"ambulance_id": 10})

	assert response.status_code == 200
	assert response.json() == {
		"incident_id": 102,
		"ambulance_id": 10,
		"status": "resolved",
	}
	assert state.resolved_incident_ids == {102}
	assert state.active_incidents == []
	assert state.assignments == {}
	assert state.ambulances[0].available is True


def test_resolve_incident_rejects_unassigned_ambulance(client_and_state):
	client, state = client_and_state
	state.active_incidents.append(Incident(102, 2, 3, 0.0))
	state.assignments[102] = Assignment(102, 10, 15.0)
	state.ambulances.append(Ambulance(11, 2, available=False))

	response = client.post("/incidents/102/resolve", params={"ambulance_id": 11})

	assert response.status_code == 409
	assert "assigned to another ambulance" in response.json()["detail"]
	assert any(incident.id == 102 for incident in state.active_incidents)


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


def test_orchestrator_uses_and_reports_per_zone_fallback(monkeypatch: pytest.MonkeyPatch):
	graph = nx.MultiDiGraph()
	graph.add_edge(1, 2, travel_time=15.0)
	incident = Incident(1, 2, 5, 0.0)
	ambulance = Ambulance(10, 1)
	state = SimulationState(active_incidents=[incident], ambulances=[ambulance])
	captured: dict[str, object] = {}

	def fallback_stub(program, selected_graph, incidents, ambulances, timeout_sec):
		captured["timeout_sec"] = timeout_sec
		return {
			"method": "simulated_annealing_fallback",
			"fallback_reason": "timeout",
			"cost": 15.0,
			"assignment": [Assignment(1, 10, 15.0)],
			"solve_time_sec": 0.01,
		}

	monkeypatch.setattr(zone_solver, "solve_with_fallback", fallback_stub)
	orchestrator = Orchestrator(graph, timeout_sec_per_zone=0.25)

	assignments = orchestrator.replan(state)

	assert assignments == [Assignment(1, 10, 15.0)]
	assert captured["timeout_sec"] == 0.25
	assert orchestrator.last_solver_methods == {
		1: "simulated_annealing_fallback",
	}
	assert orchestrator.last_fallback_reasons == {1: "timeout"}


def test_hospital_pre_alert_returns_dashboard_payload(client_and_state):
	client, _ = client_and_state

	response = client.post(
		"/hospitals/7/pre-alert",
		params={"incident_id": 100, "eta_sec": 45.5, "severity": 5},
	)

	assert response.status_code == 200
	assert response.json() == {
		"hospital_id": 7,
		"incident_id": 100,
		"eta_sec": 45.5,
		"severity": 5,
		"status": "notified",
	}


def test_map_state_returns_osm_positions_and_shortest_path(client_and_state):
	client, state = client_and_state
	graph = app_state.get_graph()
	graph.nodes[1].update(x=72.8, y=19.1)
	graph.nodes[2].update(x=72.9, y=19.2)
	state.active_incidents.append(Incident(102, 2, 5, 0.0))
	state.assignments[102] = Assignment(102, 10, 15.0)
	state.ambulances[0].available = False

	response = client.get("/map/state")

	assert response.status_code == 200
	map_state = response.json()
	assert map_state["incidents"][0]["position"] == {"lat": 19.2, "lon": 72.9}
	assert map_state["ambulances"][0]["position"] == {"lat": 19.1, "lon": 72.8}
	assert map_state["routes"][0]["path"] == [
		{"lat": 19.1, "lon": 72.8},
		{"lat": 19.2, "lon": 72.9},
	]


def test_map_state_reports_network_dependency_failure(client_and_state, monkeypatch):
	client, _ = client_and_state
	monkeypatch.setattr(
		map_data_routes,
		"get_graph",
		lambda: (_ for _ in ()).throw(ImportError("blocked native extension")),
	)

	response = client.get("/map/state")

	assert response.status_code == 503
	assert response.json() == {
		"detail": "Road network unavailable; check OSMnx/pyproj or OpenStreetMap connectivity."
	}


def test_dispatch_comparison_uses_same_incident_and_fleet_snapshot(client_and_state):
	client, state = client_and_state
	state.active_incidents.append(Incident(102, 2, 4, 0.0))
	state.assignments[102] = Assignment(102, 10, 15.0)
	state.ambulances[0].available = False

	response = client.get("/assignments/comparison")

	assert response.status_code == 200
	assert response.json()["optimized"]["assigned"] == 1
	assert response.json()["baseline_result"]["assigned"] == 1
	assert response.json()["same_coverage"] is True


def test_road_closure_control_closes_and_reopens_segment(client_and_state):
	client, _ = client_and_state
	graph = app_state.get_graph()
	graph.add_edge(1, 3, travel_time=22.0)
	graph.add_edge(3, 2, travel_time=22.0)
	graph.add_edge(2, 3, travel_time=22.0)
	graph.add_edge(3, 1, travel_time=22.0)
	assert nx.shortest_path_length(graph, 1, 2, weight=open_road_travel_time) == 15.0

	closed = client.put("/operations/closures", json={"source": 1, "target": 2, "closed": True})
	assert closed.status_code == 200
	assert closed.json()["closed"] is True
	assert client.get("/operations/closures").json()["closed_count"] == 1
	assert app_state.get_graph()[1][2][0]["closed"] is True
	assert nx.shortest_path_length(graph, 1, 2, weight=open_road_travel_time) == 44.0

	reopened = client.put("/operations/closures", json={"source": 1, "target": 2, "closed": False})
	assert reopened.status_code == 200
	assert reopened.json()["closed"] is False
	assert app_state.get_graph()[1][2][0]["closed"] is False
	assert nx.shortest_path_length(graph, 1, 2, weight=open_road_travel_time) == 15.0


def test_fhir_bundle_import_updates_hospital_directory(client_and_state):
	client, _ = client_and_state
	bundle = {
		"resourceType": "Bundle",
		"type": "collection",
		"entry": [
			{
				"resource": {
					"resourceType": "Location",
					"id": "unit-test",
					"status": "active",
					"position": {"latitude": 19.2, "longitude": 72.9},
					"extension": [
						{"url": "https://adas.example/fhir/StructureDefinition/available-beds", "valueInteger": 4}
					],
				},
			},
			{
				"resource": {
					"resourceType": "HealthcareService",
					"id": "trauma-unit",
					"location": [{"reference": "Location/unit-test"}],
					"specialty": [{"coding": [{"code": "trauma", "display": "Trauma care"}]}],
				},
			},
		],
	}

	response = client.post("/operations/hospitals/fhir-bundle", json=bundle)

	assert response.status_code == 200
	assert response.json()["updated"] == 1
	assert response.json()["services"] == 1
	assert app_state.get_hospitals()[0].id == "FHIR-unit-test"
	assert app_state.get_hospitals()[0].available_beds == 4


def test_ambulance_webhook_requires_secret_and_accepts_valid_positions(client_and_state, monkeypatch):
	client, state = client_and_state
	payload = {"ambulances": [{"id": "vehicle-a", "latitude": 19.1, "longitude": 72.8, "status": "available"}]}
	monkeypatch.delenv("AMBULANCE_WEBHOOK_BEARER_TOKEN", raising=False)

	disabled = client.post("/operations/ambulances/positions", json=payload)
	assert disabled.status_code == 503
	assert state.ambulances[0].id == 10

	monkeypatch.setenv("AMBULANCE_WEBHOOK_BEARER_TOKEN", "integration-test-secret")
	unauthorized = client.post("/operations/ambulances/positions", json=payload)
	assert unauthorized.status_code == 401

	accepted = client.post(
		"/operations/ambulances/positions",
		json=payload,
		headers={"Authorization": "Bearer integration-test-secret"},
	)
	assert accepted.status_code == 200
	assert accepted.json()["updated"] == 1
	assert len(state.ambulances) == 1


def test_demo_reset_reinitializes_simulation_and_clears_benchmark_cache(
	monkeypatch: pytest.MonkeyPatch,
):
	reset_calls = []
	monkeypatch.setattr(main_module, "init_simulation", lambda: reset_calls.append(True))
	benchmark_routes._cached_results["scaling"] = [{"n": 2}]

	with TestClient(app) as client:
		response = client.post("/demo/reset")

	assert response.status_code == 200
	assert response.json() == {"status": "reset"}
	assert reset_calls == [True]
	assert benchmark_routes._cached_results == {}
