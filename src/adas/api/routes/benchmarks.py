"""Placeholder benchmark API routes."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/summary")
def benchmark_summary() -> dict[str, str]:
	return {"status": "not yet implemented; see Phase 9"}
