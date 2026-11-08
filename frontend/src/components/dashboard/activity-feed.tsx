import Link from "next/link";
import Icon from "./dashboard-icon";

const activity = [
  ["14:32:02", "Rule", "High-temperature threshold crossed", "temperature"],
  ["14:32:03", "Command", "Cooling command sent / cmd-208", "cooling"],
  ["14:32:03", "Hardware", "Fan active · vent open · Pico confirmed", "check"],
  ["14:32:15", "Sensor", "Temperature decreasing · verification pending", "vibration"],
];
export default function ActivityFeed() {
  return <section className="dashboard-activity"><div className="dashboard-section-heading"><h2>Recent activity</h2><Link href="/incidents">View incidents <Icon name="arrow"/></Link></div><div className="activity-table"><div className="activity-table-head"><span>EVENT</span><span>TIME</span><span>SOURCE</span></div>{activity.map(([time, type, description, icon], index) => <div className="dashboard-activity-row" key={index}><div><span className={`activity-icon activity-icon-${icon}`}><Icon name={icon}/></span><p>{description}</p></div><time>{time}</time><span className={`activity-source source-${type.toLowerCase()}`}>{type}</span></div>)}</div><div className="activity-footer"><span className="online-dot"/> Water sensor dry <span>·</span> Valid reading</div></section>;
}
