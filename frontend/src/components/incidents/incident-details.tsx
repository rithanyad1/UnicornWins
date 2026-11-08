"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Heading, Panel, Status } from "@/components/ui/primitives";
import { TrendChart } from "@/components/charts/environmental-charts";
import { useLiveData } from "@/hooks/use-live-data";
import { api } from "@/lib/api";
import { cToF, formatDateTime, formatTime, incidentLabel, shortId, titleCase } from "@/lib/utils";
import type { Incident } from "@/types";

export default function IncidentDetails({ id }: { id: string }) {
  const live = useLiveData();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Reload whenever the live incident list changes, so status and verification stay current.
  const listed = live.incidents.find(item => item.id === id);
  const listedVersion = listed ? `${listed.status}:${listed.verification_data.length}` : "";
  useEffect(() => {
    let cancelled = false;
    api.incident(id).then(found => { if (!cancelled) { setIncident(found); setError(null); } })
      .catch(() => { if (!cancelled) setError("This incident was not found, or the backend is offline."); });
    return () => { cancelled = true; };
  }, [id, listedVersion]);

  if (!incident) return <main id="main" className="page"><Heading title={`Incident #${shortId(id)}`} subtitle={<Link href="/incidents">← Incident history</Link>} /><Status muted>{error ?? "Loading…"}</Status></main>;

  const detected = incident.detected_readings;
  const decision = incident.decisions?.find(item => item.decision_source !== "RULES") ?? incident.ai_analysis;
  const rule = incident.decisions?.find(item => item.decision_source === "RULES");
  const points = incident.verification_data.filter(item => typeof item.temperature_c === "number");
  const latest = points.at(-1);
  const resolved = incident.status === "RESOLVED";
  return <main id="main" className="page" data-node-id="46:497"><Heading title={`Incident #${shortId(incident.id)}`} subtitle={<><Link href="/incidents">← Incident history</Link> / {incidentLabel(incident)} / {titleCase(incident.status)}</>} />
    <Status>{incident.description}</Status>
    <div className="grid grid-two">
      <Panel title="Detection & decision">
        <p>Detected {formatDateTime(incident.detected_at)} / {detected.device_id ?? "unknown device"}</p>
        {typeof detected.temperature_c === "number" && <p>At detection: {cToF(detected.temperature_c).toFixed(1)} °F ({detected.temperature_c.toFixed(1)} °C) / {detected.humidity_percent} % / vibration {(detected.vibration_g ?? detected.vibration_score)?.toFixed(3)} g</p>}
        {detected.node_status && <p>Node status: {detected.node_status}{detected.alert_reasons?.length ? ` / ${detected.alert_reasons.join(", ")}` : ""}</p>}
        <p>Severity: {titleCase(incident.severity)}</p>
        {rule && <p>Rule: {rule.reasoning}</p>}
        {decision && decision.decision_source !== "RULES" && <p>{decision.model_name}: {decision.reasoning}</p>}
        {decision?.recommended_action && <p>Rule recommends: {decision.recommended_action} (the node runs its own fan)</p>}
      </Panel>
      <Panel title="Physical response">
        {detected.fan !== undefined && <p>Fan at detection: {detected.fan ? `on / ${detected.fan_speed_percent ?? 0}%` : "off"} (set by the SENTINEL node)</p>}
        {(incident.hardware_commands ?? []).map(command => <p key={command.id}>{shortId(command.id)} / {command.command_type} / {command.status.toLowerCase()} {command.acknowledged_at ? `at ${formatTime(command.acknowledged_at)}` : ""}</p>)}
        {latest && <p>Latest temperature: {cToF(latest.temperature_c!).toFixed(1)} °F at {formatTime(latest.recorded_at)}</p>}
        <p>Resolution: {resolved ? formatDateTime(incident.resolved_at) : "verification pending"}</p>
      </Panel>
    </div>
    {points.length > 1 && <TrendChart title="Temperature since detection" series={{ label: "Temperature", unit: "°F", color: "#8973d7", values: points.map(item => cToF(item.temperature_c!)), times: points.map(item => item.recorded_at ?? "") }} />}
    <Status muted>Resolved requires valid readings confirming recovery. Failed response or unconfirmed recovery stays unresolved.</Status></main>;
}
