"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";
import SystemOverview from "@/components/dashboard/system-overview";
import EnvironmentalCharts from "@/components/charts/environmental-charts";
import AiAnalysis from "@/components/dashboard/ai-analysis";
import ActivityFeed from "@/components/dashboard/activity-feed";
import Icon from "@/components/dashboard/dashboard-icon";
import { ConnectionBanner, connectionLabel } from "@/components/ui/connection-status";
import { useActiveIncidents, useFacilities, useFacilityHistory, useLive } from "@/lib/live-data";
import type { Facility } from "@/types";

/** Prefer a physical facility with data, then any facility with data, then the first. */
export function defaultFacility(facilities: Facility[]): Facility | undefined {
  return facilities.find(item => !item.is_simulated && item.latest_reading)
    ?? facilities.find(item => item.latest_reading)
    ?? facilities[0];
}

export default function DashboardView({ facilityId }: { facilityId?: string }) {
  const router = useRouter();
  const { status, decisions, commands, anomalies, connection } = useLive();
  const facilities = useFacilities();
  const facility = facilities.find(item => item.id === facilityId) ?? defaultFacility(facilities);
  const history = useFacilityHistory(facility?.id);
  const active = useActiveIncidents(facility?.id);
  const commandList = useMemo(() => Object.values(commands), [commands]);
  const thresholds = status?.thresholds ?? null;
  return <>
    <ConnectionBanner />
    {facilities.length > 0 && <form className="incident-filters" onSubmit={event => event.preventDefault()}>
      <label>Facility: <select value={facility?.id} onChange={event => router.replace(`/overview?facility=${encodeURIComponent(event.target.value)}`)}>
        {facilities.map(item => <option key={item.id} value={item.id}>{item.name}{item.is_simulated ? " (simulated)" : ""}</option>)}
      </select></label>
      <span className="small">{facility?.is_simulated ? "Simulated facility · synthetic readings" : facility ? `Physical facility · ${facility.city}` : ""}</span>
    </form>}
    <SystemOverview facility={facility} history={history} thresholds={thresholds} />
    <div className="dashboard-main-grid">
      <EnvironmentalCharts facility={facility} history={history} thresholds={thresholds} />
      <AiAnalysis facility={facility} incident={active[0]} decisions={decisions} commands={commandList} anomaly={facility ? anomalies[facility.id] : undefined} />
    </div>
    <ActivityFeed facility={facility} />
    <footer className="dashboard-footer"><span><Icon name="shield"/> UN1C0RN^2 <span> / </span> A little magic. Complete visibility.</span>
      <span>{connectionLabel(connection)} · {connection === "live" && status ? `Database ${status.spacetimedb_status.replace("_", " ")} · Gemini ${status.gemini_status.replace("_", " ")}` : "Service status unknown while disconnected"}</span></footer>
  </>;
}
