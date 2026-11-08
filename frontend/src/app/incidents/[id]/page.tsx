import Link from "next/link";
import { notFound } from "next/navigation";
import { incidents } from "@/lib/demo-data";
import { Heading, Panel, Status } from "@/components/ui/primitives";
import { TrendChart } from "@/components/charts/environmental-charts";

export default async function IncidentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const incident = incidents.find(i => i.id === id);
  if (!incident) notFound();
  const thermal = id === "1042";
  return <main id="main" className="page" data-node-id="46:497"><Heading title={`Incident #${id}`} subtitle={<><Link href="/incidents">← Incident history</Link> / {incident.type} / {incident.status}</>} /><Status>{thermal ? "Cooling is active. Recovery verification is still in progress." : incident.description}</Status><div className="grid grid-two"><Panel title="Detection & decision"><p>Detected {incident.time} / {id === "1040" ? "Pico 2 W" : "ESP32"}</p>{thermal ? <><p>At detection: 100.8 °F / 45 % / vibration 0.08</p><p>Water: dry / all readings validated</p><p>Rule triggered: temperature &gt;95 °F</p><p>Model score −0.18 / anomaly detected</p><p>Suspected: rapid temperature rise</p><p>Recommended: fan ON + vent open</p></> : <><p>Severity: {incident.severity}</p><p>{incident.description}</p><p>Source: illustrative incident record</p></>}</Panel><Panel title="Physical response">{thermal ? <><p>cmd-208 / Fan ON / acknowledged 14:32:03</p><p>Reported fan state: ACTIVE</p><p>cmd-209 / Vent 90° / acknowledged</p><p>Reported vent state: OPEN</p><p>Current temperature: 93.4 °F / falling</p><p>Resolution time: — / verification pending</p></> : <><p>Status: {incident.status}</p><p>{incident.status === "Resolved" ? "Subsequent valid readings confirmed recovery." : "Operator review / verification pending"}</p>{id === "1041" && <p>Simulated shutdown only. Power has not been disconnected.</p>}{id === "1040" && <p>Actuator states UNKNOWN / last heartbeat 18s ago</p>}</>}</Panel></div>{thermal && <TrendChart title="Temperature / detection → response → recovery" asset="recovery" wide />}<Status muted>Resolved requires valid readings confirming recovery. Failed response or unconfirmed recovery stays unresolved.</Status></main>;
}
