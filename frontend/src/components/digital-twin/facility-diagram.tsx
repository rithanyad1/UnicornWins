"use client";

import Link from "next/link";
import { useState } from "react";
import { Panel, IncidentLink, Status } from "@/components/ui/primitives";
import CampusViewer from "@/components/digital-twin/campus-viewer";

const roomNames: Record<string, string> = {
  A: "Server hall A", B: "Server hall B", C: "Network room", D: "Power & cooling",
};

function MapSidebar({ room, selectRoom }: { room: string; selectRoom: (id: string) => void }) {
  return <aside id="facility-metrics" className="monitoring-sidebar" aria-label="Facility metrics and rooms">
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Facility overview</h2><span className="sidebar-code">DC-01</span></div>
      <div className="sidebar-counts"><div><strong>4</strong><span>Zones</span></div><div><strong>2</strong><span>Incidents</span></div><div><strong>2</strong><span>Normal</span></div></div>
      <div className="health-distribution" aria-label="Two normal zones and two zones needing attention"><span /><span /></div>
      <div className="distribution-labels"><span>● Normal</span><span>● Attention</span></div>
    </section>
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Thermal activity</h2><span className="sidebar-code">15 MIN</span></div>
      <div className="sidebar-temperature"><strong>34.1<span> °C</span></strong><span>↘ Falling</span></div>
      <img className="sidebar-sparkline" src="/figma/temperature.svg" width="842" height="160" alt="Illustrative temperature trend rising then falling after cooling" />
      <div className="distribution-labels"><span>14:20</span><span>14:32</span></div>
    </section>
    <section className="sidebar-section room-directory">
      <div className="sidebar-section-heading"><h2>Rooms & zones</h2><span className="sidebar-code">04</span></div>
      {Object.entries(roomNames).map(([id, name]) => <button key={id} className={`directory-room ${room === id ? "active" : ""}`} onClick={() => selectRoom(id)} aria-pressed={room === id}>
        <span className={`directory-room-id room-${id}`}>{id}</span><span><strong>{name}</strong><small>{id === "A" ? "Cooling response" : id === "D" ? "Water detected" : "Systems normal"}</small></span><span className="directory-indicator" aria-label={id === "A" || id === "D" ? "Attention" : "Normal"}>{id === "A" || id === "D" ? "!" : "●"}</span>
      </button>)}
    </section>
    <section className="sidebar-section sidebar-environment"><h2>Environment</h2><dl><div><dt>Humidity</dt><dd>45 %</dd></div><div><dt>Vibration</dt><dd>0.08</dd></div><div><dt>Monitoring</dt><dd>Automatic</dd></div></dl></section>
  </aside>;
}

const roomInfo: Record<string, { title: string; location: string; value: string; unit: string; status: string; response: string; incident?: string }> = {
  A: { title: "Rack A-03", location: "Server hall A / sensor T-A03", value: "41.2°", unit: "TEMPERATURE / °C", status: "CRITICAL • RESPONDING", response: "The response is underway.", incident: "1042" },
  B: { title: "Server hall B", location: "Server hall B / sensor T-B01", value: "26.4°", unit: "TEMPERATURE / °C", status: "NORMAL", response: "All systems normal." },
  C: { title: "Network room", location: "Network room / sensor T-C01", value: "25.8°", unit: "TEMPERATURE / °C", status: "NORMAL", response: "All systems normal." },
  D: { title: "Cooling area", location: "Power & cooling / sensor W-D01", value: "Detected", unit: "WATER / MOISTURE", status: "CRITICAL • OPEN", response: "Water inspection required.", incident: "1041" },
};

const emergencyRooms = Object.fromEntries(Object.entries(roomInfo)
  .filter(([, info]) => info.status.startsWith("CRITICAL"))
  .map(([id, info]) => [id, `${info.title}: ${info.response}`]));

export default function FacilityDiagram({ initialRoom = "A", compact = false, monitoring = false }: { initialRoom?: string; compact?: boolean; monitoring?: boolean }) {
  const [room, setRoom] = useState(initialRoom in roomInfo ? initialRoom : "A");
  const [focusRequest, setFocusRequest] = useState(0);
  const selectRoom = (id: string) => {
    setRoom(id);
    setFocusRequest(request => request + 1);
  };
  const [activePanel, setActivePanel] = useState<"metrics" | "inspector" | null>(null);
  const info = roomInfo[room];
  return <div className={`facility-layout ${compact ? "compact-map" : ""} ${monitoring ? "monitoring-layout" : ""}`} data-panel={activePanel ?? "none"}>
    {monitoring && <div className="map-panel-toggles" aria-label="Map panels">
      <button aria-expanded={activePanel === "metrics"} aria-controls="facility-metrics" onClick={() => setActivePanel(activePanel === "metrics" ? null : "metrics")}>Facility overview {activePanel === "metrics" ? "×" : "+"}</button>
      <button aria-expanded={activePanel === "inspector"} aria-controls="facility-inspector" onClick={() => setActivePanel(activePanel === "inspector" ? null : "inspector")}>Room {room} details {activePanel === "inspector" ? "×" : "+"}</button>
    </div>}
    {monitoring && <MapSidebar room={room} selectRoom={selectRoom} />}
    <div className={monitoring ? "map-workspace" : "map-standard-view"}>
    {monitoring && <div className="workspace-heading"><div className="workspace-view-links"><span className="active">Facility map</span></div><span className="workspace-floor">Floor 1</span></div>}
    <div className="facility-map" aria-label="Interactive facility map">
      <CampusViewer focusRequest={focusRequest} room={room} selectRoom={selectRoom} emergencies={emergencyRooms} />
    </div>
    {monitoring && <div className="workspace-statusbar"><span><i className="map-status-dot" /> 4 monitored zones</span><span>2 active incidents</span><span>Illustrative snapshot</span></div>}
    </div>
    <Panel id={monitoring ? "facility-inspector" : undefined} className="inspector">{monitoring && <div className="inspector-eyebrow">SELECTED LOCATION <span>{room}</span></div>}<Status muted>{info.status}</Status><h2 className="inspector-title">{compact && room === "A" ? "Temperature sensor" : info.title}</h2><p>{info.location}</p><div className="inspector-reading"><p className="inspector-value">{compact && room === "A" ? "38.2 °C" : info.value}</p><p className="small unit">{info.unit}</p></div><h3>{info.response}</h3>{room === "A" ? <><p>Fan active • Pico confirmed<br />Vent open / 90° reported</p><p>Recovery verification pending</p></> : <p>{room === "D" ? "Alarm active • inspection pending" : "Readings within normal range"}</p>}{info.incident ? <IncidentLink id={info.incident} /> : <Link className="status status-link" href="/overview">View facility overview →</Link>}</Panel>
  </div>;
}
