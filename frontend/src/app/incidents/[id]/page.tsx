import IncidentDetails from "@/components/incidents/incident-details";

export default async function IncidentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <IncidentDetails id={id} />;
}
