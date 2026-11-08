import type { CSSProperties } from "react";

const paths: Record<string, React.ReactNode> = {
  temperature: <><path d="M9 14.5V5a3 3 0 0 1 6 0v9.5a5 5 0 1 1-6 0Z"/><path d="M12 9v9"/><path d="M17 5h3m-3 4h2"/></>,
  humidity: <path d="M12 3S5 11 5 15a7 7 0 0 0 14 0c0-4-7-12-7-12ZM8 15a4 4 0 0 0 4 4"/>,
  vibration: <path d="M2 12h4l3-7 5 14 3-7h5"/>,
  cooling: <><circle cx="12" cy="12" r="2"/><path d="M10 10C3 9 5 2 9 3c3 0 4 4 3 7m2 0c5-5 10 0 7 3-2 2-5 1-7-1m-2 2c2 7-5 9-7 5-1-3 2-5 5-6"/></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
  shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/></>,
  sparkle: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/><path d="m20 2 1 2 2 1-2 1-1 2-1-2-2-1 2-1Z"/></>,
  grid: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
};
export default function DashboardIcon({ name, className = "", style }: { name: string; className?: string; style?: CSSProperties }) {
  return <svg className={`dashboard-icon ${className}`} style={style} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.grid}</svg>;
}
