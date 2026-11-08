"use client";

import Icon from "./dashboard-icon";
import { nodeDevice, useLiveData } from "@/hooks/use-live-data";
import { cToF, readingF, sparkline } from "@/lib/utils";

export default function SystemOverview() {
  const data = useLiveData();
  const latest = data.facility?.latest_reading ?? null;
  const recent = data.history.slice(-30);
  const limits = data.status?.thresholds;
  const node = nodeDevice(data);
  const fanOn = latest?.fan ?? node?.actuator_state.fan ?? false;
  const fanSpeed = latest?.fan_speed_percent ?? node?.actuator_state.fan_speed_percent ?? 0;
  const nodeConnected = node?.status === "CONNECTED";

  const temperatureF = latest ? readingF(latest) : null;
  const highF = limits ? cToF(limits.high_temp_c) : null;
  const tempBadge = temperatureF === null || highF === null ? "No data"
    : limits && latest!.temperature_c >= limits.critical_temp_c ? "Critical"
    : temperatureF >= highF ? "Elevated" : "Normal";
  const humidityHigh = latest && limits ? latest.humidity_percent >= limits.high_humidity_percent : false;
  const vibration = latest ? latest.vibration_g ?? latest.vibration_score : null;
  const vibrationHigh = vibration !== null && limits ? vibration >= limits.vibration : false;

  const metrics = [
    {
      id: "temperature", label: "Temperature", unit: "°F",
      value: temperatureF === null ? "—" : temperatureF.toFixed(1),
      note: latest && highF !== null ? `${latest.temperature_c.toFixed(1)} °C · warning at ${highF.toFixed(0)} °F` : "Waiting for the first reading",
      badge: tempBadge, points: sparkline(recent.map(readingF)),
    },
    {
      id: "humidity", label: "Humidity", unit: "%",
      value: latest ? latest.humidity_percent.toFixed(0) : "—",
      note: !latest ? "Waiting for the first reading" : humidityHigh ? `Above ${limits!.high_humidity_percent}% threshold` : "Within normal range",
      badge: !latest ? "No data" : humidityHigh ? "Elevated" : "Normal", points: sparkline(recent.map(r => r.humidity_percent)),
    },
    {
      id: "vibration", label: "Vibration", unit: "g",
      value: vibration === null ? "—" : vibration.toFixed(3),
      note: vibration === null ? "Waiting for the first reading" : vibrationHigh ? `Above ${limits!.vibration} g threshold` : "Within baseline",
      badge: vibration === null ? "No data" : vibrationHigh ? "Elevated" : "Stable", points: sparkline(recent.map(r => r.vibration_g ?? r.vibration_score)),
    },
    {
      id: "cooling", label: "Cooling fan", unit: "",
      value: !nodeConnected ? "Offline" : fanOn ? `${fanSpeed}%` : "Off",
      note: !nodeConnected ? "SENTINEL node is not reporting" : `Node status: ${latest?.node_status ?? node?.actuator_state.node_status ?? "unknown"}`,
      badge: !nodeConnected ? "Disconnected" : fanOn ? "Responding" : "Idle", points: sparkline(recent.map(r => r.fan_speed_percent ?? 0)),
    },
  ];
  return <div className="dashboard-metrics">{metrics.map(metric => <section key={metric.id} className={`sensor-card sensor-${metric.id}`} aria-label={metric.label}><div className="sensor-top"><span className="sensor-icon"><Icon name={metric.id}/></span><span className="sensor-badge">{metric.badge}</span></div><h3>{metric.label}</h3><div className="sensor-reading">{metric.value}<span>{metric.value === "—" || metric.value === "Off" || metric.value === "Offline" ? "" : metric.unit}</span><svg viewBox="0 0 120 40" fill="none" aria-hidden="true">{metric.points && <polyline points={metric.points} stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>}</svg></div><p>{metric.note}</p></section>)}</div>;
}
