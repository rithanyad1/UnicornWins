import IncidentList from "@/components/incidents/incident-list";
import IncidentStats from "@/components/incidents/incident-stats";

export default function Incidents() {
  return <main id="main" className="page" data-node-id="46:442"><div className="page-heading"><h1>Incident history<span className="heading-dot">.</span></h1></div><IncidentStats /><IncidentList /></main>;
}
