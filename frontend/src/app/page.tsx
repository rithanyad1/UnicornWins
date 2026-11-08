import Link from "next/link";
import Icon from "@/components/dashboard/dashboard-icon";
import FacilityEntrance from "@/components/dashboard/facility-entrance";

const rooms = [
  ["A", "Desk & workstation", "Critical heat • responding", "critical"],
  ["B", "Window side", "All systems normal", ""],
  ["C", "Electronics shelf", "All systems normal", ""],
  ["D", "Mini-fridge nook", "Water warning • inspect", "warning"],
];

export default function DataCenter() {
  return <main id="main" className="entrance" data-node-id="44:3">
    <FacilityEntrance />
    <section className="facility-glance">
      <div className="dashboard-section-heading"><h2>Corners of the room</h2><Link href="/overview">View dashboard <Icon name="arrow"/></Link></div>
      <div className="room-grid">{rooms.map(([id, name, status, severity]) => <Link href={`/facility?room=${id}`} className={`room-card ${severity ? `room-alert room-alert-${severity}` : ""}`} key={id}><div className="room-card-top"><span className={`room-id room-${id}`}>{id}</span>{severity && <span className="room-alert-badge">{severity === "critical" ? "Critical" : "Warning"}</span>}</div><h3>{name}</h3><p className={severity ? "room-alert-message" : undefined}>{severity && <span className="room-alert-symbol" aria-hidden="true">!</span>}{status}</p></Link>)}</div>
    </section>
  </main>;
}
