import type { LiveEvent } from "@/types";
import { apiBase } from "./api";

// Opens /ws/live and reconnects with backoff. Returns a function that closes it.
export function connectLive(
  onEvent: (event: LiveEvent) => void,
  onConnectionChange: (connected: boolean) => void,
): () => void {
  let socket: WebSocket | null = null;
  let retryDelay = 1000;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let closed = false;

  const open = () => {
    socket = new WebSocket(`${apiBase().replace(/^http/, "ws")}/ws/live`);
    socket.onopen = () => { retryDelay = 1000; onConnectionChange(true); };
    socket.onmessage = message => {
      try { onEvent(JSON.parse(message.data) as LiveEvent); } catch { /* ignore malformed frames */ }
    };
    socket.onclose = () => {
      onConnectionChange(false);
      if (closed) return;
      retryTimer = setTimeout(open, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 15000);
    };
    socket.onerror = () => socket?.close();
  };
  open();

  return () => {
    closed = true;
    clearTimeout(retryTimer);
    socket?.close();
  };
}
