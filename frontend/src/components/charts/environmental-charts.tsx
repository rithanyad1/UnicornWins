"use client";

import { useId, useState } from "react";
import { Panel } from "@/components/ui/primitives";
import { useLiveData } from "@/hooks/use-live-data";
import { cToF, formatTime, readingF } from "@/lib/utils";

type Series = { label: string; unit: string; color: string; values: number[]; times: string[]; threshold?: { value: number; label: string } };

function niceRange(values: number[], threshold?: number): [number, number] {
  const all = threshold === undefined ? values : [...values, threshold];
  let min = Math.min(...all);
  let max = Math.max(...all);
  if (max - min < 1e-6) { min -= 1; max += 1; }
  const pad = (max - min) * 0.15;
  return [min - pad, max + pad];
}

// A line chart of real readings, oldest on the left.
export function LineChart({ series, height = 235, label }: { series: Series; height?: number; label: string }) {
  const gradientId = useId();
  const { values, times, threshold, color } = series;
  if (values.length < 2) return <div className="empty-state"><p>Waiting for readings from the SENTINEL node…</p></div>;
  const [lo, hi] = niceRange(values, threshold?.value);
  const bottom = height - 45;
  const y = (value: number) => bottom - (value - lo) / (hi - lo) * (bottom - 26);
  const x = (index: number) => 54 + index * (594 / (values.length - 1));
  const points = values.map((value, index) => `${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
  const ticks = Array.from({ length: 5 }, (_, index) => lo + (hi - lo) * (index + 0.5) / 5);
  const labelIndexes = [0, Math.floor((values.length - 1) / 2), values.length - 1];
  return <svg viewBox={`0 0 690 ${height}`} role="img" aria-label={label}>
    <defs><linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity=".22"/><stop offset="100%" stopColor={color} stopOpacity=".01"/></linearGradient></defs>
    {ticks.map(tick => <g key={tick}><line x1="54" x2="648" y1={y(tick)} y2={y(tick)} stroke="#eeedf5" strokeDasharray="3 5"/><text x="32" y={y(tick) + 4} textAnchor="end">{tick.toFixed(hi - lo < 1 ? 2 : 1)}</text></g>)}
    {threshold && <g><line x1="54" x2="648" y1={y(threshold.value)} y2={y(threshold.value)} stroke="#d6b18d" strokeDasharray="5 5"/><text x="645" y={y(threshold.value) - 8} textAnchor="end" className="threshold-label">{threshold.label}</text></g>}
    <polygon points={`54,${bottom} ${points} 648,${bottom}`} fill={`url(#${gradientId})`}/><polyline points={points} stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="648" cy={y(values[values.length - 1])} r="8" fill={color} fillOpacity=".15"/><circle cx="648" cy={y(values[values.length - 1])} r="4" fill={color} stroke="white" strokeWidth="2"/>
    {labelIndexes.map((index, position) => <text key={position} x={x(index)} y={height - 13} textAnchor={position === 0 ? "start" : position === 2 ? "end" : "middle"}>{formatTime(times[index])}</text>)}
  </svg>;
}

export function TrendChart({ title, series }: { title: string; series: Series }) {
  return <Panel title={title} className="chart-panel"><div className="environment-chart"><LineChart series={series} label={title} /></div></Panel>;
}

type Key = "temperature" | "humidity" | "vibration";

export default function EnvironmentalCharts() {
  const data = useLiveData();
  const [selected, setSelected] = useState<Key>("temperature");
  const recent = data.history.slice(-120);
  const times = recent.map(r => r.recorded_at);
  const limits = data.status?.thresholds;
  const all: Record<Key, Series> = {
    temperature: { label: "Temperature", unit: "°F", color: "#8973d7", values: recent.map(readingF), times, threshold: limits && { value: cToF(limits.high_temp_c), label: `${cToF(limits.high_temp_c).toFixed(0)} °F threshold` } },
    humidity: { label: "Humidity", unit: "%", color: "#4b9fba", values: recent.map(r => r.humidity_percent), times, threshold: limits && { value: limits.high_humidity_percent, label: `${limits.high_humidity_percent}% threshold` } },
    vibration: { label: "Vibration", unit: "g", color: "#c278a8", values: recent.map(r => r.vibration_g ?? r.vibration_score), times, threshold: limits && { value: limits.vibration, label: `${limits.vibration} g threshold` } },
  };
  const series = all[selected];
  const current = series.values.at(-1);
  const aboveThreshold = current !== undefined && series.threshold && current >= series.threshold.value;
  const period = recent.length > 1 ? `Last ${Math.max(1, Math.round((new Date(times.at(-1)!).getTime() - new Date(times[0]).getTime()) / 60000))} min` : "Live";
  return <section className="environment-panel"><div className="dashboard-section-heading"><div><h2>Environmental trends</h2><p>Live readings from the SENTINEL node.</p></div><span className="chart-period">{period}</span></div>
    <div className="chart-tabs" aria-label="Sensor chart">{(Object.keys(all) as Key[]).map(key => <button key={key} onClick={() => setSelected(key)} aria-pressed={selected === key}>{all[key].label}</button>)}</div>
    <div className="chart-reading" aria-live="polite"><strong>{current === undefined ? "—" : current.toFixed(selected === "vibration" ? 3 : 1)}<span>{current === undefined ? "" : series.unit}</span></strong><span className="chart-trend">{current === undefined ? "No readings yet" : aboveThreshold ? "▲ Above threshold" : "✓ Within normal range"}</span></div>
    <div className="environment-chart"><LineChart series={series} label={`${series.label} readings. Current value ${current ?? "unknown"} ${series.unit}.`} /></div>
    <div className="chart-legend"><span><i style={{ background: series.color }}/>{series.label}</span><span>{recent.length} readings</span></div></section>;
}
