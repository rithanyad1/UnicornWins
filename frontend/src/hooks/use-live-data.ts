"use client";

import { useEffect, useState } from "react";

export type HardwareReport = {
  id: string;
  recorded_at: string;
  device_id: string;
  temperature_f: number | null;
  humidity_percent: number | null;
  vibration_g: number | null;
  status: string;
  fan_active: boolean;
  fan_speed_percent: number;
  alert_reasons: string[];
};

type Snapshot = {
  reports: HardwareReport[];
  connected: boolean;
  device_timeout_seconds: number;
  checked_at: string;
};

export function useLiveData() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [expiresAt, setExpiresAt] = useState(0);
  const [now, setNow] = useState(0);

  useEffect(() => {
    let disposed = false;
    let controller: AbortController | undefined;
    let nextPoll: ReturnType<typeof setTimeout>;
    const clock = setInterval(() => setNow(Date.now()), 1000);
    const poll = async () => {
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 4000);
      try {
        const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
        const response = await fetch(`${base}/api/v1/telemetry/hardware?limit=500`, {
          cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error("Hardware status unavailable");
        const data: Snapshot = await response.json();
        const last = data.reports.at(-1);
        const age = last ? Date.parse(data.checked_at) - Date.parse(last.recorded_at) : Infinity;
        const remaining = data.device_timeout_seconds * 1000 - Math.max(0, age);
        if (!disposed) {
          setSnapshot(data);
          setNow(Date.now());
          setExpiresAt(Number.isFinite(remaining) ? Date.now() + remaining : 0);
        }
      } catch {
        if (!disposed) { setSnapshot(null); setExpiresAt(0); }
      } finally {
        clearTimeout(timeout);
        if (!disposed) nextPoll = setTimeout(poll, 3000);
      }
    };
    void poll();
    return () => { disposed = true; clearInterval(clock); clearTimeout(nextPoll); controller?.abort(); };
  }, []);

  const connected = Boolean(snapshot?.connected && now < expiresAt);
  return {
    connected,
    report: connected ? snapshot?.reports.at(-1) ?? null : null,
    reports: connected ? snapshot?.reports ?? [] : [],
  };
}
