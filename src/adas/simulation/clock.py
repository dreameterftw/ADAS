"""Discrete simulation clock and live dispatch state."""

from dataclasses import dataclass, field
import math

from adas.baselines.base import Assignment
from adas.simulation.incidents import Ambulance, Incident


@dataclass
class SimulationState:
	current_time: float = 0.0
	pending_incidents: list[Incident] = field(default_factory=list)
	active_incidents: list[Incident] = field(default_factory=list)
	resolved_incident_ids: set[int] = field(default_factory=set)
	ambulances: list[Ambulance] = field(default_factory=list)
	assignments: dict[int, Assignment] = field(default_factory=dict)

	def tick(self, dt_seconds: float) -> list[Incident]:
		"""Advance time and activate incidents whose timestamps have arrived."""
		if not math.isfinite(dt_seconds) or dt_seconds < 0:
			raise ValueError("dt_seconds must be finite and non-negative")
		self.current_time += dt_seconds
		newly_active = sorted(
			(
				incident
				for incident in self.pending_incidents
				if incident.timestamp <= self.current_time
			),
			key=lambda incident: incident.timestamp,
		)
		self.pending_incidents = [
			incident
			for incident in self.pending_incidents
			if incident.timestamp > self.current_time
		]
		self.active_incidents.extend(newly_active)
		return newly_active

	def resolve_incident(self, incident_id: int, ambulance_id: int) -> None:
		"""Resolve an active incident and release its ambulance."""
		if not any(incident.id == incident_id for incident in self.active_incidents):
			raise ValueError(f"incident {incident_id} is not active")
		ambulance = next(
			(ambulance for ambulance in self.ambulances if ambulance.id == ambulance_id),
			None,
		)
		if ambulance is None:
			raise ValueError(f"ambulance {ambulance_id} does not exist")
		assignment = self.assignments.get(incident_id)
		if assignment is not None and assignment.ambulance_id != ambulance_id:
			raise ValueError(f"incident {incident_id} is assigned to another ambulance")
		if any(
			other_incident_id != incident_id
			and other_assignment.ambulance_id == ambulance_id
			for other_incident_id, other_assignment in self.assignments.items()
		):
			raise ValueError(f"ambulance {ambulance_id} is assigned to another incident")

		self.active_incidents = [
			incident
			for incident in self.active_incidents
			if incident.id != incident_id
		]
		self.resolved_incident_ids.add(incident_id)
		self.assignments.pop(incident_id, None)
		ambulance.available = True