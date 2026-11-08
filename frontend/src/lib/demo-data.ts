import type { Incident } from "@/types";

export const incidents: Incident[] = [
  { id: "1042", type: "Thermal anomaly", severity: "Warning", time: "14:32:01", status: "Responding", description: "High-temperature threshold crossed in Server hall A." },
  { id: "1041", type: "Water detected", severity: "Critical", time: "13:18:09", status: "Open", description: "Water sensor detected moisture in the cooling area. Simulated shutdown recorded; facility power remains connected." },
  { id: "1040", type: "Device disconnected", severity: "Warning", time: "12:41:22", status: "Unresolved", description: "Pico heartbeat timed out. Current actuator states are unknown." },
  { id: "1039", type: "Abnormal vibration", severity: "Warning", time: "11:05:17", status: "Resolved", description: "Vibration exceeded the calibrated baseline. Subsequent readings confirmed recovery." },
  { id: "1038", type: "Thermal anomaly", severity: "Critical", time: "10:16:42", status: "Resolved", description: "Critical temperature triggered emergency cooling. Subsequent valid readings confirmed recovery." },
];
