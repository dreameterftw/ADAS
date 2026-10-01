# ADAS
Quantum-assisted decision layer for city-wide emergency response.

## Structure
- `src/adas/simulation/` - road network and synthetic incidents
- `src/adas/baselines/` - classical dispatch and routing methods
- `src/adas/quantum/` - QUBO, QAOA, QAE confidence, and classical fallback
- `src/adas/zones/` - city partitioning and multi-zone coordination
- `src/adas/hospitals/` - capacity- and specialty-aware hospital matching
- `src/adas/benchmarks/` - scaling, QAE efficiency, and noise studies
- `src/adas/api/` - FastAPI backend serving the dashboard
- `tests/` - correctness checks, especially QUBO versus brute force

## Setup
PowerShell:

```powershell
python -m venv venv
\.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the API
From the repository root, expose `src` on `PYTHONPATH` before starting Uvicorn:

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn adas.api.main:app --reload --port 8000
```

The first route that needs simulation state downloads the configured road network
through OSMnx. `/health` does not initialize or download it. See [docs/api.md](docs/api.md)
for endpoint methods, query parameters, and response shapes.

## Safety and benchmark notes
- Zone solving uses a 10-second QAOA wait budget by default, then falls back to simulated annealing. Python cannot forcibly stop a QAOA call already running in its worker thread; fallback bounds the request wait, but that computation may finish in the background.
- Hospital matching uses synthetic bed/specialty data, and pre-alerts are demo responses rather than real hospital notifications.
- Benchmark results are illustrative local measurements. In the current small simulator study, classical simulated annealing was substantially faster and QAE did not show a consistent sample-efficiency advantage.

## Status
Phases 1-10: backend implementation complete; see the benchmark caveats above before making scaling or quantum-advantage claims. Fallback and hospital behavior are demo safeguards, not a certified emergency-response system.
