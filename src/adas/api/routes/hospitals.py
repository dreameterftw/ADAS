"""Simulated hospital pre-alert API routes."""

import math

from fastapi import APIRouter, HTTPException, Query


router = APIRouter()


@router.post("/{hospital_id}/pre-alert")
def send_pre_alert(
	hospital_id: int,
	incident_id: int = Query(),
	eta_sec: float = Query(ge=0),
	severity: int = Query(ge=1, le=5),
) -> dict[str, int | float | str]:
	"""Return a simulated ER pre-alert payload for dashboard display."""
	if not math.isfinite(eta_sec):
		raise HTTPException(status_code=422, detail="eta_sec must be finite")
	return {
		"hospital_id": hospital_id,
		"incident_id": incident_id,
		"eta_sec": eta_sec,
		"severity": severity,
		"status": "notified",
	}