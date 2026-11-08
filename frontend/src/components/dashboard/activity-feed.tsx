import type { HardwareReport } from "@/hooks/use-live-data";
import Icon from "./dashboard-icon";

export default function ActivityFeed({ reports }: { reports: HardwareReport[] }) {
  return <section className="dashboard-activity">
    <div className="dashboard-section-heading"><h2>Recent activity</h2></div>
    <div className="activity-table"><div className="activity-table-head"><span>EVENT</span><span>TIME</span><span>SOURCE</span></div>
      {reports.length ? reports.slice(-4).reverse().map(report => <div className="dashboard-activity-row" key={report.id}><div><span className="activity-icon"><Icon name="vibration"/></span><p>{report.status} · Fan {report.fan_speed_percent}%</p></div><time dateTime={report.recorded_at}>{new Date(report.recorded_at).toLocaleTimeString([], { hour12: false })}</time><span className="activity-source">Hardware</span></div>) : <div className="dashboard-activity-row"><div><p>No live hardware activity</p></div><span>null</span><span className="activity-source">Disconnected</span></div>}
    </div><div className="activity-footer">{reports.length ? "Live Pico reports" : "Waiting for hardware connection"}</div>
  </section>;
}
