import type { Decision, Facility, Incident, LiveEvent, Reading, SystemStatus } from "@/types";

// The facility the physical SENTINEL node reports into.
export const FACILITY_ID = process.env.NEXT_PUBLIC_FACILITY_ID || "facility-main";

// Defaults to port 8000 on whatever host served the dashboard, so it also works
// from another device on the same network.
export function apiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase()}/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  facility: (id = FACILITY_ID) => get<Facility>(`/facilities/${id}`),
  history: (id = FACILITY_ID, limit = 300) => get<{ readings: Reading[] }>(`/facilities/${id}/history?limit=${limit}`).then(r => r.readings),
  incidents: () => get<{ incidents: Incident[] }>("/incidents").then(r => r.incidents),
  incident: (id: string) => get<Incident>(`/incidents/${encodeURIComponent(id)}`),
  decisions: () => get<{ decisions: Decision[] }>("/decisions").then(r => r.decisions),
  status: () => get<SystemStatus>("/system/status"),
  events: (limit = 30) => get<{ events: LiveEvent[] }>(`/events?limit=${limit}`).then(r => r.events),
};
