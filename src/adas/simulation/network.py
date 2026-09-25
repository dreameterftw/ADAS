"""Load road networks and expose travel-time graph helpers."""

import networkx as nx


def load_city_network(
	place_name: str,
	network_type: str = "drive",
) -> nx.MultiDiGraph:
	"""Download and prepare a drivable OpenStreetMap network for a place."""
	import osmnx as ox

	try:
		graph = ox.graph_from_place(place_name, network_type=network_type)
	except ValueError as error:
		if "no graph nodes within the requested polygon" not in str(error):
			raise
		center = ox.geocode(place_name)
		graph = ox.graph_from_point(center, dist=3000, network_type=network_type)
	graph = ox.add_edge_speeds(graph)
	return ox.add_edge_travel_times(graph)


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
			weight="travel_time",
		)
	)


if __name__ == "__main__":
	city_graph = load_city_network("Andheri, Mumbai, India")
	print(f"Nodes: {len(city_graph.nodes)}, Edges: {len(city_graph.edges)}")
	print(f"Sample intersections: {get_intersections(city_graph, limit=20)}")
