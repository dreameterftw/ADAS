import { useEffect, useState } from "react";
import { api } from "./api";
import MapView from "./components/MapView";
import exampleHospitalBundle from "./data/example-hospital-bundle.json";

const navItems = [["/", "Overview"], ["/dashboard", "Map"], ["/lane-plan", "Lane plan"], ["/benchmarks", "Benchmarks"], ["/integrations", "Integrations"], ["/driver", "Driver"], ["/docs", "Docs"]];

function Shell({ children }) {
  const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
  const activePath = currentPath === "/laning" ? "/lane-plan" : currentPath;
  return <div className="content-page light-page"><header className="content-header"><a className="content-brand" href="/" aria-label="ADAS home">ADAS<span>.</span><small>Emergency response</small></a><nav aria-label="Main navigation">{navItems.map(([href, label]) => <a key={href} href={href} aria-current={activePath === href ? "page" : undefined}>{label}</a>)}</nav><a className="header-action" href="/dashboard">Open response center <span aria-hidden="true">→</span></a></header>{children}<footer><span>ADAS</span><span>Emergency response decision support</span><a href="/docs">System guide</a></footer></div>;
}

function Landing() {
  return <div className="content-page light-page landing-site">
    <header className="landing-header">
      <a className="landing-brand" href="/" aria-label="ADAS home">
        <span className="landing-brand-icon" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M3 17h6l3-8 5 16 4-12 3 4h5"/></svg></span>
        <span>ADAS<span className="brand-period">.</span></span>
      </a>
      <nav aria-label="Landing page sections">
        <a href="#how">How it works</a><a href="#quantum">Why quantum</a><a href="#research">Research</a><a href="#evidence">Evidence</a>
      </nav>
      <a className="landing-nav-cta" href="/dashboard">Explore ADAS <span aria-hidden="true">↗</span></a>
    </header>

    <main>
      <section className="landing-hero" aria-labelledby="landing-title">
        <img className="landing-hero-image" src="/landing/ambulance-team.jpg" alt="Emergency medical responders beside an ambulance" fetchPriority="high" />
        <div className="landing-hero-shade" />
        <div className="landing-hero-content">
          <p className="landing-kicker"><span />CONNECTED EMERGENCY RESPONSE</p>
          <h1 id="landing-title">Every minute.<br/>Every decision.<br/><span>Made together.</span></h1>
          <p className="landing-hero-lead">One ambulance. The right hospital. A clear route.<br/>ADAS connects the decisions that save time —<br/>when time matters most.</p>
          <div className="landing-hero-actions"><a className="landing-button landing-button-primary" href="#how">See how it works <span aria-hidden="true">↗</span></a><a className="landing-button landing-button-outline" href="#quantum">Why quantum <span aria-hidden="true">→</span></a></div>
        </div>
      </section>

      <div className="landing-container">
        <section className="landing-context-strip" aria-label="ADAS response capabilities"><span>A CITY-WIDE DECISION LAYER</span><strong>Ambulance dispatch <i>/</i> Hospital matching <i>/</i> Traffic-aware routing</strong><a href="/dashboard">ONE CONNECTED PLAN <span aria-hidden="true">↗</span></a></section>

        <section className="landing-impact" aria-labelledby="impact-title">
          <div className="impact-stat"><strong>3</strong><span>decisions<br/>one response</span></div>
          <div className="impact-copy"><p className="landing-eyebrow">THE COST OF DISCONNECTED DECISIONS</p><h2 id="impact-title">In an emergency, disconnected decisions cost time.</h2><p>A delayed dispatch. A congested intersection. A hospital without available capacity. These are connected parts of the same response.</p><strong>ADAS helps coordinate them in one plan.</strong></div>
        </section>

        <section className="landing-section" id="how" aria-labelledby="how-title">
          <div className="landing-section-heading"><div><p className="landing-eyebrow">HOW IT WORKS</p><h2 id="how-title">Three decisions.<br/>One better response.</h2></div><p>From the first call to the hospital handoff, each part of the plan works in sync.</p></div>
          <div className="landing-feature-grid">
            <article className="landing-feature">
              <div className="landing-feature-image"><img src="/landing/dispatcher.jpg" alt="Emergency dispatcher coordinating a response" loading="lazy"/><span>01</span></div>
              <h3>Who responds</h3><p>Match available ambulances and reachable hospitals by incident severity, travel time, specialty, and reported capacity.</p><div className="landing-feature-foot"><span>DISPATCH + HOSPITAL MATCHING</span><span aria-hidden="true">↗</span></div>
            </article>
            <article className="landing-feature">
              <div className="landing-feature-image"><img src="/landing/city-traffic.jpg" alt="Busy city traffic in India" loading="lazy"/><span>02</span></div>
              <h3>How it gets there</h3><p>Route over mapped road segments, account for the selected traffic scenario, and replan when an operator closes a road.</p><div className="landing-feature-foot"><span>ROAD ROUTING + REROUTING</span><span aria-hidden="true">↗</span></div>
            </article>
            <article className="landing-feature landing-feature-plan">
              <div className="plan-card-top"><span><i /> PLAN EXPLANATION</span><span>ADAS</span></div>
              <strong className="plan-card-title">Every assignment has a reason.</strong>
              <div className="plan-factor"><span>01</span><div><strong>Incident priority</strong><small>Severity informs dispatch urgency</small></div><b>✓</b></div>
              <div className="plan-factor"><span>02</span><div><strong>Road travel time</strong><small>Route follows mapped streets</small></div><b>✓</b></div>
              <div className="plan-factor"><span>03</span><div><strong>Hospital match</strong><small>Specialty and reported capacity</small></div><b>✓</b></div>
              <p className="plan-card-note">A clear view of the factors considered.</p>
              <h3>How sure we are</h3><p>See the selected solver, fallback status, assignment rationale, and comparison with a nearest-available baseline.</p><div className="landing-feature-foot"><span>EXPLAINABLE DISPATCH</span><span aria-hidden="true">↗</span></div>
            </article>
          </div>
        </section>

        <section className="landing-quantum" id="quantum" aria-labelledby="quantum-title">
          <div className="quantum-copy"><p className="landing-eyebrow">WHY QUANTUM</p><h2 id="quantum-title">Not a buzzword.<br/>A research question.</h2><p className="quantum-lead">Quantum-assisted where it helps.<br/>Classically checked where it matters.</p>
            <article className="quantum-method"><span className="method-tag">QAOA</span><div><h3>The assignment search</h3><p>QAOA explores ambulance-to-incident assignments as a constrained optimization problem. A classical optimizer tunes the circuit; a classical fallback keeps dispatch planning available.</p><small>Runs on the Qiskit Aer simulator, not quantum hardware. Current benchmarks do not show a quantum speed advantage.</small></div></article>
            <article className="quantum-method"><span className="method-tag method-tag-green">QAE</span><div><h3>A separate estimation study</h3><p>Iterative amplitude estimation is compared with Monte Carlo on simulated response-time distributions.</p><small>This experiment is separate from the live dispatch planner; it does not provide an on-time probability for current assignments.</small></div></article>
          </div>
          <div className="quantum-visual" aria-label="Illustration of a road-network dispatch route">
            <div className="quantum-visual-top"><span><i /> CONNECTED RESPONSE</span><span>ROAD-NETWORK PLAN</span></div>
            <div className="quantum-route-art"><div className="route-grid-lines"/><svg viewBox="0 0 520 300" role="img" aria-label="A route connecting an incident, road junctions, and hospital"><path className="route-street" d="M28 242H168V190H300V108H468"/><path className="route-highlight" d="M28 242H168V190H300V108H468"/><circle cx="28" cy="242" r="9" className="route-start"/><circle cx="168" cy="190" r="7" className="route-waypoint"/><circle cx="300" cy="108" r="7" className="route-waypoint"/><circle cx="468" cy="108" r="11" className="route-hospital"/></svg><span className="route-label route-label-start">INCIDENT<br/><small>Unit assigned</small></span><span className="route-label route-label-end">HOSPITAL<br/><small>Capacity considered</small></span></div>
            <div className="quantum-visual-foot"><span>✓ Road graph route</span><span>✓ Assignment rationale</span></div>
          </div>
        </section>

        <section className="landing-section landing-research" id="research" aria-labelledby="research-title">
          <div className="landing-section-heading"><div><p className="landing-eyebrow">RESEARCH &amp; REAL-WORLD CONTEXT</p><h2 id="research-title">Built for real roads.<br/>Grounded in real questions.</h2></div><p>Indian urban response is the starting point. The system is designed to make coordination decisions visible.</p></div>
          <div className="research-layout"><img src="/landing/city-traffic.jpg" alt="Dense city traffic illustrating route and congestion challenges" loading="lazy"/><div className="research-points"><article><span>01 / TRAVEL-TIME VARIABILITY</span><h3>An average ETA isn’t the whole story.</h3><p>Congestion changes through the day. ADAS lets operators compare built-in traffic scenarios and see how estimated response times change.</p></article><article><span>02 / CITY-WIDE COORDINATION</span><h3>A response is more than a route.</h3><p>Ambulance position, hospital specialty and reported capacity, and road access all affect the plan.</p></article><p className="research-caveat">The Andheri showcase uses a static OpenStreetMap road extract. Traffic scenarios are simulated; live traffic, hospital, and ambulance-provider feeds are not connected.</p></div></div>
        </section>

        <section className="landing-evidence" id="evidence" aria-labelledby="evidence-title">
          <div className="landing-section-heading"><div><p className="landing-eyebrow">EVIDENCE, NOT PROMISES</p><h2 id="evidence-title">See how the system behaves.</h2></div><p>Explore the route data, dispatch comparison, and measured solver behavior.</p></div>
          <div className="evidence-grid"><article><span>01</span><h3>Mapped road routes</h3><p>Showcase routes follow mapped OpenStreetMap road edges.</p></article><article><span>02</span><h3>Baseline comparison</h3><p>Compare coordinated assignments with a nearest-available approach on the same snapshot.</p></article><article><span>03</span><h3>Quantum benchmarks</h3><p>Review measured QAOA, fallback, and QAE experiment results with their limitations.</p></article></div>
          <div className="landing-evidence-actions"><a className="landing-button landing-button-dark" href="/benchmarks">Explore the evidence <span aria-hidden="true">↗</span></a><a className="text-link" href="/docs">Read the system guide →</a></div>
        </section>

        <section className="landing-final-cta"><div><p className="landing-eyebrow">ADAS RESPONSE CENTER</p><h2>One connected view<br/>for every request.</h2><p>Review requests, inspect assignments, and follow response routes on the operations map.</p></div><a className="landing-button landing-button-primary" href="/dashboard">Explore ADAS <span aria-hidden="true">↗</span></a></section>
        <p className="landing-disclaimer">ADAS is a decision-support prototype. Provider feeds, live traffic, signal control, and medical dispatch authorization are not connected.</p>
      </div>
    </main>
    <footer className="landing-footer"><a className="landing-brand" href="/" aria-label="ADAS home"><span className="landing-brand-icon" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M3 17h6l3-8 5 16 4-12 3 4h5"/></svg></span><span>ADAS<span className="brand-period">.</span></span></a><span>Emergency response decision support</span><nav aria-label="Footer navigation"><a href="/dashboard">Response center</a><a href="/docs">System guide</a></nav></footer>
  </div>;
}

function LanePlan() {
  const [state, setState] = useState(null); const [error, setError] = useState("");
  useEffect(() => { api.replan().catch(() => {}).then(() => api.mapState()).then(setState).catch((e) => setError(e.message)); }, []);
  const routes = state?.routes ?? [];
  const incidents = (state?.incidents ?? []).map((incident) => ({ ...incident, lat: incident.position?.lat, lon: incident.position?.lon, ...(routes.find((route) => route.incident_id === incident.id) ? { route: routes.find((route) => route.incident_id === incident.id).path.map((point) => [point.lat, point.lon]) } : {}) }));
  const hospitals = state?.hospitals ?? [];
  return <Shell><main className="page-main"><p className="eyebrow">LIVE SIMULATION</p><h1>Lane plan</h1><p className="lead">Current incident routes, ambulance assignments and hospital handoffs from the dispatch simulation.</p>{error && <p className="notice">Route data unavailable: {error}</p>}<div className="lane-layout"><section className="map-card"><MapView incidents={incidents} hospitals={hospitals}/></section><aside className="feature-card"><h2>Active routes</h2>{routes.length ? routes.map((r) => <div className="data-row" key={r.incident_id}><strong>Incident #{r.incident_id}</strong><span>Ambulance {r.ambulance_id} · {Math.ceil(r.travel_time_sec / 60)} min</span><span>Hospital {r.hospital_id ?? "not matched"}</span><small>{r.assignment_reason}</small>{r.fallback_reason && <small>Planner note: {r.fallback_reason}</small>}</div>) : incidents.length ? incidents.map((incident) => <div className="data-row" key={incident.id}><strong>Incident #{incident.id} · severity {incident.severity}</strong><span>Location node {incident.location_node}</span><span>Assignment unavailable from the backend.</span></div>) : <p>{error ? "Could not load route data." : "No active incidents right now. New requests will appear here after they are received."}</p>}<h2>Hospitals</h2>{hospitals.length ? hospitals.map((hospital) => <div className="data-row" key={hospital.id}><strong>Hospital {hospital.id}</strong><span>{hospital.available_beds} available beds · node {hospital.node}</span></div>) : <p>Hospital data unavailable.</p>}<a className="primary-link" href="/dashboard">Open dispatch →</a></aside></div><p className="disclaimer">Routes use the scenario road network and any operator-selected closures. External live traffic data is not connected.</p></main></Shell>;
}

function Benchmarks() {
  const [counts, setCounts] = useState(null); const [results, setResults] = useState(null); const [busy, setBusy] = useState(""); const [error, setError] = useState("");
  useEffect(() => { api.decisionCounts().then(setCounts).catch((e) => setError(e.message)); }, []);
  async function load(label, request) { setBusy(label); setError(""); setResults(null); try { setResults(await request()); } catch (e) { setError(e.message); } finally { setBusy(""); } }
  return <Shell><main className="page-main"><p className="eyebrow">PERFORMANCE EVIDENCE</p><h1>Benchmarks</h1><p className="lead">Review solver activity from this service and request measured comparisons from the research workloads.</p><div className="feature-grid metric-grid"><div><strong>{counts?.qaoa ?? "—"}</strong><span>QAOA decisions</span></div><div><strong>{counts?.fallback ?? "—"}</strong><span>Classical fallback decisions</span></div></div><section className="feature-card"><h2>Measured comparisons</h2><p>Results describe the configured research workloads. They are not service-level guarantees.</p><div className="button-row"><button className="primary-link" disabled={!!busy} onClick={() => load("scaling", api.scalingPreview)}>{busy === "scaling" ? "Loading…" : "Load scaling results"}</button><button className="secondary-link" disabled={!!busy} onClick={() => load("qae", api.qaeEfficiency)}>{busy === "qae" ? "Loading…" : "Load QAE efficiency"}</button></div>{error && <p className="notice">{error}</p>}{results && <pre className="results">{JSON.stringify(results, null, 2)}</pre>}</section></main></Shell>;
}

function Driver() {
  const [items, setItems] = useState(null); const [error, setError] = useState(""); const [message, setMessage] = useState("");
  async function refresh() { try { await api.replan(); const data = await api.mapState(); setItems(data); setError(""); } catch (e) { setError(e.message); } }
  useEffect(() => { refresh(); const timer = setInterval(refresh, 8000); return () => clearInterval(timer); }, []);
  const incident = items?.incidents?.[0]; const route = incident && items.routes?.find((item) => item.incident_id === incident.id);
  async function confirmArrival() { if (!incident || !route) return; try { await api.resolveIncident(incident.id, route.ambulance_id); setMessage(`Arrival confirmed for incident #${incident.id}.`); await refresh(); } catch (e) { setMessage(e.message); } }
  const mapIncidents = incident ? [{ ...incident, lat: incident.position?.lat, lon: incident.position?.lon, route: route?.path?.map((point) => [point.lat, point.lon]) }] : [];
  return <Shell><main className="page-main driver-page"><p className="eyebrow">FIELD VIEW</p><h1>Driver view</h1><p className="lead">Current dispatch assignment from the response service.</p>{error && <p className="notice">Dispatch unavailable: {error}</p>}{incident ? <><section className="driver-map"><MapView incidents={mapIncidents}/></section><div className="feature-card driver-details"><div className="data-row"><strong>Incident #{incident.id}</strong><span>Severity {incident.severity}</span><span>{route ? `Ambulance ${route.ambulance_id}` : "Unassigned"}</span><span>{route ? `Hospital ${route.hospital_id ?? "not matched"}` : "No hospital match"}</span><span>{route ? `${Math.ceil(route.travel_time_sec / 60)} min estimated travel` : "—"}</span></div>{route?.assignment_reason && <p className="assignment-explanation">{route.assignment_reason}</p>}<button className="primary-link" disabled={!route} onClick={confirmArrival}>Confirm arrival</button>{message && <p role="status">{message}</p>}</div></> : !error && items && <section className="feature-card"><h2>No active call</h2><p>There are no active requests right now. New requests entered in the response center will appear here.</p><a className="primary-link" href="/dashboard">Open response center →</a></section>}</main></Shell>;
}

function Docs() {
  return <Shell><main className="page-main"><p className="eyebrow">SYSTEM GUIDE</p><h1>ADAS overview</h1><p className="lead">A decision-support system for coordinated emergency response planning.</p><div className="docs-grid"><section className="feature-card"><h2>Architecture</h2><p>The API combines a road network, dispatch optimization with classical fallback, hospital matching, and a confidence estimator.</p></section><section className="feature-card"><h2>Dispatch and comparison</h2><p>The dashboard compares coordinated dispatch with a nearest-available-unit baseline and explains each ambulance and hospital recommendation.</p></section><section className="feature-card"><h2>Congestion and rerouting</h2><p>Operators can adjust scenario traffic and close or reopen road segments. Dispatch plans recalculate while avoiding closed roads.</p></section><section className="feature-card"><h2>External data</h2><p>Import a FHIR R4 hospital bundle, connect an authorized FHIR endpoint, or send authenticated ambulance GPS updates. Live traffic providers and signal controls are not connected.</p></section><section className="feature-card"><h2>API</h2><p>Live data is served by the Render API: incidents, assignments, hospitals, map state, and benchmarks.</p><a href={`${api.API_URL}/health`} target="_blank" rel="noreferrer">Check API health →</a></section></div></main></Shell>;
}

function Integrations() {
  const [status, setStatus] = useState(null); const [error, setError] = useState(""); const [syncing, setSyncing] = useState(false); const [syncResult, setSyncResult] = useState(null);
  const [bundleText, setBundleText] = useState(""); const [bundleName, setBundleName] = useState(""); const [importing, setImporting] = useState(false); const [importResult, setImportResult] = useState(null);
  async function refresh() { await api.integrationStatus().then(setStatus); }
  useEffect(() => { refresh().catch((e) => setError(e.message)); }, []);
  async function sync() { setSyncing(true); setError(""); try { setSyncResult(await api.syncIntegrations()); await refresh(); } catch (e) { setError(e.message); } finally { setSyncing(false); } }
  async function loadFile(file) { if (!file) return; setError(""); setImportResult(null); setBundleName(file.name); try { setBundleText(await file.text()); } catch { setError("Could not read that file. Choose a valid JSON FHIR Bundle."); } }
  async function importBundle() { setImporting(true); setError(""); setImportResult(null); try { const bundle = JSON.parse(bundleText); setImportResult(await api.importHospitalBundle(bundle)); await refresh(); } catch (e) { setError(e instanceof SyntaxError ? "The selected file is not valid JSON." : e.message); } finally { setImporting(false); } }
  const rows = status ? [["Hospital directory", status.hospital, "FHIR R4 Location and HealthcareService"], ["Ambulance positions", status.ambulance, "Authenticated AVL feed or GPS webhook"], ["Traffic routing", status.traffic, "Scenario congestion and operator-triggered road closures"]] : [];
  function badgeText(label, data) { if (label === "Traffic routing") return "Scenario controls"; if (label === "Hospital directory") return data.configured ? "Endpoint configured" : "FHIR import available"; if (data.feed_configured) return "Feed configured"; if (data.webhook_configured) return "GPS webhook enabled"; return "Awaiting feed"; }
  return <Shell><main className="page-main"><p className="eyebrow">CONNECTIVITY</p><h1>Integration readiness</h1><p className="lead">Connect hospital and ambulance systems when provider access is available. Until then, you can import a FHIR hospital bundle and exercise dispatch with the built-in traffic controls.</p>{error && <p className="notice" role="alert">{error}</p>}<div className="integration-grid">{rows.map(([label, data, standard]) => <section className="feature-card" key={label}><div className="integration-title"><h2>{label}</h2><span className={data.configured ? "integration-ready" : "integration-pending"}>{badgeText(label, data)}</span></div><p>{standard}</p>{label === "Hospital directory" && <small>Live bed counts require the provider’s configured FHIR extension. Imported locations are snapped to the active road network.</small>}{label === "Ambulance positions" && <small>{data.webhook_configured ? "GPS webhook token is configured." : "Webhook endpoint is disabled until AMBULANCE_WEBHOOK_BEARER_TOKEN is set."}</small>}{label === "Traffic routing" && <small>Current mode: {data.mode}. External real-time traffic routing is not connected.</small>}</section>)}</div>
    <section className="feature-card fhir-import"><h2>Import a hospital directory</h2><p>Upload a FHIR R4 Bundle containing Location and HealthcareService resources. Importing replaces the current hospital directory for this running service.</p><div className="button-row"><button type="button" className="secondary-link" onClick={() => { setBundleText(JSON.stringify(exampleHospitalBundle, null, 2)); setBundleName("Built-in FHIR example"); setImportResult(null); setError(""); }}>Use built-in FHIR example</button><label className="file-picker">Choose a FHIR JSON file<input type="file" accept="application/json,.json,application/fhir+json" onChange={(event) => loadFile(event.target.files?.[0])}/></label></div>{bundleName && <p className="selected-file" role="status">Selected: {bundleName}</p>}<button className="primary-link" disabled={!bundleText || importing} onClick={importBundle}>{importing ? "Importing hospitals…" : "Import hospital directory"}</button>{importResult && <p className="success-message" role="status">Imported {importResult.updated} hospitals and {importResult.services} services. {importResult.capacity_note}</p>}</section>
    <section className="feature-card"><h2>Connect provider feeds</h2><p><strong>Hospital:</strong> set HOSPITAL_FHIR_BASE_URL and an authorized bearer token. Map the provider’s live-bed extension with FHIR_BED_COUNT_EXTENSION_URL.</p><p><strong>Ambulance:</strong> set AMBULANCE_FEED_URL for polling or configure AMBULANCE_WEBHOOK_BEARER_TOKEN and POST GPS positions to <code>{api.API_URL}/operations/ambulances/positions</code> using an Authorization: Bearer header.</p><p><strong>Traffic:</strong> use the dashboard’s scenario congestion and road closure controls. A live traffic provider is not connected yet.</p><p className="muted small">Store credentials only in the backend service environment. Do not send patient-identifying data in these feeds.</p><button className="primary-link" disabled={syncing} onClick={sync}>{syncing ? "Syncing feeds…" : "Sync connected feeds"}</button>{syncResult && <pre className="results">{JSON.stringify(syncResult, null, 2)}</pre>}</section></main></Shell>;
}

export default function Pages({ path }) {
  if (path === "/") return <Landing/>;
  if (path === "/laning" || path === "/lane-plan") return <LanePlan/>;
  if (path === "/benchmarks") return <Benchmarks/>;
  if (path === "/driver") return <Driver/>;
  if (path === "/docs") return <Docs/>;
  if (path === "/integrations") return <Integrations/>;
  return <Shell><main className="page-main"><h1>Page not found</h1><p>The requested ADAS page does not exist.</p><a className="primary-link" href="/">Return home →</a></main></Shell>;
}
