import Link from "next/link";
import Icon from "@/components/dashboard/dashboard-icon";
import UnicornMeadow from "@/components/dashboard/unicorn-meadow";

export default function FacilityEntrance() {
  return <section className="meadow-hero" aria-labelledby="hero-title">
    <div className="hero-content"><h1 id="hero-title">Your Data Center</h1>
      <Link href="/facility" prefetch className="button button-primary hero-cta">Explore the facility<Icon name="arrow"/></Link>
    </div>
    <div className="meadow-journey">
      <UnicornMeadow />
      <div className="distant-data-center"><img src="/models/facility-exterior.png" width="600" height="420" alt="The facility campus on the horizon, with its roofs and exterior walls intact"/></div>
    </div>
  </section>;
}
