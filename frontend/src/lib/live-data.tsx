"use client";

// Single source of truth for backend data in the browser.
//
// 1. Loads a REST snapshot from FastAPI (facilities, incidents, decisions, commands, events).
// 2. Applies /ws/live events as they arrive (readings, device/incident/command changes).
// 3. Re-syncs the snapshot after every WebSocket reconnect so missed events are recovered.
// Sensor history is fetched per facility on demand and then extended by live readings.
import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { ApiError, createApi, loadRuntimeConfig, operatorActions, websocketUrl, asReading, type SentinelApi } from "@/lib/api";
import { connectLive, type SocketState } from "@/lib/websocket";
import { isActive } from "@/lib/utils";
import type {
  Anomaly, Command, Decision, Device, Facility, Incident, IncidentDetail, LiveEvent, Reading, RuntimeConfig, SystemStatus,
} from "@/types";

const HISTORY_LIMIT = 900;          // backend caps history requests at 1000
const EVENT_LIMIT = 100;
const DECISION_LIMIT = 200;
const COMMAND_LIMIT = 200;
const STATUS_REFRESH_MS = 30_000;   // database/AI status has no push event
const STREAM_ONLY_EVENTS = new Set(["telemetry.reading", "ai.anomaly"]);

export type Connection = "loading" | "live" | "reconnecting" | "offline" | "unconfigured";

type State = {
  config: RuntimeConfig | null;
  connection: Connection;
  socket: SocketState;
  error: string | null;
  snapshotAt: string | null;
  status: SystemStatus | null;
  facilities: Record<string, Facility>;
  order: string[];
  incidents: Record<string, Incident>;
  decisions: Decision[];
  commands: Record<string, Command>;
  anomalies: Record<string, Anomaly>;
  events: LiveEvent[];
  history: Record<string, Reading[]>;
  revisions: Record<string, number>;
};

type Snapshot = Pick<State, "status" | "facilities" | "order" | "incidents" | "decisions" | "commands" | "anomalies" | "events">;

type Action =
  | { type: "config"; config: RuntimeConfig }
  | { type: "snapshot"; snapshot: Snapshot; at: string }
  | { type: "status"; status: SystemStatus }
  | { type: "socket"; socket: SocketState }
  | { type: "error"; error: string }
  | { type: "history"; facilityId: string; readings: Reading[] }
  | { type: "event"; event: LiveEvent }
  | { type: "incident"; incident: Incident };

const initialState: State = {
  config: null, connection: "loading", socket: "connecting", error: null, snapshotAt: null, status: null,
  facilities: {}, order: [], incidents: {}, decisions: [], commands: {}, anomalies: {}, events: [], history: {}, revisions: {},
};

const bump = (revisions: Record<string, number>, id: unknown) =>
  typeof id === "string" && id ? { ...revisions, [id]: (revisions[id] ?? 0) + 1 } : revisions;

function updateDevice(facilities: Record<string, Facility>, deviceId: string, patch: Partial<Device>): Record<string, Facility> {
  for (const facility of Object.values(facilities)) {
    const index = facility.devices.findIndex(device => device.device_id === deviceId);
    if (index === -1) continue;
    const devices = facility.devices.map((device, i) => i === index ? { ...device, ...patch } : device);
    return { ...facilities, [facility.id]: { ...facility, devices, connected_devices: devices.filter(device => device.status === "CONNECTED") } };
  }
  return facilities;
}

function applyEvent(state: State, event: LiveEvent): State {
  const data = event.data;
  const events = STREAM_ONLY_EVENTS.has(event.type) ? state.events : [event, ...state.events].slice(0, EVENT_LIMIT);
  switch (event.type) {
    case "telemetry.reading": {
      let reading: Reading;
      try { reading = asReading(data); } catch { return state; }
      const facility = state.facilities[reading.facility_id];
      const history = state.history[reading.facility_id];
      return {
        ...state,
        facilities: facility ? { ...state.facilities, [facility.id]: { ...facility, latest_reading: reading } } : state.facilities,
        history: history && !history.some(item => item.id === reading.id)
          ? { ...state.history, [reading.facility_id]: [...history, reading].slice(-HISTORY_LIMIT) }
          : state.history,
        anomalies: reading.anomaly ? { ...state.anomalies, [reading.facility_id]: reading.anomaly } : state.anomalies,
      };
    }
    case "ai.anomaly":
      return typeof data.facility_id === "string" ? { ...state, anomalies: { ...state.anomalies, [data.facility_id]: data as unknown as Anomaly } } : state;
    case "device.connection":
      return typeof data.device_id === "string"
        ? { ...state, events, facilities: updateDevice(state.facilities, data.device_id, { status: data.status as Device["status"] }) }
        : { ...state, events };
    case "device.updated":
      return typeof data.device_id === "string"
        ? { ...state, events, facilities: updateDevice(state.facilities, data.device_id, data as unknown as Device) }
        : { ...state, events };
    case "incident.created": case "incident.updated": case "incident.recovered": {
      const incident = data as unknown as Incident;
      if (typeof incident.id !== "string") return { ...state, events };
      return { ...state, events, incidents: { ...state.incidents, [incident.id]: { ...state.incidents[incident.id], ...incident } }, revisions: bump(state.revisions, incident.id) };
    }
    case "facility.status": {
      const facility = typeof data.facility_id === "string" ? state.facilities[data.facility_id] : undefined;
      return facility ? { ...state, events, facilities: { ...state.facilities, [facility.id]: { ...facility, status: data.status as Facility["status"] } } } : { ...state, events };
    }
    case "ai.decision": {
      const decision = data as unknown as Decision;
      if (typeof decision.id !== "string") return { ...state, events };
      return { ...state, events, decisions: [decision, ...state.decisions.filter(item => item.id !== decision.id)].slice(0, DECISION_LIMIT), revisions: bump(state.revisions, decision.incident_id) };
    }
    case "command.status": {
      const command = data as unknown as Command;
      if (typeof command.id !== "string") return { ...state, events };
      return { ...state, events, commands: { ...state.commands, [command.id]: command }, revisions: bump(state.revisions, command.incident_id) };
    }
    default:
      return { ...state, events };
  }
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "config":
      return action.config.apiUrl
        ? { ...state, config: action.config }
        : { ...state, config: action.config, connection: "unconfigured", error: "SENTINEL_PUBLIC_API_URL is not set for the frontend server." };
    case "snapshot":
      return { ...state, ...action.snapshot, snapshotAt: action.at, error: null,
        connection: state.socket === "open" ? "live" : state.socket === "connecting" ? "loading" : "reconnecting" };
    case "status":
      return { ...state, status: action.status };
    case "socket": {
      const connection: Connection = action.socket === "open" ? (state.snapshotAt ? "live" : "loading")
        : state.connection === "unconfigured" ? "unconfigured"
        : state.error ? "offline" : action.socket === "reconnecting" ? "reconnecting" : state.connection;
      return { ...state, socket: action.socket, connection };
    }
    case "error":
      return { ...state, error: action.error, connection: state.connection === "unconfigured" ? "unconfigured" : "offline" };
    case "history":
      return { ...state, history: { ...state.history, [action.facilityId]: action.readings.slice(-HISTORY_LIMIT) } };
    case "event":
      return applyEvent(state, action.event);
    case "incident":
      return { ...state, incidents: { ...state.incidents, [action.incident.id]: { ...state.incidents[action.incident.id], ...action.incident } }, revisions: bump(state.revisions, action.incident.id) };
  }
}

type LiveContext = State & {
  api: SentinelApi | null;
  /** Requests history for a facility (idempotent). */
  requestHistory: (facilityId: string) => void;
  refresh: () => Promise<void>;
  acknowledge: (incidentId: string, note?: string) => Promise<IncidentDetail>;
  sendCommand: typeof operatorActions.sendCommand;
  triggerSimulation: typeof operatorActions.triggerSimulation;
};

const Context = createContext<LiveContext | null>(null);

const errorText = (error: unknown) => error instanceof ApiError ? error.message : error instanceof Error ? error.message : "Unknown error";

export function LiveDataProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const api = useMemo(() => state.config?.apiUrl ? createApi(state.config.apiUrl) : null, [state.config]);
  const wanted = useRef(new Set<string>());
  const snapshotOk = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    loadRuntimeConfig(controller.signal)
      .then(config => dispatch({ type: "config", config }))
      .catch(error => { if (!controller.signal.aborted) dispatch({ type: "error", error: `Frontend configuration unavailable: ${errorText(error)}` }); });
    return () => controller.abort();
  }, []);

  const loadHistory = useCallback(async (facilityId: string) => {
    if (!api) return;
    try {
      dispatch({ type: "history", facilityId, readings: await api.history(facilityId, HISTORY_LIMIT) });
    } catch (error) {
      dispatch({ type: "error", error: errorText(error) });
    }
  }, [api]);

  const refresh = useCallback(async () => {
    if (!api) return;
    try {
      const [status, network, incidents, decisions, commands, anomalies, events] = await Promise.all([
        api.systemStatus(), api.networkOverview(), api.incidents(), api.decisions(),
        api.commands(COMMAND_LIMIT), api.anomalies(), api.events(EVENT_LIMIT),
      ]);
      dispatch({
        type: "snapshot", at: new Date().toISOString(), snapshot: {
          status,
          facilities: Object.fromEntries(network.facilities.map(facility => [facility.id, facility])),
          order: network.facilities.map(facility => facility.id),
          incidents: Object.fromEntries(incidents.map(incident => [incident.id, incident])),
          decisions: decisions.slice(0, DECISION_LIMIT),
          commands: Object.fromEntries(commands.map(command => [command.id, command])),
          anomalies,
          events,
        },
      });
      snapshotOk.current = true;
      await Promise.all([...wanted.current].map(loadHistory));
    } catch (error) {
      snapshotOk.current = false;
      dispatch({ type: "error", error: errorText(error) });
    }
  }, [api, loadHistory]);

  useEffect(() => {
    if (!api || !state.config?.apiUrl) return;
    void refresh();
    const disconnect = connectLive(websocketUrl(state.config.apiUrl), {
      onEvent: event => dispatch({ type: "event", event }),
      onState: socket => dispatch({ type: "socket", socket }),
      // Resync after a reconnect (events may have been missed) or if the first snapshot failed.
      onOpen: reconnected => { if (reconnected || !snapshotOk.current) void refresh(); },
    });
    const statusTimer = setInterval(() => {
      api.systemStatus().then(status => dispatch({ type: "status", status })).catch(() => undefined);
    }, STATUS_REFRESH_MS);
    return () => { clearInterval(statusTimer); disconnect(); };
  }, [api, refresh, state.config]);

  const requestHistory = useCallback((facilityId: string) => {
    if (wanted.current.has(facilityId)) return;
    wanted.current.add(facilityId);
    void loadHistory(facilityId);
  }, [loadHistory]);

  const acknowledge = useCallback(async (incidentId: string, note?: string) => {
    const incident = await operatorActions.acknowledgeIncident(incidentId, note);
    dispatch({ type: "incident", incident });
    return incident;
  }, []);

  const value = useMemo<LiveContext>(() => ({
    ...state, api, requestHistory, refresh, acknowledge,
    sendCommand: operatorActions.sendCommand, triggerSimulation: operatorActions.triggerSimulation,
  }), [state, api, requestHistory, refresh, acknowledge]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useLive(): LiveContext {
  const context = useContext(Context);
  if (!context) throw new Error("useLive must be used inside <LiveDataProvider>");
  return context;
}

export function useFacilities(): Facility[] {
  const { facilities, order } = useLive();
  return useMemo(() => order.map(id => facilities[id]).filter(Boolean), [facilities, order]);
}

export function useActiveIncidents(facilityId?: string): Incident[] {
  const { incidents } = useLive();
  return useMemo(() => Object.values(incidents)
    .filter(incident => isActive(incident) && (!facilityId || incident.facility_id === facilityId))
    .sort((a, b) => b.detected_at.localeCompare(a.detected_at)), [incidents, facilityId]);
}

export function useFacilityHistory(facilityId: string | undefined): Reading[] | null {
  const { history, requestHistory } = useLive();
  useEffect(() => { if (facilityId) requestHistory(facilityId); }, [facilityId, requestHistory]);
  return facilityId ? history[facilityId] ?? null : null;
}

/** Fetches an incident's full detail and re-fetches when live events touch it. */
export function useIncidentDetail(id: string) {
  const { api, revisions, snapshotAt } = useLive();
  const revision = revisions[id] ?? 0;
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!api) return;
    const controller = new AbortController();
    api.incident(id, controller.signal)
      .then(result => { setDetail(result); setError(null); })
      .catch(reason => { if (!controller.signal.aborted) setError(reason); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, id, revision, snapshotAt]);
  return { detail, error, loading: loading && !detail };
}

/** Re-renders periodically so relative times ("12s ago") stay current. */
export function useNow(intervalMs = 5_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}
