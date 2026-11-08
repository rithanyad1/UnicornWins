"use client";

import Link from "next/link";
import { useState } from "react";
import { Panel, IncidentLink, Status } from "@/components/ui/primitives";
import CampusViewer from "@/components/digital-twin/campus-viewer";
import { nodeDevice, useLiveData, type LiveData } from "@/hooks/use-live-data";
import { roomNames, roomStates, SENSOR_ROOM, type RoomState } from "@/lib/rooms";
import { formatTime, readingF, shortId, sparkline, titleCase } from "@/lib/utils";

function MapSidebar({ room, selectRoom, rooms, data }: { room: string; selectRoom: (id: string) => void; rooms: RoomState[]; data: LiveData }) {
  const attention = rooms.filter(item => item.severity === "critical" || item.severity === "warning").length;
  const normal = rooms.filter(item => item.monitored && item.severity === "").length;
  const latest = data.facility?.latest_reading;
  const recent = data.history.slice(-60);
  const temps = recent.map(readingF);
  const trend = temps.length > 5 ? temps.at(-1)! - temps.at(-6)! : 0;
  return <aside id="facility-metrics" className="monitoring-sidebar" aria-label="Facility metrics and rooms">
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Facility overview</h2><span className="sidebar-code">DC-01</span></div>
      <div className="sidebar-counts"><div><strong>{rooms.filter(item => item.monitored).length}</strong><span>Monitored</span></div><div><strong>{attention}</strong><span>Attention</span></div><div><strong>{normal}</strong><span>Normal</span></div></div>
      <div className="distribution-labels"><span>● Normal</span><span>● Attention</span></div>
    </section>
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Thermal activity</h2><span className="sidebar-code">LIVE</span></div>
      <div className="sidebar-temperature"><strong>{latest ? readingF(latest).toFixed(1) : "—"}<span> °F</span></strong><span>{trend > 0.2 ? "↗ Rising" : trend < -0.2 ? "↘ Falling" : "→ Steady"}</span></div>
      {temps.length > 1 && <svg className="sidebar-sparkline" viewBox="0 0 120 40" fill="none" aria-label="Recent temperature trend"><polyline points={sparkline(temps)} stroke="#8973d7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
      <div className="distribution-labels"><span>{formatTime(recent[0]?.recorded_at)}</span><span>{formatTime(recent.at(-1)?.recorded_at)}</span></div>
    </section>
    <section className="sidebar-section room-directory">
      <div className="sidebar-section-heading"><h2>Rooms & zones</h2><span className="sidebar-code">{String(rooms.length).padStart(2, "0")}</span></div>
      {rooms.map(item => { const alert = item.severity === "critical" || item.severity === "warning"; return <button key={item.id} className={`directory-room ${room === item.id ? "active" : ""}`} onClick={() => selectRoom(item.id)} aria-pressed={room === item.id}>
        <span className={`directory-room-id room-${item.id}`}>{item.id}</span><span><strong>{item.name}</strong><small>{item.summary}</small></span><span className="directory-indicator" aria-label={alert ? "Attention" : item.severity === "unknown" ? "Unknown" : "Normal"}>{alert ? "!" : item.severity === "unknown" ? "—" : "●"}</span>
      </button>; })}
    </section>
    <section className="sidebar-section sidebar-environment"><h2>Environment</h2><dl><div><dt>Humidity</dt><dd>{latest ? `${latest.humidity_percent.toFixed(0)} %` : "—"}</dd></div><div><dt>Vibration</dt><dd>{latest ? `${(latest.vibration_g ?? latest.vibration_score).toFixed(3)} g` : "—"}</dd></div><div><dt>Monitoring</dt><dd>{data.status ? titleCase(data.status.operating_mode) : "—"}</dd></div></dl></section>
  </aside>;
}

export default function FacilityDiagram({ initialRoom = "A", compact = false, monitoring = false }: { initialRoom?: string; compact?: boolean; monitoring?: boolean }) {
  const data = useLiveData();
  const rooms = roomStates(data);
  const [room, setRoom] = useState(initialRoom in roomNames ? initialRoom : SENSOR_ROOM);
  const [focusRequest, setFocusRequest] = useState(0);
  const selectRoom = (id: string) => {
    setRoom(id);
    setFocusRequest(request => request + 1);
  };
  const [activePanel, setActivePanel] = useState<"metrics" | "inspector" | null>(null);
  const info = rooms.find(item => item.id === room)!;
  const latest = data.facility?.latest_reading;
  const node = nodeDevice(data);
  const fanOn = latest?.fan ?? node?.actuator_state.fan;
  const emergencies = Object.fromEntries(rooms.filter(item => item.severity === "critical").map(item => [item.id, `${item.name}: ${item.summary}`]));
  const attention = rooms.filter(item => item.severity === "critical" || item.severity === "warning").length;
  return <div className={`facility-layout ${compact ? "compact-map" : ""} ${monitoring ? "monitoring-layout" : ""}`} data-panel={activePanel ?? "none"}>
    {monitoring && <div className="map-panel-toggles" aria-label="Map panels">
      <button aria-expanded={activePanel === "metrics"} aria-controls="facility-metrics" onClick={() => setActivePanel(activePanel === "metrics" ? null : "metrics")}>Facility overview {activePanel === "metrics" ? "×" : "+"}</button>
      <button aria-expanded={activePanel === "inspector"} aria-controls="facility-inspector" onClick={() => setActivePanel(activePanel === "inspector" ? null : "inspector")}>Room {room} details {activePanel === "inspector" ? "×" : "+"}</button>
    </div>}
    {monitoring && <MapSidebar room={room} selectRoom={selectRoom} rooms={rooms} data={data} />}
    <div className={monitoring ? "map-workspace" : "map-standard-view"}>
    {monitoring && <div className="workspace-heading"><div className="workspace-view-links"><span className="active">Facility map</span></div><span className="workspace-floor">Floor 1</span></div>}
    <div className="facility-map" aria-label="Interactive facility map">
      <CampusViewer focusRequest={focusRequest} room={room} selectRoom={selectRoom} emergencies={emergencies} />
    </div>
    {monitoring && <div className="workspace-statusbar"><span><i className="map-status-dot" /> {rooms.filter(item => item.monitored).length} monitored zone</span><span>{attention} needing attention</span><span>{data.liveConnected ? "Live" : "Reconnecting…"}</span></div>}
    </div>
    <Panel id={monitoring ? "facility-inspector" : undefined} className="inspector">{monitoring && <div className="inspector-eyebrow">SELECTED LOCATION <span>{room}</span></div>}<Status muted>{info.severity === "critical" ? "CRITICAL" : info.severity === "warning" ? "WARNING" : info.monitored && info.severity === "" ? "NORMAL" : "NO LIVE DATA"}</Status><h2 className="inspector-title">{info.name}</h2><p>{info.monitored ? `${info.name} / ${node?.device_id ?? "SENTINEL node"}` : "No sensor installed in this room"}</p>{info.monitored && <div className="inspector-reading"><p className="inspector-value">{latest ? `${readingF(latest).toFixed(1)}°` : "—"}</p><p className="small unit">TEMPERATURE / °F</p></div>}<h3>{info.summary}</h3>{info.monitored && node?.status === "CONNECTED" && <p>Fan {fanOn ? `on • ${latest?.fan_speed_percent ?? node.actuator_state.fan_speed_percent ?? 0}%` : "off"} • set by the node<br />Last report {formatTime(node.last_seen)}</p>}{info.incidentId ? <IncidentLink id={info.incidentId}>View incident #{shortId(info.incidentId)} →</IncidentLink> : <Link className="status status-link" href="/overview">View facility overview →</Link>}</Panel>
  </div>;
}
