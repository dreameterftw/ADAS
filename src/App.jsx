import { useEffect, useRef, useState } from "react";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";
import { api } from "./api";

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [log, setLog] = useState([]);
  const [decisionCounts, setDecisionCounts] = useState({});
  const [connected, setConnected] = useState(false);
  const pollRef = useRef(null);

  async function refresh() {
    try {
      const [active, counts] = await Promise.all([
        api.activeIncidents(),
        api.decisionCounts().catch(() => ({})),
      ]);
      setIncidents(active);
      setDecisionCounts(counts);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }

  async function replan() {
    try {
      const assignments = await api.replan();
      setAssignments(assignments);
      const stamp = new Date().toLocaleTimeString();
      const lines = assignments.map(
        (a) => `${stamp} — Incident #${a.incident_id} → Ambulance ${a.ambulance_id} (${Math.round(a.travel_time_sec)}s)`
      );
      setLog((prev) => [...lines, ...prev].slice(0, 50));
    } catch {
      /* non-fatal for the demo */
    }
  }

  useEffect(() => {
    refresh();
    replan();
    pollRef.current = setInterval(async () => {
      await api.tick(30).catch(() => {});
      await replan();
      await refresh();
    }, 5000); // poll every 5s — adjust for demo pacing
    return () => clearInterval(pollRef.current);
  }, []);

  const assignmentsByIncident = new Map(
    assignments.map((assignment) => [assignment.incident_id, assignment])
  );
  const mapIncidents = incidents.map((incident) => ({
    ...incident,
    ...assignmentsByIncident.get(incident.id),
  }));

  return (
    <div className="dashboard">
      <nav className="topbar">
        <div className="brand"><span className="dot" /> ADAS</div>
        <div className={`status ${connected ? "live" : "down"}`}>
          <span className="status-dot" /> {connected ? "Live" : "Reconnecting…"}
        </div>
        <button className="ghost" onClick={() => api.resetDemo().then(refresh)}>Reset demo</button>
      </nav>
      <div className="dashboard-body">
        <div className="map-pane">
          <MapView incidents={mapIncidents} />
        </div>
        <Sidebar
          incidents={incidents}
          log={log}
          decisionCounts={decisionCounts}
          onReset={() => api.resetDemo().then(refresh)}
          onLoadScenario={() => api.loadDemoScenario().then(refresh)}
        />
      </div>
    </div>
  );
}
