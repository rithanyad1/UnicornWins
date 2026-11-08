"use client";

import Link from "next/link";
import mapLayout from "@/lib/facility-map-layout.json";
import { useFacilities, useLive } from "@/lib/live-data";
import { assignSlots, humanize } from "@/lib/utils";
import type { Facility, Incident } from "@/types";

const SLOTS = Object.keys(mapLayout);

export function zoneSummary(facility: Facility, active: Incident[]): { text: string; severity: "" | "warning" | "critical" } {
  const worst = active.find(incident => incident.severity === "CRITICAL") ?? active[0];
  if (facility.status === "DISCONNECTED") return { text: facility.latest_reading ? "Sensor disconnected" : "No recent readings", severity: active.length ? "warning" : "" };
  if (worst) return { text: `${humanize(worst.incident_type)} • ${humanize(worst.status).toLowerCase()}`, severity: worst.severity === "CRITICAL" ? "critical" : "warning" };
  return { text: "All systems normal", severity: "" };
}

export default function ZoneGrid() {
  const { incidents, connection } = useLive();
  const facilities = useFacilities();
  const slots = assignSlots(facilities.map(item => item.id), SLOTS);
  if (!facilities.length) return <div className="empty-state"><p>{connection === "live" || connection === "loading" ? "Loading monitored zones…" : "No zone data — the backend is unavailable."}</p></div>;
  return <div className="room-grid">{facilities.map(facility => {
    const active = Object.values(incidents).filter(item => item.facility_id === facility.id && (item.status === "OPEN" || item.status === "RESPONDING"));
    const { text, severity } = zoneSummary(facility, active);
    const slot = slots[facility.id] ?? "";
    return <Link href={`/facility?facility=${encodeURIComponent(facility.id)}`} className={`room-card ${severity ? `room-alert room-alert-${severity}` : ""}`} key={facility.id}>
      <div className="room-card-top"><span className={`room-id room-${slot}`}>{slot || "•"}</span>{severity && <span className="room-alert-badge">{severity === "critical" ? "Critical" : "Warning"}</span>}</div>
      <h3>{facility.name}</h3>
      <p className={severity ? "room-alert-message" : undefined}>{severity && <span className="room-alert-symbol" aria-hidden="true">!</span>}{text}</p>
      <p className="small">{facility.city}{facility.is_simulated ? " · Simulated" : ""}</p>
    </Link>;
  })}</div>;
}
