import Icon from "@/components/dashboard/dashboard-icon";
import { Panel } from "@/components/ui/primitives";
import IncidentList from "@/components/incidents/incident-list";

const stats = [["Open", "2", "Awaiting response"], ["Responding", "1", "Response underway"], ["Resolved", "12", "Sensor recovery verified"], ["Unresolved", "1", "Operator review"]];
export default function Incidents() {
  return <main id="main" className="page" data-node-id="46:442"><div className="page-heading"><h1>Incident history<span className="heading-dot">.</span></h1></div><div className="grid grid-four incident-stats">{stats.map(([title, value, note]) => <Panel key={title} className={`incident-stat stat-${title.toLowerCase()}`}><div className="stat-heading"><span className="sensor-icon"><Icon name={title === "Resolved" ? "check" : title === "Responding" ? "cooling" : title === "Open" ? "vibration" : "clock"}/></span><h2>{title}</h2></div><p className="metric-value">{value}</p><p className="small">{note}</p></Panel>)}</div><IncidentList /></main>;
}
