import { useEffect, useRef, useState } from "react";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";
import { api } from "./api";
import Pages from "./Pages";

export default function App() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path !== "/dashboard") return <Pages path={path} />;
  const [incidents, setIncidents] = useState([]);
  const [mapData, setMapData] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [log, setLog] = useState([]);
  const [decisionCounts, setDecisionCounts] = useState({});
  const [requests, setRequests] = useState([]);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState("");
  const [trafficMode, setTrafficMode] = useState("normal");
  const [comparison, setComparison] = useState(null);
  const [roadSegments, setRoadSegments] = useState([]);
  const [selectedRoad, setSelectedRoad] = useState("");
  const pollRef = useRef(null);
  const pollInFlightRef = useRef(false);
  const replanInFlightRef = useRef(null);

  async function refresh() {
    try {
      const [active, counts, requestLog, liveMap, closures] = await Promise.all([
        api.activeIncidents(),
        api.decisionCounts().catch(() => ({})),
        api.requests().catch(() => []),
        api.mapState().catch(() => null),
        api.closures().catch(() => ({ segments: [] })),
      ]);
      setIncidents(active);
      setDecisionCounts(counts);
      setRequests(requestLog);
      setMapData(liveMap);
      const segments = closures.segments ?? [];
      setRoadSegments(segments);
      setSelectedRoad((current) => segments.some((segment) => `${segment.source}-${segment.target}` === current)
        ? current
        : (() => { const first = segments.find((segment) => segment.major && !segment.closed) ?? segments.find((segment) => !segment.closed) ?? segments[0]; return first ? `${first.source}-${first.target}` : ""; })());
      setTrafficMode(liveMap?.traffic_mode ?? trafficMode);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }

  async function replan() {
    if (replanInFlightRef.current) return replanInFlightRef.current;
    const task = (async () => {
    try {
      const assignments = await api.replan();
      setAssignments(assignments);
      api.comparison().then(setComparison).catch(() => {});
      const stamp = new Date().toLocaleTimeString();
      const lines = assignments.map(
        (a) => `${stamp} — Incident #${a.incident_id} → Ambulance ${a.ambulance_id} (${Math.round(a.travel_time_sec)}s)`
      );
      setLog((prev) => [...lines, ...prev].slice(0, 50));
    } catch (error) {
      setNotice(`Dispatch planning unavailable: ${error.message}`);
    }
    })();
    replanInFlightRef.current = task;
    try {
      await task;
    } finally {
      replanInFlightRef.current = null;
    }
  }

  async function pollDashboard(advance = false) {
    if (pollInFlightRef.current) return;
    pollInFlightRef.current = true;
    try {
      if (advance) await api.tick(30).catch(() => {});
      await refresh();
      await replan();
    } finally {
      pollInFlightRef.current = false;
    }
  }

  async function runAction(action, successMessage) {
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
      await refresh();
      await replan();
    } catch (error) {
      setNotice(`Action failed: ${error.message}`);
    }
  }

  useEffect(() => {
    pollDashboard();
    pollRef.current = setInterval(() => pollDashboard(true), 15000);
    return () => clearInterval(pollRef.current);
  }, []);

  const assignmentsByIncident = new Map(
    assignments.map((assignment) => [assignment.incident_id, assignment])
  );
  const mapIncidents = (mapData?.incidents ?? incidents).map((incident) => {
    const assignment = mapData?.routes?.find((route) => route.incident_id === incident.id) ?? assignmentsByIncident.get(incident.id);
    const position = incident.position;
    const route = assignment?.path ?? assignment?.route;
    return { ...incident, lat: incident.lat ?? position?.lat, lon: incident.lon ?? position?.lon, ...assignment, route: route?.map((point) => Array.isArray(point) ? point : [point.lat, point.lon]) };
  });
  const mapHospitals = mapData?.hospitals ?? [];
  const mapAmbulances = mapData?.ambulances ?? [];
  const closedRoadSegments = roadSegments.filter((segment) => segment.closed);
  const selectedSegment = roadSegments.find((segment) => `${segment.source}-${segment.target}` === selectedRoad);
  const openSegment = roadSegments.find((segment) => segment.major && !segment.closed) ?? roadSegments.find((segment) => !segment.closed);
  const roadChoice = selectedSegment ?? openSegment;

  return (
    <div className="dashboard">
      <nav className="topbar">
        <a className="brand" href="/" aria-label="ADAS home"><span className="dot" /> ADAS</a>
        <nav className="site-nav" aria-label="Main navigation"><a href="/dashboard" aria-current="page">Map</a><a href="/lane-plan">Lane plan</a><a href="/benchmarks">Benchmarks</a><a href="/integrations">Integrations</a><a href="/driver">Driver</a><a href="/docs">Docs</a></nav>
        <div className={`status ${connected ? "live" : "down"}`}>
          <span className="status-dot" /> {connected ? "Live" : "Reconnecting…"}
        </div>
      </nav>
      {notice && <div className="dashboard-notice" role="status">{notice}</div>}
      <div className="dashboard-body">
        <div className="map-pane">
          <div className="map-toolbar">
            <div><strong>Response overview</strong><span>Multi-unit dispatch · {incidents.length} active incidents</span><span className="map-source">{mapData?.network?.source === "OpenStreetMap" ? `OpenStreetMap road paths${mapData.network.extract_date ? ` · extract ${mapData.network.extract_date}` : ""}` : "Road-network route paths"}</span></div>
            <div className="map-controls">
              <label htmlFor="traffic-mode">Traffic</label>
              <select id="traffic-mode" value={trafficMode} onChange={(event) => runAction(async () => { const result = await api.setTrafficMode(event.target.value); setTrafficMode(result.traffic_mode); }, `Traffic updated to ${event.target.value}. Recalculating routes.`)}>
                <option value="normal">Normal</option><option value="peak">Peak congestion</option><option value="event">Major event</option>
              </select>
              <label htmlFor="road-segment">Road segment</label>
              <select id="road-segment" value={selectedRoad} onChange={(event) => setSelectedRoad(event.target.value)}>
                {roadSegments.map((segment) => <option key={`${segment.source}-${segment.target}`} value={`${segment.source}-${segment.target}`}>{segment.major ? "Main corridor" : "Road"} · {segment.source}–{segment.target}{segment.closed ? " · closed" : ""}</option>)}
              </select>
              <button className="closure-button" disabled={!roadChoice} onClick={() => runAction(() => api.setClosure(roadChoice.source, roadChoice.target, !roadChoice.closed), roadChoice.closed ? "Road reopened. Dispatch routes recalculated." : "Road closure applied. Dispatch routes recalculated.")}>{roadChoice?.closed ? "Reopen road" : "Close road & reroute"}</button>
              <button onClick={() => runAction(api.loadShowcaseScenario, "Multi-incident response scenario loaded.")}>Load response scenario</button>
            </div>
          </div>
          {comparison && <div className="comparison-bar" role="status"><strong>Dispatch plan comparison</strong><span>Coordinated plan: {Math.round((comparison.optimized.combined_eta_sec ?? 0) / 60)} min · {comparison.optimized.assigned} assigned · {comparison.optimized.unassigned} unassigned</span><span>Nearest-idle baseline: {Math.round((comparison.baseline_result.combined_eta_sec ?? 0) / 60)} min · {comparison.baseline_result.assigned} assigned · {comparison.baseline_result.unassigned} unassigned</span><span>{comparison.same_coverage ? `${Math.round(Math.abs(comparison.eta_delta_sec) / 60)} min ${comparison.eta_delta_sec >= 0 ? "faster than" : "slower than"} baseline` : "Coverage differs; compare assignment counts"}</span></div>}
          <MapView incidents={mapIncidents} hospitals={mapHospitals} ambulances={mapAmbulances} closedSegments={closedRoadSegments} />
        </div>
        <Sidebar
          incidents={incidents}
          assignments={assignments}
          log={log}
          requests={requests}
          decisionCounts={decisionCounts}
          onCreateRequest={(request) => runAction(() => api.createRequest(request), "Request received and added to the active response queue.")}
        />
      </div>
    </div>
  );
}
