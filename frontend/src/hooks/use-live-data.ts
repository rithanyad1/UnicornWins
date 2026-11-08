"use client";

import { useSyncExternalStore } from "react";
import { api, FACILITY_ID } from "@/lib/api";
import { connectLive } from "@/lib/websocket";
import type { Decision, Device, Facility, Incident, LiveEvent, Reading, SystemStatus } from "@/types";

export type LiveData = {
  loaded: boolean;
  backendReachable: boolean;
  liveConnected: boolean;
  facility: Facility | null;
  history: Reading[];
  incidents: Incident[];
  decisions: Decision[];
  events: LiveEvent[];
  status: SystemStatus | null;
};

const HISTORY_LIMIT = 300;
const QUIET_EVENTS = new Set(["telemetry.reading", "device.report"]);

let state: LiveData = {
  loaded: false, backendReachable: false, liveConnected: false, facility: null,
  history: [], incidents: [], decisions: [], events: [], status: null,
};
const listeners = new Set<() => void>();
let stopLive: (() => void) | null = null;
let pollTimer: ReturnType<typeof setInterval> | undefined;
let refreshTimer: ReturnType<typeof setTimeout> | undefined;

function update(patch: Partial<LiveData>) {
  state = { ...state, ...patch };
  listeners.forEach(listener => listener());
}

async function refresh(includeHistory = false) {
  try {
    const [facility, incidents, decisions, status, events, history] = await Promise.all([
      api.facility(), api.incidents(), api.decisions(), api.status(), api.events(),
      includeHistory ? api.history(FACILITY_ID, HISTORY_LIMIT) : Promise.resolve(null),
    ]);
    update({
      loaded: true, backendReachable: true, facility, incidents, decisions, status, events,
      ...(history ? { history } : {}),
    });
  } catch {
    update({ loaded: true, backendReachable: false });
  }
}

function scheduleRefresh() {
  clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => void refresh(), 400);
}

function onEvent(event: LiveEvent) {
  if (event.type === "telemetry.reading") {
    const reading = event.data as unknown as Reading;
    if (reading.facility_id !== FACILITY_ID) return;
    update({
      history: [...state.history, reading].slice(-HISTORY_LIMIT),
      facility: state.facility ? { ...state.facility, latest_reading: reading } : state.facility,
    });
    return;
  }
  if (!QUIET_EVENTS.has(event.type)) update({ events: [event, ...state.events].slice(0, 30) });
  scheduleRefresh();
}

function start() {
  void refresh(true);
  stopLive = connectLive(onEvent, connected => {
    update({ liveConnected: connected });
    if (connected) void refresh(true);
  });
  // Safety net in case a WebSocket event is missed.
  pollTimer = setInterval(() => void refresh(), 15000);
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  if (listeners.size === 1) start();
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      stopLive?.();
      stopLive = null;
      clearInterval(pollTimer);
      clearTimeout(refreshTimer);
    }
  };
}

const serverSnapshot = state;

export function useLiveData(): LiveData {
  return useSyncExternalStore(subscribe, () => state, () => serverSnapshot);
}

export function nodeDevice(data: LiveData): Device | undefined {
  return data.status?.devices.find(device => device.facility_id === FACILITY_ID && device.device_type === "SENTINEL_NODE")
    ?? data.status?.devices.find(device => device.facility_id === FACILITY_ID && device.status === "CONNECTED");
}
