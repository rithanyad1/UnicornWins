"use client";

import { useId, useState } from "react";
import { Panel } from "@/components/ui/primitives";
import { useLiveMetric } from "@/lib/use-live-metric";

export function TrendChart({ title, asset = "temperature", wide = false }: { title: string; asset?: string; wide?: boolean }) {
  const widths: Record<string, number> = { temperature: 842, humidity: 387, vibration: 387, recovery: 1336 };
  return <Panel title={title} className="chart-panel"><div className={`chart-art ${wide ? "chart-wide" : ""}`}><img src={`/figma/${asset}.svg`} alt={`Illustrative ${title.toLowerCase()} trend`} width={widths[asset]} height="160" /></div><div className="chart-times"><span>14:20</span><span>14:26</span><span>14:32</span></div></Panel>;
}

const readings = {
  temperature: { label: "Temperature", base: 74.4, amplitude: 0.3, decimals: 1, unit: "°F", color: "#8973d7", values: [73, 73.2, 73.5, 73.9, 74.3, 74.9, 75.5, 76, 75.8, 75.3, 74.8, 74.4], range: [70, 78], ticks: [78, 76, 74, 72, 70] },
  humidity: { label: "Humidity", base: 21, amplitude: 0.6, decimals: 1, unit: "%", color: "#4b9fba", values: [20.8, 21, 21.2, 20.9, 21.1, 21, 20.7, 21.3, 21, 20.9, 21.1, 21], range: [15, 25], ticks: [25, 20, 15] },
  vibration: { label: "Vibration", base: 0.028, amplitude: 0.003, decimals: 3, unit: "G", color: "#c278a8", values: [0.027, 0.029, 0.026, 0.03, 0.028, 0.027, 0.029, 0.026, 0.028, 0.03, 0.027, 0.028], range: [0, 0.04], ticks: [0.04, 0.03, 0.02, 0.01, 0] },
};
export default function EnvironmentalCharts() {
  const [selected, setSelected] = useState<keyof typeof readings>("temperature");
  const gradientId = useId();
  const data = readings[selected];
  const liveValue = useLiveMetric(data.base, data.amplitude).toFixed(data.decimals);
  const y = (value: number) => 190 - (value - data.range[0]) / (data.range[1] - data.range[0]) * 164;
  const points = data.values.map((value, index) => `${54 + index * 54},${y(value)}`).join(" ");
  const lastY = y(data.values[data.values.length - 1]);
  return <section className="environment-panel"><div className="dashboard-section-heading"><div><h2>Environmental trends</h2><p>Small signals. The complete picture.</p></div><span className="chart-period">Last 15 minutes</span></div>
    <div className="chart-tabs" aria-label="Sensor chart">{Object.entries(readings).map(([key, item]) => <button key={key} onClick={() => setSelected(key as keyof typeof readings)} aria-pressed={selected === key}>{item.label}</button>)}</div>
    <div className="chart-reading" aria-live="polite"><strong>{liveValue}<span>{data.unit}</span></strong><span className="chart-trend">{selected === "temperature" ? "↘ Cooling response active" : "✓ Within normal range"}</span></div>
    <div className="environment-chart"><svg viewBox="0 0 690 235" role="img" aria-label={`Illustrative ${data.label.toLowerCase()} readings over the last 15 minutes. Current value ${liveValue} ${data.unit}.`}>
      <defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={data.color} stopOpacity=".22"/><stop offset="100%" stopColor={data.color} stopOpacity=".01"/></linearGradient></defs>
      {data.ticks.map(tick => <g key={tick}><line x1="54" x2="648" y1={y(tick)} y2={y(tick)} stroke="#eeedf5" strokeDasharray="3 5"/><text x="32" y={y(tick) + 4} textAnchor="end">{tick}</text></g>)}
      {selected === "temperature" && <g>
        <line x1="54" x2="648" y1={y(74)} y2={y(74)} stroke="#d59438" strokeDasharray="5 5"/><text x="645" y={y(74) - 8} textAnchor="end" className="threshold-label">74 °F warning</text>
        <line x1="54" x2="648" y1={y(76)} y2={y(76)} stroke="#d04768" strokeDasharray="5 5"/><text x="645" y={y(76) - 8} textAnchor="end" className="threshold-label">76 °F critical</text>
      </g>}
      <polygon points={`54,190 ${points} 648,190`} fill={`url(#${gradientId})`}/><polyline points={points} stroke={data.color} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="648" cy={lastY} r="8" fill={data.color} fillOpacity=".15"/><circle cx="648" cy={lastY} r="4" fill={data.color} stroke="white" strokeWidth="2"/>
      {["14:17", "14:20", "14:23", "14:26", "14:29", "14:32"].map((time, index) => <text key={time} x={54 + index * 118.8} y="222" textAnchor={index === 0 ? "start" : index === 5 ? "end" : "middle"}>{time}</text>)}
    </svg></div><div className="chart-legend"><span><i style={{ background: data.color }}/>{data.label}</span><span>Illustrative sensor readings</span></div></section>;
}
