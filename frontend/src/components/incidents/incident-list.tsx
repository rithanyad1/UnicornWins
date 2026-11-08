"use client";

import Link from "next/link";
import { useState } from "react";
import { useLiveData } from "@/hooks/use-live-data";
import { Panel } from "@/components/ui/primitives";
import { formatDateTime, incidentLabel, shortId, titleCase } from "@/lib/utils";

export default function IncidentList() {
  const { incidents, loaded, backendReachable } = useLiveData();
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("All");
  const [status, setStatus] = useState("All");
  const filtered = incidents.filter(i => `${i.id} ${incidentLabel(i)}`.toLowerCase().includes(search.toLowerCase()) && (severity === "All" || titleCase(i.severity) === severity) && (status === "All" || titleCase(i.status) === status));
  const filtering = search !== "" || severity !== "All" || status !== "All";
  return <><form className="incident-filters" onSubmit={e => e.preventDefault()}><input aria-label="Search incidents" placeholder="Search incident ID or type…" value={search} onChange={e => setSearch(e.target.value)} /><label>Severity: <select value={severity} onChange={e => setSeverity(e.target.value)}>{["All", "Warning", "Critical"].map(s => <option key={s}>{s}</option>)}</select></label><label>Status: <select value={status} onChange={e => setStatus(e.target.value)}>{["All", "Open", "Responding", "Resolved", "Unresolved"].map(s => <option key={s}>{s}</option>)}</select></label><span className="small">{backendReachable ? `${incidents.length} incidents` : loaded ? "Backend offline" : "Loading…"}</span></form><Panel title="Recent incidents"><div className="incident-list">{filtered.map(i => <Link className="incident-row" href={`/incidents/${i.id}`} key={i.id}><strong>#{shortId(i.id)} / {incidentLabel(i)}</strong><span className={`severity-badge severity-${i.severity.toLowerCase()}`}>{titleCase(i.severity)}</span><time>{formatDateTime(i.detected_at)}</time><span className={`incident-state incident-state-${i.status.toLowerCase()}`}>{titleCase(i.status)} <span aria-hidden="true">→</span></span></Link>)}</div>{filtered.length === 0 && <div className="empty-state"><p>{filtering ? "No matching incidents" : "No incidents yet"}</p>{filtering && <button className="button" onClick={() => { setSearch(""); setSeverity("All"); setStatus("All"); }}>Clear filters</button>}</div>}</Panel></>;
}
