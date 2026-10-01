"""FastAPI application exposing live simulation state."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adas.api.routes import assignments, benchmarks, incidents


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


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}
