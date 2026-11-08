import type { Incident } from "@/types";

export const incidents: Incident[] = [
  { id: "1042", type: "Thermal anomaly", severity: "Warning", time: "14:32:01", status: "Responding", description: "High-temperature threshold crossed at the desk & workstation sensor." },
  { id: "1041", type: "Water detected", severity: "Critical", time: "13:18:09", status: "Open", description: "Moisture sensor detected condensation near the mini-fridge nook. Simulated shutdown recorded; room power remains connected." },
  { id: "1040", type: "Device disconnected", severity: "Warning", time: "12:41:22", status: "Unresolved", description: "Pico heartbeat timed out. Current actuator states are unknown." },
  { id: "1039", type: "Abnormal vibration", severity: "Warning", time: "11:05:17", status: "Resolved", description: "Vibration exceeded the 0.028G calibrated baseline. Subsequent readings confirmed recovery." },
  { id: "1038", type: "Thermal anomaly", severity: "Critical", time: "10:16:42", status: "Resolved", description: "Critical temperature (76°F) triggered emergency cooling. Subsequent valid readings confirmed recovery." },
];
