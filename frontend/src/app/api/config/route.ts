// Runtime configuration for the browser. Read from server-side environment
// variables on each request (not inlined at build time), so a single build can be
// deployed against any backend. Never returns secrets.
export const dynamic = "force-dynamic";

export function GET() {
  const apiUrl = process.env.SENTINEL_PUBLIC_API_URL?.trim() || null;
  return Response.json({
    apiUrl,
    operatorControls: Boolean(process.env.SENTINEL_OPERATOR_KEY?.trim()),
  }, { headers: { "Cache-Control": "no-store" } });
}
