export default function Sidebar({ incidents, log, decisionCounts, onReset, onLoadScenario }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span>Active Incidents</span>
        <span className="muted">{incidents.length}</span>
      </div>

      <div className="incident-list">
        {incidents.length === 0 && <p className="muted small">No active incidents.</p>}
        {incidents.map((inc) => (
          <div className="incident-card" key={inc.id}>
            <div className="incident-row">
              <span className={`severity-badge sev-${inc.severity}`}>S{inc.severity}</span>
              <span>{inc.location_node ?? `Incident ${inc.id}`}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-header">
        <span>Solver Log</span>
        <span className="muted">QAOA {decisionCounts.qaoa ?? 0} · Fallback {decisionCounts.fallback ?? 0}</span>
      </div>
      <div className="solver-log">
        {log.length === 0 && <p className="muted small">No decisions yet.</p>}
        {log.map((line, i) => (
          <div key={i} className="log-line">{line}</div>
        ))}
      </div>

      <div className="sidebar-actions">
        <button onClick={onLoadScenario}>Load demo scenario</button>
        <button className="ghost" onClick={onReset}>Reset demo</button>
      </div>
    </aside>
  );
}
