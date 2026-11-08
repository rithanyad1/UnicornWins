import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { afterEach, test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/app/api/hardware/route.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { GET } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
const originalFetch = globalThis.fetch;
const originalEnv = { ...process.env };
afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const key of ["API_BASE_URL", "NEXT_PUBLIC_API_BASE_URL", "NODE_ENV"]) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
});

const snapshot = { reports: [], connected: false, device_timeout_seconds: 15, checked_at: new Date().toISOString() };

test("production default uses Render and does not forward credentials", async () => {
  delete process.env.API_BASE_URL;
  delete process.env.NEXT_PUBLIC_API_BASE_URL;
  process.env.NODE_ENV = "production";
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "https://un1c0rn-2.onrender.com/api/v1/telemetry/hardware?limit=500");
    assert.equal(options.cache, "no-store");
    assert.equal(options.headers, undefined);
    return Response.json(snapshot);
  };
  const response = await GET();
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(await response.json(), snapshot);
});

test("server environment overrides the old public setting", async () => {
  process.env.API_BASE_URL = "https://configured.example/";
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
  globalThis.fetch = async url => {
    assert.equal(url, "https://configured.example/api/v1/telemetry/hardware?limit=500");
    return Response.json(snapshot);
  };
  assert.equal((await GET()).status, 200);
});

test("upstream failure provides a diagnostic without exposing its body", async () => {
  globalThis.fetch = async () => new Response("private traceback", { status: 503 });
  const response = await GET();
  assert.equal(response.status, 502);
  assert.match((await response.json()).error, /HTTP 503/);
});

test("network errors and incompatible deployed API return a connection error", async () => {
  for (const fetch of [async () => { throw new Error("private internal address"); }, async () => Response.json({ status: "ok" })]) {
    globalThis.fetch = fetch;
    const response = await GET();
    assert.equal(response.status, 502);
    assert.match((await response.json()).error, /Cannot reach/);
  }
});
