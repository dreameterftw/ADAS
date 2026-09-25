# ADAS
Quantum-assisted decision layer for city-wide emergency response.

## Structure
- `src/adas/simulation/` - road network and synthetic incidents
- `src/adas/baselines/` - classical dispatch and routing methods
- `src/adas/quantum/` - QUBO, QAOA solver, and QAE confidence engine
- `src/adas/zones/` - city partitioning and multi-zone coordination
- `src/adas/api/` - FastAPI backend serving the dashboard
- `tests/` - correctness checks, especially QUBO versus brute force

## Setup
```text
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Status
Phase 1: scaffolding - done
Phase 2: toolchain verification - in progress
