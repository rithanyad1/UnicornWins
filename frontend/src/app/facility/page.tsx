import FacilityDiagram from "@/components/digital-twin/facility-diagram";

export default async function Facility({ searchParams }: { searchParams: Promise<{ room?: string }> }) {
  const { room } = await searchParams;
  return <main id="main" className="page facility-monitoring-page" data-node-id="44:327">
    <FacilityDiagram key={room} initialRoom={room} monitoring />
    <div className="facility-map-caption"><p>Select a room to inspect its readings and response.</p><span>○ Normal　! Attention　— Unknown</span></div>
  </main>;
}
