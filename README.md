# ADAS — Ambulance Dispatch and Assistance System

ADAS is a web application for coordinating ambulance responses across multiple incidents. It combines a road-network map, incident intake, ambulance availability, hospital capacity and specialty matching, and a quantum-inspired optimization experiment to produce and explain dispatch assignments.

## Open the live application

- **Web app:** https://adas-nav.web.app
- **Backend health:** https://adas-backend-3mz9.onrender.com/health

The public app is useful for exploring the workflow. Its hospital, vehicle, incident, traffic, and closure data are currently a controlled in-memory presentation scenario; the external provider connections described below need authorized endpoints and credentials before they represent live operational feeds.

## What it can do

- Record an incident with location and severity, then show it on the operations map.
- Assign available ambulances across multiple incidents while considering severity and estimated road travel time.
- Compare the current assignments with a nearest-available-unit baseline using the same fleet and incident snapshot.
- Explain why each ambulance was assigned, including solver method, priority, traffic scenario, and hospital matching rationale.
- Match incidents to reachable hospitals using reported capacity and specialty preferences.
- Close or reopen a road segment and recalculate routes; unreachable incidents remain unassigned.
- Import hospital locations and services from a FHIR R4 bundle, or receive ambulance GPS positions through an authenticated AVL webhook.
- Explore solver scaling, QAOA/fallback decision counts, and a separate QAE versus Monte Carlo experiment.
- View the live assignment in the driver page and confirm arrival.

## Map and routing

The repeatable Andheri response scenario uses a compact road extract from OpenStreetMap. Routes are calculated along directed road-network edges, so the displayed route follows mapped roads instead of drawing a straight line across buildings or open land. The extract is a static snapshot, not a live map or traffic feed. See [map-data attribution and notes](src/adas/data/README.md).

Traffic modes and road closures are application scenarios. A live traffic provider is not configured. For operational use, the road graph, closures, traffic conditions, and location accuracy would need current, authorized data sources.

## How the quantum component works

The dispatch planner builds a QUBO (a binary optimization model). A binary variable represents whether a particular ambulance is assigned to a particular incident. The model rewards covering incidents, gives severe incidents more priority, and accounts for estimated travel time. Constraints prevent an ambulance from taking multiple incidents or an incident from receiving multiple ambulances; unavailable and unreachable pairs are excluded.

The app runs QAOA using Qiskit and the Aer **quantum circuit simulator**. A warm start and a classical optimizer help search for a good assignment. The assignment is checked, and simulated annealing can provide a classical fallback if QAOA errors, times out, or returns an unusable result. The zone solver splits larger maps into smaller regions and reconciles assignments at region boundaries.

This is an experiment on simulated quantum circuits, **not quantum hardware**. The project does not claim quantum advantage: current small benchmark results show classical simulated annealing is substantially faster, and the separate QAE experiment has not shown consistent sample-efficiency gains. QAE is a benchmark feature; it does not drive live dispatch assignments.

## Hospital and ambulance connections

The app currently supports integration workflows, but no external hospital, ambulance, or live traffic provider is configured in the public deployment.

- **Hospitals:** Import an authorized FHIR R4 Bundle containing active `Location` resources and optional `HealthcareService` resources. Live available-bed counts are provider-specific and require the configured extension URL. Imported coordinates are snapped to the road graph. An import replaces the in-memory hospital directory.
- **Ambulances:** Poll an authorized JSON AVL endpoint or send GPS positions to `POST /operations/ambulances/positions` with a backend-configured bearer token. Valid coordinates are snapped to the road graph, replace the in-memory fleet, and trigger replanning.
- **Hospital request logs:** The current intake form creates operator-entered requests in process memory. Connecting real logs requires an authorized provider feed, field mapping, authentication, durable storage, and an agreed privacy/security process. This repository does not currently include an HL7 ADT connector.
- **Traffic:** Only built-in traffic scenarios and operator-controlled road closures are connected. There is no real-time traffic provider adapter configured in the deployment.

Integration setup, accepted fields, and backend environment variables are in [docs/integrations.md](docs/integrations.md). API endpoints and request/response details are in [docs/api.md](docs/api.md).

## Run locally

Requires Python 3.11 or later. From the repository root in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:PYTHONPATH = "src"
python -m uvicorn adas.api.main:app --reload --port 8000
```

Open the API documentation at http://127.0.0.1:8000/docs. The map network is initialized lazily; the bundled Andheri scenario is reproducible without downloading the default road graph. For benchmark behavior, see the notes in [docs/api.md](docs/api.md).

## Repository guide

| Path | Contents |
| --- | --- |
| `src/adas/api/` | FastAPI endpoints and application state |
| `src/adas/quantum/` | QUBO, QAOA solver, confidence/QAE experiment |
| `src/adas/zones/` | Road-network partitioning and boundary coordination |
| `src/adas/data/` | Bundled road extract and attribution |
| `dashboard/` | React web application used by the Firebase deployment |
| `docs/api.md` | API reference and behavior notes |
| `docs/integrations.md` | FHIR, ambulance AVL, traffic and closure integration details |
| `docs/presentation-guide.md` | Simple team briefing and judge presentation outline |

## Important operational limits

Dispatch state and operator request logs are in memory and reset when the backend restarts. Most operator endpoints are intended for a controlled presentation environment and do not provide user authentication. The ambulance webhook requires a bearer token when enabled. The application is a project prototype, not a certified medical dispatch service; do not use it to make real emergency-care decisions.
