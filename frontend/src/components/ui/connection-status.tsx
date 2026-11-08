"use client";

import { Status } from "@/components/ui/primitives";
import { useLive, type Connection } from "@/lib/live-data";
import { formatTime } from "@/lib/utils";

const DOT_COLORS: Record<Connection, string> = {
  live: "#5baf94", loading: "#b7a9cc", reconnecting: "#d59438", offline: "#d04768", unconfigured: "#d04768",
};

export function ConnectionDot({ connection }: { connection: Connection }) {
  return <span className="online-dot" style={{ background: DOT_COLORS[connection] }} aria-hidden="true" />;
}

export function connectionLabel(connection: Connection): string {
  switch (connection) {
    case "live": return "Live monitoring";
    case "loading": return "Connecting…";
    case "reconnecting": return "Reconnecting…";
    case "offline": return "Backend offline";
    case "unconfigured": return "Not configured";
  }
}

/** Page-level notice whenever data is not live; renders nothing while connected. */
export function ConnectionBanner() {
  const { connection, error, snapshotAt } = useLive();
  if (connection === "live") return null;
  const lastSync = snapshotAt ? ` Showing last known data from ${formatTime(snapshotAt)}.` : "";
  const message = connection === "loading" ? "Connecting to the UN1C0RN^2 backend…"
    : connection === "unconfigured" ? `Frontend is not configured: ${error ?? "set SENTINEL_PUBLIC_API_URL"}`
    : connection === "offline" ? `Backend unavailable: ${error ?? "no response"}.${lastSync || " No data has been received."}`
    : `Live updates disconnected — reconnecting.${lastSync}`;
  return <div role="status" aria-live="polite"><Status muted={connection === "loading"}><ConnectionDot connection={connection} /> {message}</Status></div>;
}
