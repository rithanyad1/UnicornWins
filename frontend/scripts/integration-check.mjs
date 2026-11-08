#!/usr/bin/env node
// End-to-end integration check: Next.js frontend ⇄ FastAPI backend ⇄ WebSocket.
//
// Usage (with both servers running):
//   FRONTEND_URL=http://localhost:3000 node scripts/integration-check.mjs
//   node scripts/integration-check.mjs --skip-workflow   # read-only checks
//
// The backend URL is discovered from the frontend's /api/config, exactly as the
// browser does. The workflow test only drives *simulated* facilities through the
// operator proxy (overheating → incident → acknowledgment → recovery); it never
// sends physical hardware commands. Requires Node 22+ (global fetch and WebSocket).

const FRONTEND = (process.env.FRONTEND_URL || "http://localhost:3000").replace(/\/+$/, "");
const SKIP_WORKFLOW = process.argv.includes("--skip-workflow");
const results = [];
let failed = 0;

const record = (status, name, detail = "") => {
  results.push({ status, name, detail });
  if (status === "FAIL") failed++;
  console.log(`[${status}] ${name}${detail ? ` — ${detail}` : ""}`);
};
async function check(name, fn) {
  try { record("PASS", name, (await fn()) || ""); } catch (error) { record("FAIL", name, error instanceof Error ? error.message : String(error)); }
}
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const isObject = value => typeof value === "object" && value !== null && !Array.isArray(value);

async function getJson(url, init) {
  const response = await fetch(url, { ...init, signal: AbortSignal.timeout(15_000) });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { throw new Error(`${url} returned non-JSON (${response.status})`); }
  return { response, body, text };
}

// --- live event stream -----------------------------------------------------
function openStream(wsUrl) {
  const socket = new WebSocket(wsUrl);
  const waiters = [];
  const seen = [];
  socket.addEventListener("message", message => {
    const event = JSON.parse(String(message.data));
    seen.push(event);
    for (const waiter of [...waiters]) if (waiter.match(event)) { waiters.splice(waiters.indexOf(waiter), 1); waiter.resolve(event); }
  });
  const opened = new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", () => reject(new Error(`WebSocket failed: ${wsUrl}`)), { once: true });
  });
  const waitFor = (match, timeoutMs, label) => new Promise((resolve, reject) => {
    const earlier = seen.find(match);
    if (earlier) return resolve(earlier);
    const waiter = { match, resolve };
    waiters.push(waiter);
    setTimeout(() => { const index = waiters.indexOf(waiter); if (index !== -1) { waiters.splice(index, 1); reject(new Error(`timed out after ${timeoutMs / 1000}s waiting for ${label}`)); } }, timeoutMs);
  });
  return { socket, opened, waitFor };
}

const operator = (path, body) => getJson(`${FRONTEND}/api/operator/${path}`, {
  method: "POST", headers: { "Content-Type": "application/json", Origin: FRONTEND }, body: JSON.stringify(body ?? {}),
});

async function main() {
  console.log(`Frontend: ${FRONTEND}`);
  let config;
  await check("frontend /api/config serves runtime backend URL", async () => {
    const { response, body } = await getJson(`${FRONTEND}/api/config`);
    assert(response.ok, `status ${response.status}`);
    assert(typeof body.apiUrl === "string" && body.apiUrl, "apiUrl not configured (set SENTINEL_PUBLIC_API_URL)");
    assert(typeof body.operatorControls === "boolean", "operatorControls missing");
    assert(Object.keys(body).every(key => ["apiUrl", "operatorControls"].includes(key)), `unexpected keys ${Object.keys(body)}`);
    config = body;
    return `apiUrl=${body.apiUrl}, operatorControls=${body.operatorControls}`;
  });
  if (!config) return;
  const api = `${config.apiUrl.replace(/\/+$/, "")}/api/v1`;
  const wsUrl = new URL("/ws/live", config.apiUrl).toString().replace(/^http/, "ws");

  let status, network;
  await check("GET /system/status (with thresholds)", async () => {
    ({ body: status } = await getJson(`${api}/system/status`));
    for (const key of ["high_temperature_c", "critical_temperature_c", "recovery_temperature_c", "high_humidity_percent", "vibration_score"])
      assert(typeof status.thresholds?.[key] === "number", `thresholds.${key} missing`);
    return `db=${status.spacetimedb_status}, gemini=${status.gemini_status}, model=${status.anomaly_model_status}, mode=${status.operating_mode}`;
  });
  await check("GET /network/overview (facilities with devices + latest reading)", async () => {
    ({ body: network } = await getJson(`${api}/network/overview`));
    assert(Array.isArray(network.facilities) && network.facilities.length > 0, "no facilities");
    for (const facility of network.facilities) {
      assert(typeof facility.id === "string" && typeof facility.is_simulated === "boolean", "facility shape");
      assert(Array.isArray(facility.devices) && Array.isArray(facility.active_incidents), `${facility.id} missing devices/active_incidents`);
    }
    return network.facilities.map(item => `${item.id}:${item.status}`).join(", ");
  });
  for (const [path, key] of [["/incidents", "incidents"], ["/decisions", "decisions"], ["/commands?limit=50", "commands"], ["/events?limit=50", "events"]]) {
    await check(`GET ${path}`, async () => {
      const { response, body } = await getJson(`${api}${path}`);
      assert(response.ok && Array.isArray(body[key]), `expected ${key}[]`);
      if (key === "events") assert(body.events.every(event => event.type !== "telemetry.reading"), "raw telemetry leaked into activity feed");
      return `${body[key].length} ${key}`;
    });
  }
  await check("GET /sensors/anomaly/latest", async () => {
    const { body } = await getJson(`${api}/sensors/anomaly/latest`);
    assert(isObject(body.anomalies), "anomalies not an object");
    return `${Object.keys(body.anomalies).length} facilities scored`;
  });
  const withData = network?.facilities.find(item => item.latest_reading);
  if (withData) await check(`GET /facilities/${withData.id}/history`, async () => {
    const { body } = await getJson(`${api}/facilities/${withData.id}/history?limit=900`);
    assert(Array.isArray(body.readings) && body.readings.length > 0, "no readings");
    const sources = new Set(body.readings.map(reading => reading.is_simulated ? "simulated" : "physical"));
    return `${body.readings.length} readings (${[...sources].join("+")})`;
  });
  await check("CORS allows the frontend origin", async () => {
    const { response } = await getJson(`${api}/system/status`, { headers: { Origin: FRONTEND } });
    const allowed = response.headers.get("access-control-allow-origin");
    assert(allowed === FRONTEND, `Access-Control-Allow-Origin=${allowed} (add ${FRONTEND} to backend CORS_ORIGINS)`);
    return allowed;
  });
  for (const page of ["/", "/overview", "/facility", "/incidents", "/incidents/does-not-exist"]) {
    await check(`frontend page ${page} renders`, async () => {
      const response = await fetch(`${FRONTEND}${page}`, { signal: AbortSignal.timeout(15_000) });
      assert(response.ok, `status ${response.status}`);
    });
  }
  await check("operator proxy rejects cross-origin and unsupported requests", async () => {
    const cross = await fetch(`${FRONTEND}/api/operator/commands`, { method: "POST", headers: { Origin: "https://attacker.example", "Content-Type": "application/json" }, body: "{}" });
    const unsupported = await fetch(`${FRONTEND}/api/operator/system/mode`, { method: "POST", headers: { Origin: FRONTEND }, body: "{}" });
    assert(cross.status === 403 || cross.status === 503, `cross-origin → ${cross.status}`);
    assert(unsupported.status === 404 || unsupported.status === 503, `unsupported path → ${unsupported.status}`);
    return `cross-origin → ${cross.status}, unsupported → ${unsupported.status}`;
  });

  const stream = openStream(wsUrl);
  await check("WebSocket /ws/live connects and streams readings", async () => {
    await stream.opened;
    const event = await stream.waitFor(event => event.type === "telemetry.reading", 15_000, "telemetry.reading");
    assert(typeof event.data.facility_id === "string" && typeof event.data.temperature_c === "number", "reading shape");
    assert(isObject(event.data.anomaly), "reading is missing streamed anomaly result");
    return `${event.data.facility_id} ${event.data.temperature_c.toFixed(1)} °C (${event.data.is_simulated ? "simulated" : "physical"})`;
  });

  const simulated = network?.facilities.find(item => item.is_simulated);
  if (SKIP_WORKFLOW) record("SKIP", "overheating → recovery workflow", "--skip-workflow");
  else if (!config.operatorControls) record("SKIP", "overheating → recovery workflow", "operator controls disabled (SENTINEL_OPERATOR_KEY unset)");
  else if (!simulated) record("SKIP", "overheating → recovery workflow", "no simulated facility (SIMULATION_ENABLED=false)");
  else {
    const isTemperature = incident => incident.facility_id === simulated.id && /TEMPERATURE/.test(incident.incident_type);
    const activeTemperature = async () => (await getJson(`${api}/incidents`)).body.incidents.find(item => isTemperature(item) && ["OPEN", "RESPONDING"].includes(item.status));
    let incident;
    await check(`overheating scenario creates incident (${simulated.id})`, async () => {
      const existing = await activeTemperature();
      if (existing) {
        await operator(`facilities/${simulated.id}/simulation/trigger`, { scenario: "normal" });
        await stream.waitFor(event => event.type === "incident.recovered" && event.data.id === existing.id, 90_000, "pre-existing incident to recover");
      }
      const trigger = await operator(`facilities/${simulated.id}/simulation/trigger`, { scenario: "overheating" });
      assert(trigger.response.ok, `trigger → ${trigger.response.status} ${trigger.text}`);
      const created = await stream.waitFor(event => event.type === "incident.created" && isTemperature(event.data), 20_000, "incident.created");
      incident = created.data;
      return `#${incident.id.slice(0, 8)} ${incident.incident_type} — ${incident.description}`;
    });
    if (incident) {
      await check("incident detail has rule decision and no physical command (simulated)", async () => {
        const { body } = await getJson(`${api}/incidents/${incident.id}`);
        assert(body.decisions.some(decision => decision.decision_source === "RULES"), "no RULES decision");
        assert(body.hardware_commands.length === 0, "simulated facility queued a hardware command");
        return `${body.decisions.length} decisions, 0 hardware commands`;
      });
      await check("operator acknowledgment through the frontend proxy", async () => {
        const { response, body, text } = await operator(`incidents/${incident.id}/acknowledge`, { note: "integration check" });
        assert(response.ok, `${response.status} ${text}`);
        assert(body.incident.acknowledged_at, "acknowledged_at not set");
        assert(["OPEN", "RESPONDING"].includes(body.incident.status), `status changed to ${body.incident.status}`);
        await stream.waitFor(event => event.type === "incident.updated" && event.data.id === incident.id, 10_000, "incident.updated");
        return `acknowledged at ${body.incident.acknowledged_at}; status still ${body.incident.status}`;
      });
      await check("recovery is verified from sensor readings after returning to normal", async () => {
        await operator(`facilities/${simulated.id}/simulation/trigger`, { scenario: "normal" });
        const recovered = await stream.waitFor(event => event.type === "incident.recovered" && event.data.id === incident.id, 90_000, "incident.recovered");
        const { body } = await getJson(`${api}/incidents/${incident.id}`);
        assert(body.status === "RESOLVED" && body.resolved_at, `status ${body.status}`);
        const seconds = Math.round((new Date(body.resolved_at) - new Date(body.detected_at)) / 1000);
        return `resolved after ${seconds}s (${recovered.data.verification_data.length} verification entries)`;
      });
    }
  }
  stream.socket.close();
  console.log(`\n${results.filter(item => item.status === "PASS").length} passed, ${failed} failed, ${results.filter(item => item.status === "SKIP").length} skipped`);
  process.exitCode = failed ? 1 : 0;
}

main().catch(error => { console.error(error); process.exitCode = 1; });
