import SystemOverview from "@/components/dashboard/system-overview";
import EnvironmentalCharts from "@/components/charts/environmental-charts";
import AiAnalysis from "@/components/dashboard/ai-analysis";
import ActivityFeed from "@/components/dashboard/activity-feed";
import Icon from "@/components/dashboard/dashboard-icon";

export default function Overview() {
  return <main id="main" className="page dashboard-page" data-node-id="46:6">
    <h1 className="sr-only">Facility dashboard</h1>
    <SystemOverview />
    <div className="dashboard-main-grid"><EnvironmentalCharts /><AiAnalysis /></div>
    <ActivityFeed />
    <footer className="dashboard-footer"><span><Icon name="shield"/> SENTINEL <span> / </span> A little magic. Complete visibility.</span><span>Live data from the SENTINEL node</span></footer>
  </main>;
}
