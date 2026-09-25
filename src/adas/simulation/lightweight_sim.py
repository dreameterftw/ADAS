"""Lightweight travel-time simulation fallback when SUMO is unavailable."""

import math

import networkx as nx


def congestion_factor(t_seconds: float, sim_duration_sec: float) -> float:
    """Return a smooth peak-hour multiplier for a simulation time."""
    if sim_duration_sec <= 0:
        raise ValueError("sim_duration_sec must be positive")

    peak = sim_duration_sec / 2
    spread = sim_duration_sec / 4
    return 1.0 + 1.5 * math.exp(
        -((t_seconds - peak) ** 2) / (2 * spread**2)
    )


def travel_time_at(
    graph: nx.MultiDiGraph,
    origin: int,
    destination: int,
    t_seconds: float,
    sim_duration_sec: float,
) -> float:
    """Estimate travel time by scaling the shortest base travel time."""
    base_time = nx.shortest_path_length(
        graph,
        origin,
        destination,
        weight="travel_time",
    )
    return float(base_time) * congestion_factor(t_seconds, sim_duration_sec)