"use client";

import Link from "next/link";
import { useLiveData } from "@/hooks/use-live-data";
import { roomStates } from "@/lib/rooms";

export default function RoomGrid() {
  const rooms = roomStates(useLiveData());
  return <div className="room-grid">{rooms.map(({ id, name, summary, severity }) => {
    const alert = severity === "critical" || severity === "warning";
    return <Link href={`/facility?room=${id}`} className={`room-card ${alert ? `room-alert room-alert-${severity}` : ""}`} key={id}><div className="room-card-top"><span className={`room-id room-${id}`}>{id}</span>{alert && <span className="room-alert-badge">{severity === "critical" ? "Critical" : "Warning"}</span>}</div><h3>{name}</h3><p className={alert ? "room-alert-message" : undefined}>{alert && <span className="room-alert-symbol" aria-hidden="true">!</span>}{summary}</p></Link>;
  })}</div>;
}
