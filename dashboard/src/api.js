// Keep the production API fixed to Render; local .env.local values only apply
// to development and must not leak into or redirect the hosted build.
const localApiUrl = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const API_URL = import.meta.env.PROD
  ? "https://adas-backend-3mz9.onrender.com"
  : localApiUrl;

async function get(path) {
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function post(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_URL}${path}${qs ? `?${qs}` : ""}`, { method: "POST" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  health: () => get("/health"),
  activeIncidents: () => get("/incidents/active"),
  tick: (dt_seconds = 30) => post("/incidents/tick", { dt_seconds }),
  replan: () => post("/assignments/replan"),
  comparison: () => get("/assignments/comparison"),
  decisionCounts: () => get("/benchmarks/decisions"),
  mapState: () => get("/map/state"),
  loadShowcaseScenario: () => post("/operations/scenario/showcase"),
  setTrafficMode: (mode) => fetch(`${API_URL}/operations/traffic`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Traffic update failed: ${res.status}`);
    return data;
  }),
  closures: () => get("/operations/closures"),
  setClosure: (source, target, closed) => fetch(`${API_URL}/operations/closures?replan=false`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, target, closed }),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Road closure update failed: ${res.status}`);
    return data;
  }),
  integrationStatus: () => get("/operations/integrations"),
  syncIntegrations: () => post("/operations/sync"),
  importHospitalBundle: (bundle) => fetch(`${API_URL}/operations/hospitals/fhir-bundle`, {
    method: "POST",
    headers: { "Content-Type": "application/fhir+json" },
    body: JSON.stringify(bundle),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `FHIR import failed: ${res.status}`);
    return data;
  }),
  requests: () => get("/incidents/requests"),
  createRequest: (request) => fetch(`${API_URL}/incidents/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
    return data;
  }),
  scalingPreview: () => get("/benchmarks/scaling/preview"),
  qaeEfficiency: () => get("/benchmarks/qae-efficiency"),
  driverState: async () => {
    const [incidents, assignments] = await Promise.all([
      get("/incidents/active"),
      post("/assignments/replan"),
    ]);
    const assignmentByIncident = new Map(assignments.map((item) => [item.incident_id, item]));
    return incidents.map((incident) => ({ ...incident, ...assignmentByIncident.get(incident.id) }));
  },
  resolveIncident: (incidentId, ambulanceId) => post(`/incidents/${incidentId}/resolve`, { ambulance_id: ambulanceId }),
};
