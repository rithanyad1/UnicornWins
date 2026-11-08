"use client";

import { useEffect, useRef } from "react";
import { sampleUnicorn } from "@/lib/unicorn-behavior";

export default function MeadowUnicorn({ id, x, y, size, row }: { id: number; x: number; y: number; size: number; row: number }) {
  const root = useRef<SVGGElement>(null);
  const facing = useRef<SVGGElement>(null);
  const initial = sampleUnicorn(id, 0);
  const center = x + size / 2;

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let elapsed = 0;
    let previous = performance.now();
    const update = () => {
      const now = performance.now();
      if (!document.hidden && !motion.matches) elapsed += Math.min((now - previous) / 1000, .2);
      previous = now;
      const state = sampleUnicorn(id, elapsed);
      root.current?.setAttribute("transform", `translate(${state.x} ${state.y})`);
      root.current?.setAttribute("data-action", motion.matches ? "pause" : state.action);
      facing.current?.setAttribute("transform", `translate(${center} 0) scale(${state.facing} 1) translate(${-center} 0)`);
    };
    update();
    const timer = window.setInterval(update, 50);
    return () => window.clearInterval(timer);
  }, [id, center]);

  return <g ref={root} className={`unicorn-roam unicorn-${id}`} transform={`translate(${initial.x} ${initial.y})`} data-action={initial.action}>
    <g ref={facing} transform={`translate(${center} 0) scale(${initial.facing} 1) translate(${-center} 0)`}>
      <ellipse cx={center} cy={y + size * .875} rx={size * .27} ry={size * .035} fill="#6B8D55" opacity=".3" />
      <ellipse cx={center} cy={y + size * .875} rx={size * .17} ry={size * .018} fill="#5F804B" opacity=".25" />
      <g className="unicorn-body">
        <svg x={x} y={y} width={size} height={size} viewBox="0 0 100 100" overflow="hidden">
          <image className="unicorn-sprite unicorn-walk-sheet" href="/models/unicorn-voxel-walk-atlas.png" x="0" y={-row * 100} width="400" height="400" />
          <image className="unicorn-sprite unicorn-graze-sheet" href="/models/unicorn-voxel-graze-atlas.png" x="0" y={-row * 100} width="400" height="400" />
        </svg>
      </g>
    </g>
  </g>;
}
