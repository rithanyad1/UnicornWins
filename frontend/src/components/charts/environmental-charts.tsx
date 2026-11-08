"use client";

import { useId, useState } from "react";
import { Panel } from "@/components/ui/primitives";

export function TrendChart({ title, asset = "temperature", wide = false }: { title: string; asset?: string; wide?: boolean }) {
  const widths: Record<string, number> = { temperature: 842, humidity: 387, vibration: 387, recovery: 1336 };
  return <Panel title={title} className="chart-panel"><div className={`chart-art ${wide ? "chart-wide" : ""}`}><img src={`/figma/${asset}.svg`} alt={`Illustrative ${title.toLowerCase()} trend`} width={widths[asset]} height="160" /></div><div className="chart-times"><span>14:20</span><span>14:26</span><span>14:32</span></div></Panel>;
}

const readings = {
  temperature: { label: "Temperature", value: "38.2", unit: "°C", color: "#8973d7", values: [29, 29.4, 30.1, 31.8, 33, 35.8, 39.4, 41.2, 42, 41, 39.6, 38.2], range: [25, 45], ticks: [45, 40, 35, 30, 25] },
  humidity: { label: "Humidity", value: "45", unit: "%", color: "#4b9fba", values: [43, 44, 43.5, 44.2, 44, 45, 44.5, 46, 45.5, 44.8, 45.2, 45], range: [35, 55], ticks: [55, 50, 45, 40, 35] },
  vibration: { label: "Vibration", value: "0.08", unit: "", color: "#c278a8", values: [0.07, 0.07, 0.09, 0.06, 0.08, 0.075, 0.09, 0.065, 0.08, 0.07, 0.085, 0.08], range: [0, 0.16], ticks: [0.16, 0.12, 0.08, 0.04, 0] },
};
export default function EnvironmentalCharts() {
  const [selected, setSelected] = useState<keyof typeof readings>("temperature");
  const gradientId = useId();
  const data = readings[selected];
  const y = (value: number) => 190 - (value - data.range[0]) / (data.range[1] - data.range[0]) * 164;
  const points = data.values.map((value, index) => `${54 + index * 54},${y(value)}`).join(" ");
  const lastY = y(data.values[data.values.length - 1]);
  return <section className="environment-panel"><div className="dashboard-section-heading"><div><h2>Environmental trends</h2><p>Small signals. The complete picture.</p></div><span className="chart-period">Last 15 minutes</span></div>
    <div className="chart-tabs" aria-label="Sensor chart">{Object.entries(readings).map(([key, item]) => <button key={key} onClick={() => setSelected(key as keyof typeof readings)} aria-pressed={selected === key}>{item.label}</button>)}</div>
    <div className="chart-reading" aria-live="polite"><strong>{data.value}<span>{data.unit}</span></strong><span className="chart-trend">{selected === "temperature" ? "↘ Cooling response active" : "✓ Within normal range"}</span></div>
    <div className="environment-chart"><svg viewBox="0 0 690 235" role="img" aria-label={`Illustrative ${data.label.toLowerCase()} readings over the last 15 minutes. Current value ${data.value} ${data.unit}.`}>
      <defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={data.color} stopOpacity=".22"/><stop offset="100%" stopColor={data.color} stopOpacity=".01"/></linearGradient></defs>
      {data.ticks.map(tick => <g key={tick}><line x1="54" x2="648" y1={y(tick)} y2={y(tick)} stroke="#eeedf5" strokeDasharray="3 5"/><text x="32" y={y(tick) + 4} textAnchor="end">{tick}</text></g>)}
      {selected === "temperature" && <g><line x1="54" x2="648" y1={y(35)} y2={y(35)} stroke="#d6b18d" strokeDasharray="5 5"/><text x="645" y={y(35) - 8} textAnchor="end" className="threshold-label">35 °C threshold</text></g>}
      <polygon points={`54,190 ${points} 648,190`} fill={`url(#${gradientId})`}/><polyline points={points} stroke={data.color} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="648" cy={lastY} r="8" fill={data.color} fillOpacity=".15"/><circle cx="648" cy={lastY} r="4" fill={data.color} stroke="white" strokeWidth="2"/>
      {["14:17", "14:20", "14:23", "14:26", "14:29", "14:32"].map((time, index) => <text key={time} x={54 + index * 118.8} y="222" textAnchor={index === 0 ? "start" : index === 5 ? "end" : "middle"}>{time}</text>)}
    </svg></div><div className="chart-legend"><span><i style={{ background: data.color }}/>{data.label}</span><span>Illustrative sensor readings</span></div></section>;
}
