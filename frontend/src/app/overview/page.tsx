"use client";

import { useLiveData } from "@/hooks/use-live-data";
import SystemOverview from "@/components/dashboard/system-overview";
import EnvironmentalCharts from "@/components/charts/environmental-charts";
import AiAnalysis from "@/components/dashboard/ai-analysis";
import ActivityFeed from "@/components/dashboard/activity-feed";
import Icon from "@/components/dashboard/dashboard-icon";

export default function Overview() {
  const { report, reports, connected } = useLiveData();
  return <main id="main" className="page dashboard-page" data-node-id="46:6">
    <h1 className="sr-only">Facility dashboard</h1>
    <SystemOverview report={report} />
    <div className="dashboard-main-grid"><EnvironmentalCharts report={report} reports={reports} /><AiAnalysis report={report} /></div>
    <ActivityFeed reports={reports} />
    <footer className="dashboard-footer"><span><Icon name="shield"/> UN1C0RN^2 <span> / </span> A little magic. Complete visibility.</span><span role="status">{connected ? "Hardware connected · Live readings" : "Hardware disconnected · Values are null"}</span></footer>
  </main>;
}
