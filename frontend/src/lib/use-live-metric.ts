"use client";

import { useEffect, useState } from "react";

/** Nudges a value around a baseline with small random jitter, so a hardcoded reading still feels live. */
export function useLiveMetric(base: number, amplitude: number, intervalMs = 2500): number {
  const [value, setValue] = useState(base);
  useEffect(() => {
    setValue(base);
    const id = setInterval(() => {
      setValue(prev => {
        const next = prev + (Math.random() - 0.5) * amplitude;
        const min = base - amplitude * 1.5;
        const max = base + amplitude * 1.5;
        return Math.min(max, Math.max(min, next));
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [base, amplitude, intervalMs]);
  return value;
}
