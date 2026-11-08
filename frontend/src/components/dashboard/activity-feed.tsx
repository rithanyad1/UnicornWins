import Icon from "./dashboard-icon";

const activity = [
  { id: "a4", label: "Fan stepped down to 60% · temperature easing toward 74°F", time: "14:32" },
  { id: "a3", label: "Fan ramped to 100% · temperature crossed 76°F (critical)", time: "14:29" },
  { id: "a2", label: "Temperature crossed 74°F (warning) · fan preparing to respond", time: "14:26" },
  { id: "a1", label: "Baseline reading · 73°F, 21% humidity, 0.028G vibration", time: "14:20" },
];

export default function ActivityFeed() {
  return <section className="dashboard-activity">
    <div className="dashboard-section-heading"><h2>Recent activity</h2></div>
    <div className="activity-table"><div className="activity-table-head"><span>EVENT</span><span>TIME</span><span>SOURCE</span></div>
      {activity.map(item => <div className="dashboard-activity-row" key={item.id}><div><span className="activity-icon"><Icon name="vibration"/></span><p>{item.label}</p></div><time>{item.time}</time><span className="activity-source">Hardware</span></div>)}
    </div><div className="activity-footer">Illustrative hardware activity</div>
  </section>;
}
