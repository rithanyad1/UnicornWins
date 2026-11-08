"use client";

import Link from "next/link";
import Icon from "./dashboard-icon";
import { nodeDevice, useLiveData } from "@/hooks/use-live-data";
import { formatTime, incidentLabel, secondsAgo } from "@/lib/utils";
import type { LiveEvent } from "@/types";

function describe(event: LiveEvent): [string, string, string] {
  const data = event.data as Record<string, string>;
  switch (event.type) {
    case "incident.created": return ["Rule", `${incidentLabel({ incident_type: data.incident_type })} detected`, "temperature"];
    case "incident.recovered": return ["Sensor", `${incidentLabel({ incident_type: data.incident_type })} recovered`, "check"];
    case "ai.decision": return [data.decision_source === "RULES" ? "Rule" : "AI", data.reasoning || "Decision recorded", "sparkle"];
    case "ai.anomaly": return ["AI", "Anomaly model flagged a reading", "sparkle"];
    case "device.connection": return ["Hardware", `${data.device_id} ${data.status === "CONNECTED" ? "connected" : "disconnected"}`, data.status === "CONNECTED" ? "check" : "vibration"];
    case "facility.status": return ["Sensor", `Facility status ${data.previous_status} → ${data.status}`, "vibration"];
    case "sensor.fault": return ["Hardware", data.description || "Sensor fault", "vibration"];
    case "command.status": return ["Command", `${data.command_type} ${String(data.status).toLowerCase()}`, "cooling"];
    default: return ["System", event.type, "vibration"];
  }
}

export default function ActivityFeed() {
  const data = useLiveData();
  const node = nodeDevice(data);
  const events = data.events.slice(0, 8);
  const lastSeen = secondsAgo(node?.last_seen);
  return <section className="dashboard-activity"><div className="dashboard-section-heading"><h2>Recent activity</h2><Link href="/incidents">View incidents <Icon name="arrow"/></Link></div><div className="activity-table"><div className="activity-table-head"><span>EVENT</span><span>TIME</span><span>SOURCE</span></div>
    {events.length === 0 && <div className="dashboard-activity-row"><div><span className="activity-icon activity-icon-check"><Icon name="check"/></span><p>{data.backendReachable ? "No activity yet" : "Backend offline"}</p></div><time>—</time><span className="activity-source source-system">System</span></div>}
    {events.map((event, index) => { const [source, description, icon] = describe(event); return <div className="dashboard-activity-row" key={`${event.timestamp}-${index}`}><div><span className={`activity-icon activity-icon-${icon}`}><Icon name={icon}/></span><p>{description}</p></div><time>{formatTime(event.timestamp)}</time><span className={`activity-source source-${source.toLowerCase()}`}>{source}</span></div>; })}
  </div><div className="activity-footer"><span className="online-dot"/> {node?.status === "CONNECTED" ? `${node.device_id} reporting` : "SENTINEL node offline"} <span>·</span> {lastSeen === null ? "never seen" : `last report ${lastSeen}s ago`}</div></section>;
}
