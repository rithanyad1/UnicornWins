"use client";

import Link from "next/link";
import { useState } from "react";
import { Panel, IncidentLink, Status } from "@/components/ui/primitives";
import CampusViewer from "@/components/digital-twin/campus-viewer";
import { useLiveMetric } from "@/lib/use-live-metric";

const roomNames: Record<string, string> = {
  A: "Desk & workstation", B: "Window side", C: "Electronics shelf", D: "Mini-fridge nook",
};

function MapSidebar({ room, selectRoom }: { room: string; selectRoom: (id: string) => void }) {
  const temperature = useLiveMetric(74.4, 0.3);
  const humidity = useLiveMetric(21, 0.6);
  const vibration = useLiveMetric(0.028, 0.003);
  return <aside id="facility-metrics" className="monitoring-sidebar" aria-label="Room metrics and corners">
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Room overview</h2><span className="sidebar-code">RM-214</span></div>
      <div className="sidebar-counts"><div><strong>4</strong><span>Corners</span></div><div><strong>2</strong><span>Incidents</span></div><div><strong>2</strong><span>Normal</span></div></div>
      <div className="health-distribution" aria-label="Two normal corners and two corners needing attention"><span /><span /></div>
      <div className="distribution-labels"><span>● Normal</span><span>● Attention</span></div>
    </section>
    <section className="sidebar-section">
      <div className="sidebar-section-heading"><h2>Thermal activity</h2><span className="sidebar-code">15 MIN</span></div>
<<<<<<< HEAD
      <div className="sidebar-temperature"><strong>93.4<span> °F</span></strong><span>↘ Falling</span></div>
=======
      <div className="sidebar-temperature"><strong>{temperature.toFixed(1)}<span> °F</span></strong><span>↘ Falling</span></div>
>>>>>>> 245739c (Last Changes)
      <img className="sidebar-sparkline" src="/figma/temperature.svg" width="842" height="160" alt="Illustrative temperature trend rising then falling after cooling" />
      <div className="distribution-labels"><span>14:20</span><span>14:32</span></div>
    </section>
    <section className="sidebar-section room-directory">
      <div className="sidebar-section-heading"><h2>Corners of the room</h2><span className="sidebar-code">04</span></div>
      {Object.entries(roomNames).map(([id, name]) => <button key={id} className={`directory-room ${room === id ? "active" : ""}`} onClick={() => selectRoom(id)} aria-pressed={room === id}>
        <span className={`directory-room-id room-${id}`}>{id}</span><span><strong>{name}</strong><small>{id === "A" ? "Cooling response" : id === "D" ? "Water detected" : "Systems normal"}</small></span><span className="directory-indicator" aria-label={id === "A" || id === "D" ? "Attention" : "Normal"}>{id === "A" || id === "D" ? "!" : "●"}</span>
      </button>)}
    </section>
    <section className="sidebar-section sidebar-environment"><h2>Environment</h2><dl><div><dt>Humidity</dt><dd>{humidity.toFixed(1)} %</dd></div><div><dt>Vibration</dt><dd>{vibration.toFixed(3)} G</dd></div><div><dt>Monitoring</dt><dd>Automatic</dd></div></dl></section>
  </aside>;
}

const roomInfo: Record<string, { title: string; location: string; value: string; unit: string; status: string; response: string; incident?: string }> = {
<<<<<<< HEAD
  A: { title: "Rack A-03", location: "Server hall A / sensor T-A03", value: "106.2°", unit: "TEMPERATURE / °F", status: "CRITICAL • RESPONDING", response: "The response is underway.", incident: "1042" },
  B: { title: "Server hall B", location: "Server hall B / sensor T-B01", value: "79.5°", unit: "TEMPERATURE / °F", status: "NORMAL", response: "All systems normal." },
  C: { title: "Network room", location: "Network room / sensor T-C01", value: "78.4°", unit: "TEMPERATURE / °F", status: "NORMAL", response: "All systems normal." },
  D: { title: "Cooling area", location: "Power & cooling / sensor W-D01", value: "Detected", unit: "WATER / MOISTURE", status: "CRITICAL • OPEN", response: "Water inspection required.", incident: "1041" },
=======
  A: { title: "Desk & Workstation", location: "Desk & workstation / sensor DHT22-01", value: "76.0°", unit: "TEMPERATURE / °F", status: "CRITICAL • RESPONDING", response: "The response is underway.", incident: "1042" },
  B: { title: "Window Side", location: "Window side / sensor DHT22-02", value: "73.0°", unit: "TEMPERATURE / °F", status: "NORMAL", response: "All systems normal." },
  C: { title: "Electronics Shelf", location: "Electronics shelf / sensor DHT22-03", value: "73.2°", unit: "TEMPERATURE / °F", status: "NORMAL", response: "All systems normal." },
  D: { title: "Mini-Fridge Nook", location: "Mini-fridge nook / sensor water-01", value: "Detected", unit: "WATER / MOISTURE", status: "CRITICAL • OPEN", response: "Moisture inspection required.", incident: "1041" },
>>>>>>> 245739c (Last Changes)
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
  const tempA = useLiveMetric(76, 0.3);
  const tempB = useLiveMetric(73, 0.2);
  const tempC = useLiveMetric(73.2, 0.2);
  const liveTemps: Record<string, number> = { A: tempA, B: tempB, C: tempC };
  const liveValue = room in liveTemps ? `${liveTemps[room].toFixed(1)}°` : info.value;
  return <div className={`facility-layout ${compact ? "compact-map" : ""} ${monitoring ? "monitoring-layout" : ""}`} data-panel={activePanel ?? "none"}>
    {monitoring && <div className="map-panel-toggles" aria-label="Map panels">
      <button aria-expanded={activePanel === "metrics"} aria-controls="facility-metrics" onClick={() => setActivePanel(activePanel === "metrics" ? null : "metrics")}>Room overview {activePanel === "metrics" ? "×" : "+"}</button>
      <button aria-expanded={activePanel === "inspector"} aria-controls="facility-inspector" onClick={() => setActivePanel(activePanel === "inspector" ? null : "inspector")}>Room {room} details {activePanel === "inspector" ? "×" : "+"}</button>
    </div>}
    {monitoring && <MapSidebar room={room} selectRoom={selectRoom} />}
    <div className={monitoring ? "map-workspace" : "map-standard-view"}>
    {monitoring && <div className="workspace-heading"><div className="workspace-view-links"><span className="active">Room map</span></div><span className="workspace-floor">Rm. 214</span></div>}
    <div className="facility-map" aria-label="Interactive room map">
      <CampusViewer focusRequest={focusRequest} room={room} selectRoom={selectRoom} emergencies={emergencyRooms} />
    </div>
    {monitoring && <div className="workspace-statusbar"><span><i className="map-status-dot" /> 4 monitored corners</span><span>2 active incidents</span><span>Illustrative snapshot</span></div>}
    </div>
<<<<<<< HEAD
    <Panel id={monitoring ? "facility-inspector" : undefined} className="inspector">{monitoring && <div className="inspector-eyebrow">SELECTED LOCATION <span>{room}</span></div>}<Status muted>{info.status}</Status><h2 className="inspector-title">{compact && room === "A" ? "Temperature sensor" : info.title}</h2><p>{info.location}</p><div className="inspector-reading"><p className="inspector-value">{compact && room === "A" ? "100.8 °F" : info.value}</p><p className="small unit">{info.unit}</p></div><h3>{info.response}</h3>{room === "A" ? <><p>Fan active • Pico confirmed<br />Vent open / 90° reported</p><p>Recovery verification pending</p></> : <p>{room === "D" ? "Alarm active • inspection pending" : "Readings within normal range"}</p>}{info.incident ? <IncidentLink id={info.incident} /> : <Link className="status status-link" href="/overview">View facility overview →</Link>}</Panel>
=======
    <Panel id={monitoring ? "facility-inspector" : undefined} className="inspector">{monitoring && <div className="inspector-eyebrow">SELECTED LOCATION <span>{room}</span></div>}<Status muted>{info.status}</Status><h2 className="inspector-title">{compact && room === "A" ? "Temperature sensor" : info.title}</h2><p>{info.location}</p><div className="inspector-reading"><p className="inspector-value">{compact && room === "A" ? `${tempA.toFixed(1)} °F` : liveValue}</p><p className="small unit">{info.unit}</p></div><h3>{info.response}</h3>{room === "A" ? <><p>Fan active • Pico confirmed<br />Speed stepped down to 60%</p><p>Recovery verification pending</p></> : <p>{room === "D" ? "Alarm active • inspection pending" : "Readings within normal range"}</p>}{info.incident ? <IncidentLink id={info.incident} /> : <Link className="status status-link" href="/overview">View room overview →</Link>}</Panel>
>>>>>>> 245739c (Last Changes)
  </div>;
}
