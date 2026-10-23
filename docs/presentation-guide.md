# ADAS team and presentation guide

This guide gives the team a shared, accurate explanation of ADAS and a short route through the web app. Use “scenario” for the repeatable prepared data. Be clear that provider feeds are supported as integration paths but are not connected in the current deployment.

## The project in one sentence

ADAS helps coordinate ambulance assignments across simultaneous incidents by considering urgency, road travel time, vehicle availability, and hospital capacity, then showing the operator why it made each choice.

## Suggested 5-minute presentation

### 1. Introduce the problem (30 seconds)

“When several emergencies happen at once, dispatchers need to decide which available ambulance should respond to each incident and which reachable hospital can receive the patient. Picking only the nearest vehicle can miss severity, road conditions, hospital capacity, and the impact of other incidents.”

### 2. Explain the system (45 seconds)

“ADAS puts incidents, ambulances, hospitals, and routes on one operations map. It plans assignments for multiple incidents together, compares the result with a nearest-available baseline, and shows the reason for each assignment. Operators can also change traffic scenarios or close a road segment to see the plan update.”

### 3. Walk through the application (about 2 minutes)

1. Open the [ADAS web app](https://adas-nav.web.app) and go to the operations dashboard.
2. Load the prepared response scenario if the map does not already show incidents and ambulances. This gives a repeatable starting point.
3. Point out the incident severity, available vehicles, hospitals, and route lines. Explain that the showcase route follows mapped OpenStreetMap road edges in the Andheri extract; it is not a straight-line route.
4. Show the assignment explanation and open the comparison with the nearest-available baseline. Explain that both plans use the same current incident and fleet snapshot.
5. Close a road segment using the closure control. Show the route/assignment update, then reopen it. If a closure disconnects an incident from vehicles, the system leaves that incident unassigned instead of drawing a route through the closed road.
6. Open Integrations and show the FHIR bundle example. Explain that importing it replaces the current in-memory hospital directory. It is an integration workflow demonstration, not evidence of a live hospital connection.
7. If time permits, open Benchmarks to show QAOA and fallback decision counts and the separate QAE comparison. The first benchmark request can take longer while results are calculated.

The driver page can show the first active assignment and confirm arrival. Use it only if the presentation has enough time; the operations dashboard is the clearest core flow.

### 4. Explain the quantum part (about 1 minute)

**Short explanation for judges:**

“We express dispatch as a binary optimization problem: should ambulance A respond to incident X? The model rewards covering incidents, gives higher-severity calls more weight, and considers road travel time. It also enforces that one ambulance cannot be assigned to two incidents at once. We use QAOA, a hybrid quantum/classical optimization algorithm, through Qiskit’s Aer simulator to search for assignments. If the solver fails or exceeds its time budget, a classical simulated-annealing fallback keeps the workflow usable.”

**If asked what makes it quantum:**

“QAOA represents candidate solutions in a parameterized quantum circuit and uses a classical optimizer to adjust the circuit parameters. We sample the simulator’s output and decode valid assignments. The current app simulates the circuit on a classical computer; it does not use quantum hardware.”

**Be candid about results:**

“This project tests whether quantum optimization is useful for this dispatch formulation. We are not claiming quantum advantage. In our small measurements, classical simulated annealing is substantially faster, and our separate QAE experiment has not shown consistent sample-efficiency improvement.”

The QAE page/benchmark is a separate experiment for estimating a probability from a time distribution with iterative amplitude estimation. It does **not** calculate the active dispatch plan.

### 5. Explain hospital and ambulance integration (45 seconds)

“The current deployment does not receive live hospital or ambulance feeds. Hospital locations and services can be imported using FHIR R4. For a real hospital connection, the hospital or its integration partner would authorize an endpoint and credentials; we would map its location and service records, agree how live capacity is represented, validate the data, and then update the directory. An active incident can then be matched to reachable facilities using specialty and reported capacity.”

“Ambulance tracking can use an authorized AVL feed or a secured GPS webhook. Each update includes the vehicle identifier, location, and optionally status. ADAS maps the position to a road node and replans. Real incident logs would similarly need a secured, agreed feed and field mapping. The current request log is operator-entered and held in memory; it is not connected to a hospital system and does not persist across backend restarts.”

## The real-feed path, simply

```text
Hospital system (FHIR locations/services + agreed capacity field)
              └── authorized backend connector ──┐
Ambulance AVL/GPS ── authenticated feed/webhook ──┼── validate and map data
Incident intake/log ─ authorized adapter ────────┘          │
                                                            v
                                              road network + dispatch planner
                                                            │
                                      explainable assignments, ETAs, hospital match
```

For a real deployment, the team and provider would still need to agree on authentication, data formats, update frequency, uptime behavior, privacy controls, persistent storage, and operational review. FHIR core location/service records do not provide a universal live bed count, so each hospital must define a trusted capacity field. The current backend is a prototype: most operator APIs are unauthenticated and state is in memory. Never describe the current deployment as a live or production hospital dispatch connection.

## Quick answers to likely judge questions

| Question | Simple answer |
| --- | --- |
| Does the suggested route follow roads? | In the prepared Andheri scenario, yes: it is calculated over a bundled, static OpenStreetMap road extract. The geometry may age and traffic is not live. |
| Is the app using a quantum computer? | No. QAOA runs with Qiskit Aer simulation. |
| Does the quantum solver beat classical methods? | We do not claim that. In the current small benchmark, simulated annealing is faster. The project evaluates the approach and keeps a classical fallback. |
| Are the hospitals and ambulances connected live? | No provider is configured in the deployed project. FHIR import and authenticated AVL integration paths are implemented, and the presentation scenario supplies repeatable data. |
| What if a route is blocked? | The operator can close a road segment. ADAS replans over the remaining graph and leaves the incident unassigned if no route remains. |
| Does the incident log persist? | Not currently. It is held in backend memory and resets on restart. A real deployment needs persistent storage and access control. |

## Team preparation checklist

- Open the public app and confirm the dashboard loads before presenting.
- Load the same prepared scenario and use the same closure segment during practice.
- Decide who will introduce the problem, operate the map, and explain the quantum method.
- Keep the honest limitations above ready; they make the technical scope clear.
- If the public service has restarted, reload the scenario. If a benchmark is slow, continue with the dashboard walkthrough while it calculates.
