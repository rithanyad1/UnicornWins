"use client";

import Link from "next/link";
import Icon from "./dashboard-icon";
import { nodeDevice, useLiveData } from "@/hooks/use-live-data";
import { FACILITY_ID } from "@/lib/api";
import { incidentLabel, shortId } from "@/lib/utils";

export default function AiAnalysis() {
  const data = useLiveData();
  const node = nodeDevice(data);
  const latest = data.facility?.latest_reading;
  const active = data.incidents.filter(item => item.facility_id === FACILITY_ID && (item.status === "OPEN" || item.status === "RESPONDING"));
  const incident = active[0];
  const decision = incident ? data.decisions.find(item => item.incident_id === incident.id && item.decision_source !== "RULES") ?? incident.ai_analysis ?? null : null;
  const anomaly = data.decisions.find(item => item.decision_source === "ISOLATION_FOREST");
  const reasons = latest?.alert_reasons ?? node?.actuator_state.alert_reasons ?? [];
  const fanOn = latest?.fan ?? node?.actuator_state.fan;
  const connected = node?.status === "CONNECTED";

  const heading = !data.backendReachable ? "Backend offline." : !connected ? "Node offline." : incident ? `${incidentLabel(incident)}.` : "All clear.";
  const summary = !data.backendReachable ? "The dashboard cannot reach the SENTINEL backend. Check that it is running on port 8000."
    : !connected ? "No reports from the SENTINEL node. Check its USB cable and that the serial bridge is running."
    : incident ? (decision?.reasoning || incident.description) : "Every sensor is within its normal range.";

  return <section className="response-panel"><div className="response-heading"><span className="sensor-icon"><Icon name="sparkle"/></span><span>Sentinel intelligence</span><span className="response-dot"/></div>
    <div className="response-status">{incident ? (incident.status === "RESPONDING" ? "AUTOMATED RESPONSE" : "OPEN INCIDENT") : "MONITORING"}</div>
    <h2>{heading}</h2><p>{summary}</p>
    <div className="response-steps">
      {connected && <div><span className={fanOn ? "step-check" : "step-pending"}>{fanOn && <Icon name="check"/>}</span><span>{fanOn ? "Cooling active" : "Cooling idle"}<small>Fan controlled by the SENTINEL node</small></span></div>}
      {reasons.map(reason => <div key={reason}><span className="step-pending"/><span>{reason}<small>Reported by the node</small></span></div>)}
      {incident && <div><span className={incident.status === "RESOLVED" ? "step-check" : "step-pending"}/><span>Verifying recovery<small>Resolves after readings stay normal</small></span></div>}
    </div>
    <div className="model-score">{anomaly?.anomaly_score != null ? <span>Isolation Forest score <strong>{anomaly.anomaly_score.toFixed(2)}</strong></span> : <span>Anomaly model <strong>{data.status?.anomaly_model_status ?? "unknown"}</strong></span>}<small>Gemini {data.status?.gemini_status === "configured" ? "is analysing incidents" : "is not configured"}. Safety rules take priority.</small></div>
    {incident ? <Link href={`/incidents/${incident.id}`} className="response-link">View incident #{shortId(incident.id)} <Icon name="arrow"/></Link> : <Link href="/incidents" className="response-link">Incident history <Icon name="arrow"/></Link>}
  </section>;
}
