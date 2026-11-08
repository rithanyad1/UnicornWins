"use client";

import Link from "next/link";
import { useState } from "react";
import { incidents } from "@/lib/demo-data";
import { Panel } from "@/components/ui/primitives";

export default function IncidentList() {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("All");
  const [status, setStatus] = useState("All");
  const filtered = incidents.filter(i => `${i.id} ${i.type}`.toLowerCase().includes(search.toLowerCase()) && (severity === "All" || i.severity === severity) && (status === "All" || i.status === status));
  return <><form className="incident-filters" onSubmit={e => e.preventDefault()}><input aria-label="Search incidents" placeholder="Search incident ID or type…" value={search} onChange={e => setSearch(e.target.value)} /><label>Severity: <select value={severity} onChange={e => setSeverity(e.target.value)}>{["All", "Warning", "Critical"].map(s => <option key={s}>{s}</option>)}</select></label><label>Status: <select value={status} onChange={e => setStatus(e.target.value)}>{["All", "Open", "Responding", "Resolved", "Unresolved"].map(s => <option key={s}>{s}</option>)}</select></label><span className="small">Illustrative session</span></form><Panel title="Recent incidents"><div className="incident-list">{filtered.map(i => <Link className="incident-row" href={`/incidents/${i.id}`} key={i.id}><strong>#{i.id} / {i.type}</strong><span className={`severity-badge severity-${i.severity.toLowerCase()}`}>{i.severity}</span><time>{i.time}</time><span className={`incident-state incident-state-${i.status.toLowerCase()}`}>{i.status} <span aria-hidden="true">→</span></span></Link>)}</div>{filtered.length === 0 && <div className="empty-state"><p>No matching incidents</p><button className="button" onClick={() => { setSearch(""); setSeverity("All"); setStatus("All"); }}>Clear filters</button></div>}</Panel></>;
}
