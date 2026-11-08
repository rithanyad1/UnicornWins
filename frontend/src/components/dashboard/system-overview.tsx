<<<<<<< HEAD
import type { HardwareReport } from "@/hooks/use-live-data";
=======
"use client";

>>>>>>> 245739c (Last Changes)
import Icon from "./dashboard-icon";
import { useLiveMetric } from "@/lib/use-live-metric";

<<<<<<< HEAD
export default function SystemOverview({ report }: { report: HardwareReport | null }) {
  const metrics = [
    { id: "temperature", label: "Temperature", value: report?.temperature_f?.toFixed(1), unit: "°F" },
    { id: "humidity", label: "Humidity", value: report?.humidity_percent?.toFixed(0), unit: "%" },
    { id: "vibration", label: "Vibration", value: report?.vibration_g?.toFixed(3), unit: "g" },
    { id: "cooling", label: "Cooling system", value: report ? (report.fan_active ? "Active" : "Off") : null, unit: "" },
  ];
  return <div className="dashboard-metrics">{metrics.map(metric => <section key={metric.id} className={`sensor-card sensor-${metric.id}`} aria-label={metric.label}>
    <div className="sensor-top"><span className="sensor-icon"><Icon name={metric.id}/></span><span className="sensor-badge">{!report ? "Disconnected" : metric.value == null ? "Unavailable" : "Live"}</span></div>
    <h3>{metric.label}</h3><div className="sensor-reading">{metric.value ?? "null"}{metric.value != null && <span>{metric.unit}</span>}</div>
    <p>{!report ? "Waiting for hardware connection" : metric.value == null ? "Sensor reading unavailable" : metric.id === "cooling" ? `Fan speed: ${report.fan_speed_percent}%` : "Latest hardware reading"}</p>
  </section>)}</div>;
=======
const metrics = [
  { id: "temperature", label: "Temperature", base: 74.4, amplitude: 0.3, decimals: 1, unit: "°F", note: "Above 74 °F warning · fan at 60%", badge: "Elevated", points: "0,30 12,29 24,30 36,23 48,26 60,14 72,9 84,13 96,18 108,22 120,25" },
  { id: "humidity", label: "Humidity", base: 21, amplitude: 0.6, decimals: 1, unit: "%", note: "Within normal range", badge: "Normal", points: "0,25 12,22 24,26 36,20 48,23 60,17 72,20 84,14 96,17 108,13 120,16" },
  { id: "vibration", label: "Vibration", base: 0.028, amplitude: 0.003, decimals: 3, unit: "G", note: "Within calibrated baseline", badge: "Stable", points: "0,22 12,22 24,18 36,27 48,20 60,21 72,15 84,25 96,21 108,23 120,21" },
  { id: "cooling", label: "Cooling system", base: 60, amplitude: 2, decimals: 0, unit: "%", note: "Stepped down from 100% at the red threshold", badge: "Responding", points: "0,30 12,30 24,30 36,30 48,12 60,12 72,12 84,12 96,12 108,12 120,12" },
];

function MetricCard({ metric }: { metric: (typeof metrics)[number] }) {
  const value = useLiveMetric(metric.base, metric.amplitude);
  return <section className={`sensor-card sensor-${metric.id}`} aria-label={metric.label}><div className="sensor-top"><span className="sensor-icon"><Icon name={metric.id}/></span><span className="sensor-badge">{metric.badge}</span></div><h3>{metric.label}</h3><div className="sensor-reading">{value.toFixed(metric.decimals)}<span>{metric.unit}</span><svg viewBox="0 0 120 40" fill="none" aria-hidden="true"><polyline points={metric.points} stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg></div><p>{metric.note}</p></section>;
}

export default function SystemOverview() {
  return <div className="dashboard-metrics">{metrics.map(metric => <MetricCard key={metric.id} metric={metric} />)}</div>;
>>>>>>> 245739c (Last Changes)
}
