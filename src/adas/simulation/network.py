"""Load road networks and expose travel-time graph helpers."""

import gzip
import json
import logging
import math
import re
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import networkx as nx


logger = logging.getLogger(__name__)

DRIVE_HIGHWAYS = {
	"motorway",
	"trunk",
	"primary",
	"secondary",
	"tertiary",
	"unclassified",
	"residential",
	"living_street",
	"service",
	"road",
	"motorway_link",
	"trunk_link",
	"primary_link",
	"secondary_link",
	"tertiary_link",
}
DEFAULT_SPEED_KPH = {
	"motorway": 80.0,
	"trunk": 70.0,
	"primary": 50.0,
	"secondary": 40.0,
	"tertiary": 35.0,
	"unclassified": 30.0,
	"residential": 25.0,
	"living_street": 10.0,
	"service": 15.0,
	"road": 25.0,
}


def open_road_travel_time(_source: int, _target: int, edge_data: dict) -> float | None:
	"""NetworkX weight callback that hides closed edges, including parallel roads."""
	attributes = (
		edge_data.values()
		if edge_data and all(isinstance(value, dict) for value in edge_data.values())
		else (edge_data,)
	)
	weights = [
		float(data.get("travel_time", 1.0))
		for data in attributes
		if not data.get("closed")
	]
	return min(weights) if weights else None
OSM_USER_AGENT = "ADAS-dispatch-demo/1.0"


def _geocode_with_nominatim(place_name: str) -> tuple[float, float]:
	query = urllib.parse.urlencode({
		"q": place_name,
		"format": "json",
		"limit": 1,
	})
	request = urllib.request.Request(
		f"https://nominatim.openstreetmap.org/search?{query}",
		headers={"User-Agent": OSM_USER_AGENT},
	)
	with urllib.request.urlopen(request, timeout=20) as response:
		places = json.load(response)
	if not places:
		raise ValueError(f"No OpenStreetMap result found for {place_name!r}")
	return float(places[0]["lat"]), float(places[0]["lon"])


def _haversine_meters(
	latitude_a: float,
	longitude_a: float,
	latitude_b: float,
	longitude_b: float,
) -> float:
	earth_radius_m = 6_371_000.0
	latitude_delta = math.radians(latitude_b - latitude_a)
	longitude_delta = math.radians(longitude_b - longitude_a)
	a = (
		math.sin(latitude_delta / 2) ** 2
		+ math.cos(math.radians(latitude_a))
		* math.cos(math.radians(latitude_b))
		* math.sin(longitude_delta / 2) ** 2
	)
	return 2 * earth_radius_m * math.asin(math.sqrt(a))


def _speed_kph(tags: dict[str, str]) -> float:
	maxspeed = tags.get("maxspeed", "")
	match = re.search(r"\d+(?:\.\d+)?", maxspeed)
	if match:
		speed = float(match.group())
		return speed * 1.609344 if "mph" in maxspeed.lower() else speed
	highway = tags.get("highway", "road").split(",", 1)[0]
	return DEFAULT_SPEED_KPH.get(highway, 25.0)


def _graph_from_osm_xml(xml_data: bytes, place_name: str) -> nx.MultiDiGraph:
	root = ET.fromstring(xml_data)
	node_positions = {
		int(node.attrib["id"]): (
			float(node.attrib["lat"]),
			float(node.attrib["lon"]),
		)
		for node in root.findall("node")
	}
	ways = []
	for way in root.findall("way"):
		tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
		highway = tags.get("highway")
		nodes = [int(node.attrib["ref"]) for node in way.findall("nd")]
		if highway in DRIVE_HIGHWAYS and len(nodes) >= 2:
			ways.append((nodes, tags))

	used_nodes = {node for nodes, _ in ways for node in nodes if node in node_positions}
	data = {"elements": [
		{
			"type": "node",
			"id": node_id,
			"lat": position[0],
			"lon": position[1],
		}
		for node_id, position in node_positions.items()
		if node_id in used_nodes
	]}
	data["elements"].extend(
		{
			"type": "way",
			"nodes": nodes,
			"tags": tags,
		}
		for nodes, tags in ways
	)
	return _graph_from_osm_elements(data, place_name)


def _graph_from_osm_elements(data: dict[str, object], place_name: str) -> nx.MultiDiGraph:
	graph = nx.MultiDiGraph(crs="EPSG:4326", name=place_name)
	elements = data.get("elements", [])
	if not isinstance(elements, list):
		raise ValueError("OpenStreetMap returned an invalid road-network response")

	for element in elements:
		if not isinstance(element, dict) or element.get("type") != "node":
			continue
		graph.add_node(
			element["id"],
			y=float(element["lat"]),
			x=float(element["lon"]),
		)

	for element in elements:
		if not isinstance(element, dict) or element.get("type") != "way":
			continue
		tags = element.get("tags", {})
		nodes = element.get("nodes", [])
		if not isinstance(tags, dict) or not isinstance(nodes, list):
			continue
		if len(nodes) < 2 or any(node not in graph for node in nodes):
			continue

		max_speed = _speed_kph(tags)
		oneway_value = str(tags.get("oneway", "")).lower()
		is_oneway = oneway_value in {"yes", "true", "1"} or (
			tags.get("junction") == "roundabout" and oneway_value != "no"
		)
		reverse_only = oneway_value == "-1"
		for node_a, node_b in zip(nodes, nodes[1:]):
			attributes_a = graph.nodes[node_a]
			attributes_b = graph.nodes[node_b]
			length = _haversine_meters(
				attributes_a["y"],
				attributes_a["x"],
				attributes_b["y"],
				attributes_b["x"],
			)
			edge_attributes = {
				"length": length,
				"speed_kph": max_speed,
				"travel_time": length / (max_speed / 3.6),
				"highway": tags.get("highway", "road"),
			}
			if "name" in tags:
				edge_attributes["name"] = tags["name"]
			if "maxspeed" in tags:
				edge_attributes["maxspeed"] = tags["maxspeed"]
			if reverse_only:
				graph.add_edge(node_b, node_a, **edge_attributes)
			else:
				graph.add_edge(node_a, node_b, **edge_attributes)
			if not is_oneway and not reverse_only:
				graph.add_edge(node_b, node_a, **edge_attributes)

	if not graph:
		raise ValueError(f"No drivable OpenStreetMap roads found near {place_name!r}")
	return graph


def _load_city_network_from_osm_api(place_name: str) -> nx.MultiDiGraph:
	latitude, longitude = _geocode_with_nominatim(place_name)
	latitude_radius = 1000 / 111_320
	longitude_radius = latitude_radius / math.cos(math.radians(latitude))
	bounds = (
		longitude - longitude_radius,
		latitude - latitude_radius,
		longitude + longitude_radius,
		latitude + latitude_radius,
	)
	query = urllib.parse.urlencode({"bbox": ",".join(map(str, bounds))})
	request = urllib.request.Request(
		f"https://api.openstreetmap.org/api/0.6/map?{query}",
		headers={"User-Agent": OSM_USER_AGENT},
	)
	with urllib.request.urlopen(request, timeout=60) as response:
		return _graph_from_osm_xml(response.read(), place_name)


def load_city_network(
	place_name: str,
	network_type: str = "drive",
) -> nx.MultiDiGraph:
	"""Download and prepare a drivable OpenStreetMap network for a place."""
	try:
		import osmnx as ox
	except ImportError:
		if network_type != "drive":
			raise
		logger.warning("OSMnx unavailable; loading a bounded extract from the OSM API")
		return _load_city_network_from_osm_api(place_name)

	try:
		graph = ox.graph_from_place(place_name, network_type=network_type)
	except ValueError as error:
		if "no graph nodes within the requested polygon" not in str(error):
			raise
		center = ox.geocode(place_name)
		graph = ox.graph_from_point(center, dist=3000, network_type=network_type)
	graph = ox.add_edge_speeds(graph)
	return ox.add_edge_travel_times(graph)


def load_bundled_road_network() -> nx.MultiDiGraph:
	"""Load the small, attributed Andheri OpenStreetMap network used by the showcase."""
	data_path = Path(__file__).parent.parent / "data" / "andheri_osm_roads.json.gz"
	with gzip.open(data_path, "rt", encoding="utf-8") as source:
		payload = json.load(source)
	if payload.get("source") != "OpenStreetMap" or not payload.get("nodes") or not payload.get("edges"):
		raise ValueError("Bundled road network is missing its OpenStreetMap data")

	graph = nx.MultiDiGraph(crs="EPSG:4326", name=str(payload.get("place", "Andheri, Mumbai, India")))
	graph.graph["network_source"] = "OpenStreetMap"
	graph.graph["extract_date"] = str(payload.get("extract_date", ""))
	graph.graph["route_geometry"] = "road_network"
	for node in payload["nodes"]:
		graph.add_node(int(node["id"]), y=float(node["lat"]), x=float(node["lon"]))
	major_highways = {"motorway", "trunk", "primary", "secondary", "tertiary"}
	for edge in payload["edges"]:
		highway = str(edge.get("highway", "road"))
		travel_time = max(1.0, float(edge.get("travel_time", 60.0)))
		attributes = {
			"length": float(edge.get("length", 0.0)),
			"travel_time": travel_time,
			"base_travel_time": travel_time,
			"highway": highway,
			"major_corridor": highway in major_highways,
			"traffic_level": "normal",
		}
		for optional in ("name", "maxspeed"):
			if edge.get(optional):
				attributes[optional] = str(edge[optional])
		graph.add_edge(int(edge["source"]), int(edge["target"]), **attributes)
	return graph


def get_intersections(
	graph: nx.MultiDiGraph,
	limit: int | None = None,
) -> list[int]:
	"""Return graph nodes with at least three incident edges."""
	intersections = [node for node, degree in graph.degree() if degree >= 3]
	return intersections[:limit] if limit is not None else intersections


def shortest_travel_time(
	graph: nx.MultiDiGraph,
	origin: int,
	destination: int,
) -> float:
	"""Return the shortest travel time between two graph nodes in seconds."""
	return float(
		nx.shortest_path_length(
			graph,
			origin,
			destination,
			weight=open_road_travel_time,
		)
	)


def get_node_latlon(graph: nx.MultiDiGraph, node_id: int) -> tuple[float, float]:
	"""Return a graph node's (latitude, longitude) coordinates."""
	data = graph.nodes[node_id]
	return float(data["y"]), float(data["x"])


def get_route_latlon(graph: nx.MultiDiGraph, path: list[int]) -> list[list[float]]:
	"""Convert route node IDs into [latitude, longitude] pairs for a map."""
	return [list(get_node_latlon(graph, node_id)) for node_id in path]


if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)
	city_graph = load_city_network("Andheri, Mumbai, India")
	logger.info("Nodes: %d, edges: %d", len(city_graph.nodes), len(city_graph.edges))
	logger.info("Sample intersections: %s", get_intersections(city_graph, limit=20))
