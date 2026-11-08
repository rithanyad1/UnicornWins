import type { LiveData } from "@/hooks/use-live-data";
import { nodeDevice } from "@/hooks/use-live-data";
import { FACILITY_ID } from "./api";
import { incidentLabel, readingF } from "./utils";

export const roomNames: Record<string, string> = {
  A: "Server hall A", B: "Server hall B", C: "Network room", D: "Power & cooling",
};

// The SENTINEL node is installed in this room; the others have no sensors yet.
export const SENSOR_ROOM = process.env.NEXT_PUBLIC_SENSOR_ROOM || "A";

export type RoomState = {
  id: string;
  name: string;
  monitored: boolean;
  severity: "critical" | "warning" | "unknown" | "";
  summary: string;
  incidentId?: string;
};

export function roomStates(data: LiveData): RoomState[] {
  return Object.entries(roomNames).map(([id, name]) => {
    if (id !== SENSOR_ROOM) return { id, name, monitored: false, severity: "unknown", summary: "No sensor installed" };
    const node = nodeDevice(data);
    const latest = data.facility?.latest_reading;
    const active = data.incidents.filter(item => item.facility_id === FACILITY_ID && (item.status === "OPEN" || item.status === "RESPONDING"));
    const worst = active.find(item => item.severity === "CRITICAL") ?? active[0];
    if (!data.backendReachable) return { id, name, monitored: true, severity: "unknown", summary: "Backend offline" };
    if (node?.status !== "CONNECTED") return { id, name, monitored: true, severity: "unknown", summary: "SENTINEL node offline" };
    if (worst) {
      const responding = worst.status === "RESPONDING" ? " • responding" : "";
      return { id, name, monitored: true, severity: worst.severity === "CRITICAL" ? "critical" : "warning", summary: `${incidentLabel(worst)}${responding}`, incidentId: worst.id };
    }
    const nodeStatus = latest?.node_status ?? node.actuator_state.node_status;
    if (nodeStatus === "WARNING" || nodeStatus === "CRITICAL") {
      return { id, name, monitored: true, severity: nodeStatus === "CRITICAL" ? "critical" : "warning", summary: latest?.alert_reasons?.[0] ?? `Node reports ${nodeStatus.toLowerCase()}` };
    }
    return { id, name, monitored: true, severity: "", summary: latest ? `All systems normal • ${readingF(latest).toFixed(1)} °F` : "Waiting for readings" };
  });
}
