// Shapes returned by the SENTINEL backend (FastAPI, /api/v1).

export type Severity = "INFO" | "WARNING" | "CRITICAL";
export type IncidentStatus = "OPEN" | "RESPONDING" | "RESOLVED" | "UNRESOLVED";
export type FacilityStatus = "HEALTHY" | "WARNING" | "CRITICAL" | "DISCONNECTED";

export type Reading = {
  id: string;
  device_id: string;
  facility_id: string;
  temperature_c: number;
  humidity_percent: number;
  vibration_score: number;
  water_detected: boolean;
  timestamp_ms: number;
  recorded_at: string;
  is_simulated: boolean;
  // Present on readings from the SENTINEL Pico node.
  temperature_f?: number;
  vibration_g?: number;
  fan?: boolean;
  fan_speed_percent?: number;
  node_status?: string;
  alert_reasons?: string[];
};

export type Device = {
  device_id: string;
  facility_id: string;
  device_type: string;
  status: "CONNECTED" | "DISCONNECTED";
  last_seen: string | null;
  actuator_state: {
    fan?: boolean;
    fan_speed_percent?: number;
    node_status?: string;
    alert_reasons?: string[];
    [key: string]: unknown;
  };
  firmware_version: string | null;
};

export type Decision = {
  id: string;
  incident_id: string | null;
  model_name: string;
  anomaly_score: number | null;
  anomaly_detected: boolean;
  severity: string;
  reasoning: string;
  recommended_action: string | null;
  decision_source: string;
  created_at: string;
};

export type HardwareCommand = {
  id: string;
  device_id: string;
  command_type: string;
  status: string;
  created_at: string;
  acknowledged_at: string | null;
};

export type VerificationPoint = {
  recorded_at?: string;
  temperature_c?: number;
  humidity_percent?: number;
  vibration_score?: number;
};

export type Incident = {
  id: string;
  facility_id: string;
  incident_type: string;
  severity: Severity;
  status: IncidentStatus;
  description: string;
  detected_readings: Partial<Reading> & { device_id?: string };
  verification_data: VerificationPoint[];
  detected_at: string;
  resolved_at: string | null;
  ai_analysis?: Decision | null;
  decisions?: Decision[];
  hardware_commands?: HardwareCommand[];
};

export type Facility = {
  id: string;
  name: string;
  city: string;
  status: FacilityStatus;
  is_simulated: boolean;
  latest_reading: Reading | null;
  active_incidents: Incident[];
  connected_devices: Device[];
  device_count: number;
};

export type Thresholds = {
  high_temp_c: number;
  critical_temp_c: number;
  recovery_temp_c: number;
  high_humidity_percent: number;
  vibration: number;
};

export type SystemStatus = {
  backend_status: string;
  gemini_status: string;
  anomaly_model_status: string;
  connected_hardware: number;
  active_incidents: number;
  operating_mode: string;
  latest_telemetry_at: string | null;
  thresholds: Thresholds;
  devices: Device[];
};

export type LiveEvent = {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
};
