# ADAS API

Base URL: `http://127.0.0.1:8000`. Start locally with `PYTHONPATH=src python -m uvicorn adas.api.main:app --reload --port 8000` (PowerShell: set `$env:PYTHONPATH = "src"` first).

Simulation state is held in memory and resets when the process restarts. The road graph is loaded lazily the first time a route needs simulation data; `/health` does not trigger a network download. Routes currently have no authentication and CORS allows all origins, so keep the demo server on a trusted network.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Process health; does not initialize the simulation. |
| `POST` | `/demo/reset` | Reinitialize the default simulation and clear cached benchmark results. |
| `GET` | `/incidents/active` | Return currently active incidents. |
| `POST` | `/incidents/tick?dt_seconds=30` | Advance the clock; `dt_seconds` is optional, finite, and non-negative. |
| `POST` | `/assignments/replan` | Replan active incidents using per-zone QAOA with a 10-second wait budget and simulated-annealing fallback. |
| `POST` | `/hospitals/{hospital_id}/pre-alert?incident_id=1&eta_sec=120&severity=5` | Return a simulated ER pre-alert payload. |
| `GET` | `/benchmarks/summary` | Phase 9 placeholder status. |
| `GET` | `/benchmarks/scaling` | Cached QAOA/annealing scaling measurements for sizes 2 through 5. |
| `GET` | `/benchmarks/qae-efficiency` | Cached simulator-derived QAE/Monte Carlo comparison. |

## Response shapes

`GET /health`:

```json
{"status":"ok"}
```

`POST /demo/reset`:

```json
{"status":"reset"}
```

Reset reloads the default OSM network and resets pending/active incidents, ambulance state, and cached benchmark results. The request may take time and requires the network loader to succeed.

`GET /incidents/active` returns an array of objects with integer `id`, `location_node`, `severity`, and numeric `timestamp` (simulation seconds).

`POST /incidents/tick`:

```json
{"current_time":600.0,"newly_active_count":2}
```

`POST /assignments/replan` returns an array of assignments. Times are seconds; `fallback_reason` is `null` for QAOA results and explains why the classical fallback ran otherwise:

```json
[{"incident_id":1,"ambulance_id":2,"travel_time_sec":45.0,"solver_method":"qaoa","fallback_reason":null}]
```

Fallback is applied per zone after a 10-second wait budget by default. On timeout, Python cannot stop an already-running QAOA thread; the API returns the simulated-annealing result while that worker may finish in the background. This is a demo-level wait bound, not a hard real-time execution guarantee.

`POST /hospitals/{hospital_id}/pre-alert`:

```json
{"hospital_id":7,"incident_id":1,"eta_sec":45.0,"severity":5,"status":"notified"}
```

Benchmark endpoints return arrays of measurements. Scaling rows include `n`, `num_qubits`, severity-weighted QAOA and simulated-annealing costs, runtimes, QAOA feasibility metadata, and brute-force costs/times for `n <= 3`. QAE efficiency rows include target epsilon, estimate/error, Grover-oracle queries, sampler shots, and Monte Carlo sample count/estimate/error. These are local experimental measurements, not guarantees of quantum advantage.

The scaling and QAE benchmark routes can take a while on first request and initialize/download the default OSM network. Results are cached in process memory until `/demo/reset` or restart.
