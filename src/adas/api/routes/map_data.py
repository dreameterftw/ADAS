"""Map-ready simulation state for the dashboard."""

from typing import Any

import networkx as nx
from fastapi import APIRouter, HTTPException

from adas.app_state import (
	get_graph,
	get_hospitals,
	get_simulation_state,
	get_traffic_mode,
)
from adas.hospitals.matching import best_hospital_for_incident


router = APIRouter()


def _position(graph: nx.MultiDiGraph, node: int) -> dict[str, float] | None:
	attributes = graph.nodes[node]
	if "x" not in attributes or "y" not in attributes:
		return None
	return {"lat": float(attributes["y"]), "lon": float(attributes["x"])}


@router.get("/state")
def get_map_state() -> dict[str, Any]:
	try:
		graph = get_graph()
		state = get_simulation_state()
		hospitals = get_hospitals()
	except (ImportError, OSError, RuntimeError, ValueError) as error:
		raise HTTPException(
			status_code=503,
			detail="Road network unavailable; check OSMnx/pyproj or OpenStreetMap connectivity.",
		) from error
	ambulances_by_id = {ambulance.id: ambulance for ambulance in state.ambulances}
	incidents_by_id = {incident.id: incident for incident in state.active_incidents}
	incident_items = []
	route_items = []

	for incident in state.active_incidents:
		incident_items.append({
			"id": incident.id,
			"severity": incident.severity,
			"location_node": incident.location_node,
			"position": _position(graph, incident.location_node),
		})

	for incident_id, assignment in state.assignments.items():
		incident = incidents_by_id.get(incident_id)
		ambulance = ambulances_by_id.get(assignment.ambulance_id)
		if incident is None or ambulance is None:
			continue

		hospital, match_reason = best_hospital_for_incident(
			graph,
			incident.location_node,
			incident.severity,
			hospitals,
		)
		try:
			path_nodes = nx.shortest_path(
				graph,
				ambulance.current_node,
				incident.location_node,
				weight="travel_time",
			)
			if hospital is not None:
				hospital_path = nx.shortest_path(
					graph,
					incident.location_node,
					hospital.node,
					weight="travel_time",
				)
				path_nodes.extend(hospital_path[1:])
		except (nx.NetworkXNoPath, nx.NodeNotFound):
			path_nodes = []

		route_items.append({
			"incident_id": incident.id,
			"ambulance_id": ambulance.id,
			"hospital_id": hospital.id if hospital is not None else None,
			"hospital_match_reason": match_reason,
			"travel_time_sec": assignment.travel_time_sec,
			"path": [
				position
				for node in path_nodes
				if (position := _position(graph, node)) is not None
			],
		})

	return {
		"current_time": state.current_time,
		"traffic_mode": get_traffic_mode(),
		"incidents": incident_items,
		"ambulances": [
			{
				"id": ambulance.id,
				"current_node": ambulance.current_node,
				"available": ambulance.available,
				"position": _position(graph, ambulance.current_node),
			}
			for ambulance in state.ambulances
		],
		"hospitals": [
			{
				"id": hospital.id,
				"node": hospital.node,
				"available_beds": hospital.available_beds,
				"position": _position(graph, hospital.node),
			}
			for hospital in hospitals
		],
		"routes": route_items,
	}
