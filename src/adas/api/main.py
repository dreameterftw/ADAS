"""FastAPI application exposing live simulation state."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adas.api.routes import assignments, benchmarks, hospitals, incidents
from adas.app_state import init_simulation


app = FastAPI(title="ADAS API")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(benchmarks.router, prefix="/benchmarks", tags=["benchmarks"])
app.include_router(hospitals.router, prefix="/hospitals", tags=["hospitals"])


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/demo/reset")
def reset_demo() -> dict[str, str]:
	init_simulation()
	benchmarks.clear_benchmark_cache()
	return {"status": "reset"}
