# ADAS API

Base URL: `http://127.0.0.1:8000`. Start locally with `PYTHONPATH=src python -m uvicorn adas.api.main:app --reload --port 8000` (PowerShell: set `$env:PYTHONPATH = "src"` first).

Dispatch state and the operator request log are held in memory and reset when the process restarts. The road graph is loaded lazily the first time a route needs simulation data; `/health` does not trigger a network download. Most operator endpoints are intended for a controlled presentation environment and do not provide user authentication. The inbound ambulance GPS webhook is disabled unless `AMBULANCE_WEBHOOK_BEARER_TOKEN` is configured and always requires that token.

The repeatable Andheri response scenario uses a bundled OpenStreetMap road extract. Routes are calculated over directed road edges and returned as the coordinates of their road nodes, so the displayed line follows mapped streets. The extract is static; scenario traffic controls do not represent live traffic. `GET /map/state` includes a `network` object identifying the map-data source and extract date.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Process health; does not initialize the simulation. |
| `POST` | `/demo/reset` | Reinitialize the default simulation and clear cached benchmark results. |
| `GET` | `/incidents/active` | Return currently active incidents. |
| `GET` | `/incidents/requests` | Return operator-entered request records for this process. |
| `POST` | `/incidents/requests` | Add an intake request and create its map-visible incident. |
| `POST` | `/incidents/tick?dt_seconds=30` | Advance the clock; `dt_seconds` is optional, finite, and non-negative. |
| `POST` | `/incidents/demo/scenario` | Load a deterministic scenario that exercises boundary reassignment and both fallback paths. |
| `POST` | `/incidents/{incident_id}/resolve?ambulance_id=10` | Resolve an active incident and release its assigned ambulance. Returns `409` if the incident or ambulance assignment is invalid. |
| `POST` | `/assignments/replan` | Replan active incidents using per-zone QAOA with a 10-second wait budget and simulated-annealing fallback. |
| `GET` | `/assignments/comparison` | Compare the current plan with nearest-available-unit dispatch on the same incident and fleet snapshot. |
| `GET` | `/operations/closures` | List selectable road segments and active closures. |
| `PUT` | `/operations/closures` | Close or reopen a road segment and recalculate dispatch routes. Body: `{"source":1,"target":2,"closed":true}`. |
| `POST` | `/operations/hospitals/fhir-bundle` | Import a FHIR R4 Bundle containing hospital `Location` and optional `HealthcareService` resources. Replaces the in-memory directory. |
| `POST` | `/operations/ambulances/positions` | Receive authenticated AVL/GPS positions. Requires `Authorization: Bearer <AMBULANCE_WEBHOOK_BEARER_TOKEN>`. |
| `GET` | `/operations/integrations` | Report configured hospital and ambulance sources and whether routing is scenario-only. |
| `POST` | `/operations/sync` | Pull configured hospital and ambulance provider feeds. |
| `POST` | `/hospitals/{hospital_id}/pre-alert?incident_id=1&eta_sec=120&severity=5` | Return a simulated ER pre-alert payload. |
| `GET` | `/benchmarks/summary` | Phase 9 placeholder status. |
| `GET` | `/benchmarks/scaling` | Cached QAOA/annealing scaling measurements for sizes 2 through 5. |
| `GET` | `/benchmarks/scaling/preview` | Cached small scaling sample for the UI, sizes 2 and 3. |
| `GET` | `/benchmarks/qae-efficiency` | Cached simulator-derived QAE/Monte Carlo comparison. |
| `GET` | `/benchmarks/decisions` | In-memory counts of QAOA and classical fallback zone decisions. |

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

`POST /incidents/requests` accepts caller/source, a location label, severity from 1 to 5, latitude, longitude, and optional intake notes. The service snaps the coordinates to the nearest geocoded road node, creates an active incident, and appends an operator-entered request record. The log is in memory; durable multi-operator intake requires a persistent database and authenticated integration.

`POST /incidents/{incident_id}/resolve?ambulance_id=10` resolves an active incident and releases the ambulance assigned to it:

```json
{"incident_id":1,"ambulance_id":10,"status":"resolved"}
```

The endpoint returns `409` if the incident is not active or the ambulance is not assigned to it.

`POST /incidents/tick`:

```json
{"current_time":600.0,"newly_active_count":2}
```

`POST /assignments/replan` returns an array of assignments. Times are seconds; `fallback_reason` is `null` for QAOA results and explains why the classical fallback ran otherwise. `assignment_reason` gives the priority, solver, traffic mode, hospital specialty, and reported bed rationale. `coordination_reason` is `in_zone` or `reassigned_at_boundary`; `hospital_match_reason` reports specialty-and-capacity selection, capacity-only fallback, or no reachable capacity:

```json
[{"incident_id":1,"ambulance_id":2,"travel_time_sec":45.0,"coordination_reason":"in_zone","solver_method":"qaoa","fallback_reason":null,"assignment_reason":"Severity 5 priority was considered; qaoa selected this available unit for an estimated 1-minute response under normal traffic conditions. Hospital 7 has a preferred specialty and 3 reported available beds.","hospital_id":7,"hospital_match_reason":"specialty_and_capacity","hospital_available_beds":3,"hospital_specialties":["trauma"]}]
```

Road closures are omitted from route calculations. If a closure disconnects a call from the available fleet, that call remains unassigned rather than being routed across the closed segment. Traffic mode controls use scenario factors; no live traffic provider is connected.

Fallback is applied per zone after a 10-second timeout by default. On expiry, the QAOA worker process is forcibly terminated, rather than only bounding the caller's wait. This remains a demo-level timeout, not a hard real-time execution guarantee.

`POST /incidents/demo/scenario` loads a small deterministic in-memory graph with one active incident. Replanning it produces a boundary reassignment, a hospital match using capacity fallback, and a solver timeout fallback. It replaces the current simulation state; `/demo/reset` restores the default OSM-backed simulation.

`GET /benchmarks/decisions` returns cumulative in-memory counts, for example:

```json
{"qaoa":3,"fallback":1}
```

`POST /hospitals/{hospital_id}/pre-alert`:

```json
{"hospital_id":7,"incident_id":1,"eta_sec":45.0,"severity":5,"status":"notified"}
```

Benchmark endpoints return arrays of measurements. Scaling rows include `n`, `num_qubits`, severity-weighted QAOA and simulated-annealing costs, runtimes, QAOA feasibility metadata, and brute-force costs/times for `n <= 3`. QAE efficiency rows include target epsilon, estimate/error, Grover-oracle queries, sampler shots, and Monte Carlo sample count/estimate/error. These are local experimental measurements, not guarantees of quantum advantage.

The scaling and QAE benchmark routes can take a while on first request and initialize/download the default OSM network. Results are cached in process memory until `/demo/reset` or restart.
