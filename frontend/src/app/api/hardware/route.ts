// Only the public, read-only hardware snapshot is proxied. Device and database
// credentials never belong in the browser or in this route.
export const dynamic = "force-dynamic";

export async function GET() {
  const base = (process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL ||
    (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "https://un1c0rn-2.onrender.com"))
    .trim().replace(/\/+$/, "");
  try {
    const response = await fetch(`${base}/api/v1/telemetry/hardware?limit=500`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) {
      return Response.json({ error: `Backend returned HTTP ${response.status}. Check the backend deployment.` },
        { status: 502, headers: { "Cache-Control": "no-store" } });
    }
    const data = await response.json();
    if (!Array.isArray(data.reports) || typeof data.connected !== "boolean" ||
        typeof data.device_timeout_seconds !== "number" || typeof data.checked_at !== "string") {
      throw new Error("Invalid hardware response");
    }
    return Response.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "Cannot reach the hardware backend. Check its URL and service status." },
      { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
