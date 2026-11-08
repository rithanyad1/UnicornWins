export type UnicornAction = "walk" | "pause" | "graze";
type Stop = { action: UnicornAction; seconds: number; x: number; y: number };

// Coordinates are offsets within each unicorn's own patch of meadow.
const routes: Record<number, { phase: number; stops: Stop[] }> = {
  1: { phase: 0, stops: [
    { action: "walk", seconds: 9, x: 115, y: -14 },
    { action: "pause", seconds: 2.4, x: 115, y: -14 },
    { action: "graze", seconds: 6.5, x: 115, y: -14 },
    { action: "walk", seconds: 6, x: 160, y: 3 },
    { action: "pause", seconds: 3, x: 160, y: 3 },
    { action: "walk", seconds: 12, x: 20, y: 12 },
    { action: "graze", seconds: 5, x: 20, y: 12 },
    { action: "walk", seconds: 3, x: 0, y: 0 },
  ] },
  2: { phase: 12, stops: [
    { action: "walk", seconds: 8, x: -85, y: 12 },
    { action: "graze", seconds: 7, x: -85, y: 12 },
    { action: "walk", seconds: 13, x: 90, y: 5 },
    { action: "pause", seconds: 4, x: 90, y: 5 },
    { action: "graze", seconds: 4.5, x: 90, y: 5 },
    { action: "walk", seconds: 8, x: 0, y: 0 },
    { action: "pause", seconds: 2, x: 0, y: 0 },
  ] },
  3: { phase: 5, stops: [
    { action: "walk", seconds: 10, x: -105, y: 18 },
    { action: "pause", seconds: 3.5, x: -105, y: 18 },
    { action: "walk", seconds: 7, x: -150, y: -4 },
    { action: "graze", seconds: 8, x: -150, y: -4 },
    { action: "walk", seconds: 14, x: 35, y: 10 },
    { action: "pause", seconds: 2, x: 35, y: 10 },
    { action: "walk", seconds: 4, x: 0, y: 0 },
    { action: "graze", seconds: 5, x: 0, y: 0 },
  ] },
  4: { phase: 18, stops: [
    { action: "walk", seconds: 11, x: 100, y: -8 },
    { action: "pause", seconds: 5, x: 100, y: -8 },
    { action: "graze", seconds: 5.5, x: 100, y: -8 },
    { action: "walk", seconds: 9, x: 165, y: 13 },
    { action: "graze", seconds: 7.5, x: 165, y: 13 },
    { action: "walk", seconds: 16, x: 0, y: 0 },
    { action: "pause", seconds: 4, x: 0, y: 0 },
  ] },
};

export function sampleUnicorn(id: number, elapsed: number) {
  const { phase, stops } = routes[id];
  const duration = stops.reduce((total, stop) => total + stop.seconds, 0);
  let time = (elapsed + phase) % duration;
  let previous = stops[stops.length - 1];
  // Preserve the last walking direction while standing or grazing.
  let facing = 1;
  for (let i = stops.length - 1; i >= 0; i--) {
    const from = stops[(i + stops.length - 1) % stops.length];
    if (stops[i].action === "walk" && stops[i].x !== from.x) {
      facing = Math.sign(stops[i].x - from.x);
      break;
    }
  }
  for (const stop of stops) {
    if (stop.action === "walk" && stop.x !== previous.x) facing = Math.sign(stop.x - previous.x);
    if (time < stop.seconds) {
      const progress = stop.action === "walk" ? time / stop.seconds : 1;
      return { action: stop.action, facing, x: previous.x + (stop.x - previous.x) * progress, y: previous.y + (stop.y - previous.y) * progress };
    }
    time -= stop.seconds;
    previous = stop;
  }
  return { action: previous.action, facing, x: previous.x, y: previous.y };
}
