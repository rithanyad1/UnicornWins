import type { Incident, Reading } from "@/types";

export const cToF = (celsius: number) => celsius * 9 / 5 + 32;

export function readingF(reading: Pick<Reading, "temperature_c" | "temperature_f">): number {
  return reading.temperature_f ?? cToF(reading.temperature_c);
}

export function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function secondsAgo(value: string | null | undefined): number | null {
  if (!value) return null;
  return Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
}

const incidentLabels: Record<string, string> = {
  CRITICAL_TEMPERATURE: "Critical temperature",
  HIGH_TEMPERATURE: "High temperature",
  HIGH_HUMIDITY: "High humidity",
  WATER_DETECTED: "Water detected",
  ABNORMAL_VIBRATION: "Abnormal vibration",
  DEVICE_DISCONNECTED: "Device disconnected",
};

export function incidentLabel(incident: Pick<Incident, "incident_type">): string {
  return incidentLabels[incident.incident_type] ?? incident.incident_type.replaceAll("_", " ").toLowerCase();
}

export function titleCase(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

// Maps values to SVG polyline points within a width × height box.
export function sparkline(values: number[], width = 120, height = 40, pad = 6): string {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  return values.map((value, index) => `${(index * step).toFixed(1)},${(height - pad - (value - min) / span * (height - pad * 2)).toFixed(1)}`).join(" ");
}
