import type { HardwareReport } from "@/hooks/use-live-data";
import Icon from "./dashboard-icon";

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
}
