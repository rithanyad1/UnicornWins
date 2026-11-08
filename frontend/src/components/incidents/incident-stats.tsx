"use client";

import Icon from "@/components/dashboard/dashboard-icon";
import { Panel } from "@/components/ui/primitives";
import { useLiveData } from "@/hooks/use-live-data";

const cards = [
  ["Open", "OPEN", "Awaiting response", "vibration"],
  ["Responding", "RESPONDING", "Response underway", "cooling"],
  ["Resolved", "RESOLVED", "Sensor recovery verified", "check"],
  ["Unresolved", "UNRESOLVED", "Operator review", "clock"],
] as const;

export default function IncidentStats() {
  const { incidents, backendReachable } = useLiveData();
  return <div className="grid grid-four incident-stats">{cards.map(([title, status, note, icon]) => <Panel key={title} className={`incident-stat stat-${title.toLowerCase()}`}><div className="stat-heading"><span className="sensor-icon"><Icon name={icon}/></span><h2>{title}</h2></div><p className="metric-value">{backendReachable ? incidents.filter(item => item.status === status).length : "—"}</p><p className="small">{note}</p></Panel>)}</div>;
}
