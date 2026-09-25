"""Common dispatch strategy interface and assignment result type."""

from dataclasses import dataclass

import networkx as nx

from adas.simulation.incidents import Ambulance, Incident


@dataclass(frozen=True)
class Assignment:
    """One ambulance assignment produced by a dispatch strategy."""

    incident_id: int
    ambulance_id: int
    travel_time_sec: float


class DispatchStrategy:
    """Interface shared by classical and future quantum dispatch solvers."""

    name = "base"

    def solve(
        self,
        graph: nx.MultiDiGraph,
        incidents: list[Incident],
        ambulances: list[Ambulance],
    ) -> list[Assignment]:
        raise NotImplementedError