"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [["/", "Home"], ["/facility", "Map"], ["/overview", "Dashboard"], ["/incidents", "Incidents"]];

export default function TopNavigation() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return <header className={`navigation navigation-dashboard ${pathname === "/facility" ? "navigation-map" : ""}`}>
    <Link href="/" className="brand" aria-label="Sentinel home">SENTINEL</Link>
    <button className="menu-button" aria-expanded={open} aria-controls="primary-nav" onClick={() => setOpen(!open)}>Menu {open ? "×" : "☰"}</button>
    <nav id="primary-nav" aria-label="Main navigation" className={open ? "nav-links is-open" : "nav-links"}>
      {links.map(([href, label]) => <Link key={href} href={href} aria-current={(href === "/" ? pathname === "/" : pathname.startsWith(href)) ? "page" : undefined} onClick={() => setOpen(false)}>{label}</Link>)}
    </nav>
    <div className="nav-dashboard-status"><span className="online-dot"/> Demo workspace <span className="sentinel-avatar" aria-label="Sentinel workspace">S</span></div>
  </header>;
}
