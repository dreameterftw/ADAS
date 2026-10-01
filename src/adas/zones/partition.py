"""Community-detection partitioning of the road network into bounded zones."""

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities


def partition_into_zones(
	graph: nx.MultiDiGraph,
	max_nodes_per_zone: int = 20,
) -> dict[int, int]:
	"""Map every graph node to a zone, splitting oversized communities."""
	if (
		isinstance(max_nodes_per_zone, bool)
		or not isinstance(max_nodes_per_zone, int)
		or max_nodes_per_zone < 1
	):
		raise ValueError("max_nodes_per_zone must be a positive integer")
	if graph.number_of_nodes() == 0:
		return {}

	communities = greedy_modularity_communities(graph.to_undirected())
	communities = sorted(communities, key=lambda community: min(community))
	zone_map: dict[int, int] = {}
	zone_id = 0
	for community in communities:
		nodes = sorted(community)
		for offset in range(0, len(nodes), max_nodes_per_zone):
			for node in nodes[offset : offset + max_nodes_per_zone]:
				zone_map[node] = zone_id
			zone_id += 1
	return zone_map


def get_boundary_nodes(
	graph: nx.MultiDiGraph,
	zone_map: dict[int, int],
) -> set[int]:
	"""Return endpoints of edges whose endpoints are assigned to different zones."""
	boundary: set[int] = set()
	for source, target in graph.edges():
		if (
			source in zone_map
			and target in zone_map
			and zone_map[source] != zone_map[target]
		):
			boundary.update((source, target))
	return boundary


def zone_members(zone_map: dict[int, int], zone_id: int) -> list[int]:
	"""Return the nodes assigned to a zone in stable order."""
	return sorted(node for node, assigned_zone in zone_map.items() if assigned_zone == zone_id)
