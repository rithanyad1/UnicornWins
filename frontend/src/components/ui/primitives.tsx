import Link from "next/link";

export function Panel({ id, title, children, className = "" }: { id?: string; title?: string; children: React.ReactNode; className?: string }) {
  return <section id={id} className={`panel ${className}`}>{title && <h2>{title}</h2>}{children}</section>;
}
export function Heading({ title, subtitle, eyebrow }: { title: string; subtitle: React.ReactNode; eyebrow?: string }) {
  return <div className="page-heading">{eyebrow && <span className="dashboard-eyebrow">{eyebrow}</span>}<h1>{title}<span className="heading-dot">.</span></h1><div className="subtitle">{subtitle}</div></div>;
}
export function Status({ children, muted = false }: { children: React.ReactNode; muted?: boolean }) {
  return <div className={`status ${muted ? "status-muted" : ""}`}>{children}</div>;
}
export function IncidentLink({ id, children }: { id: string; children?: React.ReactNode }) {
  return <Link className="status status-link" href={`/incidents/${id}`}>{children ?? `View incident #${id} →`}</Link>;
}
