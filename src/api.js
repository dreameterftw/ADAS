// Single source of truth for the backend URL.
// Local dev hits localhost; the deployed build reads this from an env var
// set at build time (VITE_API_URL), so nothing points at localhost in prod.
export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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
  loadDemoScenario: () => post("/incidents/demo/scenario"),
  resetDemo: () => post("/demo/reset"),
  decisionCounts: () => get("/benchmarks/decisions"),
};
