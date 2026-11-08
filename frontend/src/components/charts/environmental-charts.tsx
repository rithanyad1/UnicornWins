"use client";

import { useState } from "react";
import type { HardwareReport } from "@/hooks/use-live-data";
import { Panel } from "@/components/ui/primitives";

export function TrendChart({ title, asset = "temperature", wide = false }: { title: string; asset?: string; wide?: boolean }) {
  const widths: Record<string, number> = { temperature: 842, humidity: 387, vibration: 387, recovery: 1336 };
  return <Panel title={title} className="chart-panel"><div className={`chart-art ${wide ? "chart-wide" : ""}`}><img src={`/figma/${asset}.svg`} alt={`Illustrative ${title.toLowerCase()} trend`} width={widths[asset]} height="160" /></div><div className="chart-times"><span>14:20</span><span>14:26</span><span>14:32</span></div></Panel>;
}

const sensors = {
  temperature_f: { label: "Temperature", unit: "°F", color: "#8973d7", decimals: 1 },
  humidity_percent: { label: "Humidity", unit: "%", color: "#4b9fba", decimals: 0 },
  vibration_g: { label: "Vibration", unit: "g", color: "#c278a8", decimals: 3 },
};

export default function EnvironmentalCharts({ report, reports }: { report: HardwareReport | null; reports: HardwareReport[] }) {
  const [selected, setSelected] = useState<keyof typeof sensors>("temperature_f");
  const sensor = sensors[selected];
  const current = report?.[selected];
  const end = report ? Date.parse(report.recorded_at) : 0;
  const start = end - 15 * 60 * 1000;
  const history = reports.filter(item => Date.parse(item.recorded_at) >= start);
  const values = history.flatMap(item => item[selected] == null ? [] : [item[selected]]);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const padding = Math.max((max - min) * 0.15, selected === "vibration_g" ? 0.01 : 1);
  const bottom = selected === "temperature_f" ? min - padding : Math.max(0, min - padding);
  const top = max + padding;
  const x = (date: string) => 54 + (Date.parse(date) - start) / (end - start) * 594;
  const y = (value: number) => 190 - (value - bottom) / (top - bottom) * 164;
  let penDown = false;
  let previousTime = 0;
  const path = history.map(item => {
    const value = item[selected];
    if (value == null) { penDown = false; return ""; }
    const time = Date.parse(item.recorded_at);
    const command = penDown && time - previousTime < 15000 ? "L" : "M";
    penDown = true;
    previousTime = time;
    return `${command}${x(item.recorded_at)},${y(value)}`;
  }).join(" ");
  const ticks = Array.from({ length: 5 }, (_, index) => bottom + (top - bottom) * index / 4);
  return <section className="environment-panel">
    <div className="dashboard-section-heading"><div><h2>Environmental trends</h2><p>Small signals. The complete picture.</p></div><span className="chart-period">Last 15 minutes</span></div>
    <div className="chart-tabs" aria-label="Sensor chart">{Object.entries(sensors).map(([key, item]) => <button key={key} onClick={() => setSelected(key as keyof typeof sensors)} aria-pressed={selected === key}>{item.label}</button>)}</div>
    <div className="chart-reading" aria-live="polite"><strong>{current == null ? "null" : current.toFixed(sensor.decimals)}{current != null && <span>{sensor.unit}</span>}</strong><span className="chart-trend">{!report ? "Hardware disconnected" : current == null ? "Sensor unavailable" : "Live hardware reading"}</span></div>
    <div className="environment-chart"><svg viewBox="0 0 690 235" role="img" aria-label={`${sensor.label} history. Current value ${current == null ? "null" : `${current} ${sensor.unit}`}.`}>
      {ticks.map(tick => <g key={tick}><line x1="54" x2="648" y1={y(tick)} y2={y(tick)} stroke="#eeedf5" strokeDasharray="3 5"/>{report && <text x="44" y={y(tick) + 4} textAnchor="end">{tick.toFixed(selected === "vibration_g" ? 3 : 1)}</text>}</g>)}
      {report && values.length > 0 ? <><path d={path} stroke={sensor.color} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>{history.map(item => item[selected] == null ? null : <circle key={item.id} cx={x(item.recorded_at)} cy={y(item[selected])} r="3" fill={sensor.color}/>)}</> : <text x="345" y="112" textAnchor="middle">{report ? "No sensor readings available" : "No hardware connected"}</text>}
      {report && [0, 1, 2, 3, 4, 5].map(index => <text key={index} x={54 + index * 118.8} y="222" textAnchor={index === 0 ? "start" : index === 5 ? "end" : "middle"}>{new Date(start + index * 180000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</text>)}
    </svg></div><div className="chart-legend"><span><i style={{ background: sensor.color }}/>{sensor.label}</span><span>{report ? "Recorded hardware readings" : "Waiting for hardware connection"}</span></div>
  </section>;
}
