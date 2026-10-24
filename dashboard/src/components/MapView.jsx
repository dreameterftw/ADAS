import { useEffect, useRef } from "react";
import L from "leaflet";

const MAP_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const SIGNAL = "#C8402A";
const CONFIDENCE = "#2F6F62";

function pulsingIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div class="map-pulse-wrap">
             <div class="map-pulse-ring" style="border-color:${color}"></div>
             <div class="map-pulse-dot" style="background:${color}"></div>
           </div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[character]);
}

const incidentIcon = pulsingIcon(SIGNAL);
const ambulanceIcon = pulsingIcon(CONFIDENCE);
const hospitalIcon = L.divIcon({
  className: "",
  html: `<div class="map-hospital-ring"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

export default function MapView({ incidents, hospitals = [], ambulances = [], closedSegments = [], center = [19.119, 72.846], zoom = 13 }) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const markersRef = useRef([]);
  const lastFitKeyRef = useRef("");

  useEffect(() => {
    if (mapRef.current) return; // init once
    const map = L.map(containerRef.current, {
      center,
      zoom,
      zoomControl: true,
      attributionControl: true,
    });
    L.tileLayer(MAP_TILES, {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);
    mapRef.current = map;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((m) => map.removeLayer(m));
    markersRef.current = [];
    const bounds = [];

    for (const inc of incidents) {
      if (inc.lat == null || inc.lon == null) continue; // skip until real coords wired in
      bounds.push([inc.lat, inc.lon]);

      const marker = L.marker([inc.lat, inc.lon], { icon: incidentIcon })
        .addTo(map)
        .bindPopup(
          `<b>${escapeHtml(inc.location_node ?? "Incident")}</b><br/>severity ${escapeHtml(inc.severity)}`
        );
      markersRef.current.push(marker);

      if (inc.route) {
        const line = L.polyline(inc.route, {
          color: SIGNAL,
          weight: 3,
          dashArray: "6 8",
          className: "route-animate",
        }).addTo(map);
        markersRef.current.push(line);
        bounds.push(...inc.route);
      }

      if (inc.hospital_lat != null && inc.hospital_lon != null) {
        bounds.push([inc.hospital_lat, inc.hospital_lon]);
        const h = L.marker([inc.hospital_lat, inc.hospital_lon], { icon: hospitalIcon })
          .addTo(map)
          .bindPopup(`<b>${inc.hospital_name ?? "Hospital"}</b>`);
        markersRef.current.push(h);
      }
    }

    for (const hospital of hospitals) {
      const point = hospital.position ? [hospital.position.lat, hospital.position.lon] : hospital.lat != null && hospital.lon != null ? [hospital.lat, hospital.lon] : null;
      if (!point) continue;
      bounds.push(point);
      markersRef.current.push(L.marker(point, { icon: hospitalIcon }).addTo(map).bindPopup(`<b>Hospital ${escapeHtml(hospital.id)}</b><br/>${escapeHtml(hospital.available_beds ?? "—")} available beds`));
    }

    for (const ambulance of ambulances) {
      const point = ambulance.position ? [ambulance.position.lat, ambulance.position.lon] : ambulance.lat != null && ambulance.lon != null ? [ambulance.lat, ambulance.lon] : null;
      if (!point) continue;
      bounds.push(point);
      markersRef.current.push(L.marker(point, { icon: ambulanceIcon }).addTo(map).bindPopup(`<b>Ambulance ${escapeHtml(ambulance.id)}</b><br/>${ambulance.available ? "Available" : "Assigned"}`));
    }

    for (const segment of closedSegments) {
      const start = segment.source_position && [segment.source_position.lat, segment.source_position.lon];
      const end = segment.target_position && [segment.target_position.lat, segment.target_position.lon];
      if (!start || !end) continue;
      bounds.push(start, end);
      const line = L.polyline([start, end], { color: SIGNAL, weight: 7, dashArray: "7 7", opacity: 0.95 })
        .addTo(map)
        .bindPopup("Road closed · dispatch routes avoid this segment");
      markersRef.current.push(line);
    }

    const fitKey = bounds
      .map((point) => point.map((coordinate) => coordinate.toFixed(5)).join(","))
      .sort()
      .join("|");
    if (bounds.length && fitKey !== lastFitKeyRef.current) {
      lastFitKeyRef.current = fitKey;
      requestAnimationFrame(() => {
        map.invalidateSize({ pan: false });
        map.fitBounds(bounds, { padding: [48, 48], maxZoom: 17 });
      });
    }
  }, [incidents, hospitals, ambulances, closedSegments]);

  return <div className="map-shell"><div ref={containerRef} className="map-canvas" />{closedSegments.length > 0 && <div className="map-key"><span /> Closed road · routes avoid this segment</div>}</div>;
}
