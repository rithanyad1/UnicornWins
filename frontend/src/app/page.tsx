import Link from "next/link";
import Icon from "@/components/dashboard/dashboard-icon";
import FacilityEntrance from "@/components/dashboard/facility-entrance";
import RoomGrid from "@/components/dashboard/room-grid";

export default function DataCenter() {
  return <main id="main" className="entrance" data-node-id="44:3">
    <FacilityEntrance />
    <section className="facility-glance">
      <div className="dashboard-section-heading"><h2>Your rooms & zones</h2><Link href="/overview">View dashboard <Icon name="arrow"/></Link></div>
      <RoomGrid />
    </section>
  </main>;
}
