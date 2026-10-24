import { useState } from "react";

export default function Sidebar({ incidents, assignments = [], log, requests, decisionCounts, onCreateRequest }) {
  const [form, setForm] = useState({ caller: "Hospital intake", location: "Andheri East, Mumbai", severity: 4, latitude: "19.12", longitude: "72.8472", notes: "" });
  const [saving, setSaving] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await onCreateRequest({ ...form, severity: Number(form.severity), latitude: Number(form.latitude), longitude: Number(form.longitude) });
    } finally { setSaving(false); }
  }

  return (
    <aside className="sidebar">
      <section className="request-entry">
        <div className="sidebar-header"><span>New request</span><span className="muted">Operator entry</span></div>
        <form onSubmit={submit}>
          <label>Source<input value={form.caller} maxLength="100" required onChange={(e) => setForm({ ...form, caller: e.target.value })} /></label>
          <label>Location<input value={form.location} maxLength="160" required onChange={(e) => setForm({ ...form, location: e.target.value })} /></label>
          <div className="coordinate-fields">
            <label>Latitude<input type="number" min="-90" max="90" step="any" value={form.latitude} required onChange={(e) => setForm({ ...form, latitude: e.target.value })} /></label>
            <label>Longitude<input type="number" min="-180" max="180" step="any" value={form.longitude} required onChange={(e) => setForm({ ...form, longitude: e.target.value })} /></label>
          </div>
          <label>Priority<select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>{[5, 4, 3, 2, 1].map((level) => <option key={level} value={level}>Level {level}{level === 5 ? " · Critical" : level === 4 ? " · High" : ""}</option>)}</select></label>
          <label>Intake notes<textarea rows="2" maxLength="500" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional details for dispatch" /></label>
          <button type="submit" disabled={saving}>{saving ? "Adding request…" : "Add to request log"}</button>
        </form>
      </section>
      <div className="sidebar-header">
        <span>Active responses</span>
        <span className="muted">{incidents.length}</span>
      </div>

      <div className="sidebar-header"><span>Request log</span><span className="muted">{requests?.length ?? 0}</span></div>
      <div className="request-log">
        {!requests?.length && <p className="muted small">New operator-entered calls will appear here.</p>}
        {requests?.map((request) => <article className="request-item" key={request.request_id}><strong>#{request.incident_id} · {request.location}</strong><span>{request.caller} · Priority {request.severity}</span><small>{new Date(request.received_at).toLocaleString()} · {request.status}</small>{request.notes && <small>{request.notes}</small>}</article>)}
      </div>

      <div className="incident-list">
        {incidents.length === 0 && <p className="muted small">No active incidents.</p>}
        {incidents.map((inc) => (
          <div className="incident-card" key={inc.id}>
            <div className="incident-row">
              <span className={`severity-badge sev-${inc.severity}`}>S{inc.severity}</span>
              <span>{inc.location_node ?? `Incident ${inc.id}`}</span>
            </div>
            {assignments.find((item) => item.incident_id === inc.id) && <div className="incident-assignment"><p>Ambulance {assignments.find((item) => item.incident_id === inc.id).ambulance_id} · {Math.ceil(assignments.find((item) => item.incident_id === inc.id).travel_time_sec / 60)} min to scene</p><small>{assignments.find((item) => item.incident_id === inc.id).assignment_reason}</small>{assignments.find((item) => item.incident_id === inc.id).fallback_reason && <small>Planner note: {assignments.find((item) => item.incident_id === inc.id).fallback_reason}</small>}</div>}
          </div>
        ))}
      </div>

      <div className="sidebar-header">
        <span>Dispatch activity</span>
        <span className="muted">QAOA {decisionCounts.qaoa ?? 0} · Fallback {decisionCounts.fallback ?? 0}</span>
      </div>
      <div className="solver-log">
        {log.length === 0 && <p className="muted small">No decisions yet.</p>}
        {log.map((line, i) => (
          <div key={i} className="log-line">{line}</div>
        ))}
      </div>

    </aside>
  );
}
