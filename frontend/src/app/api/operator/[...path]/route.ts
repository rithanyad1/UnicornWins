// Same-origin proxy for operator actions.
//
// The FastAPI operator key (SENTINEL_OPERATOR_KEY) stays on the Next.js server and is
// attached here, so it is never sent to or stored in the browser. Only an allowlist of
// operator endpoints is forwarded; every request is still validated by the backend's
// safety rules. Disabled entirely unless SENTINEL_OPERATOR_KEY is configured.
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const ALLOWED = [
  /^incidents\/[\w-]+\/acknowledge$/,
  /^commands$/,
  /^facilities\/[\w-]+\/simulation\/trigger$/,
];
const MAX_BODY_BYTES = 4_096;
const TIMEOUT_MS = 10_000;

const json = (status: number, detail: string) => Response.json({ detail }, { status });

export async function POST(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const key = process.env.SENTINEL_OPERATOR_KEY?.trim();
  const backend = (process.env.SENTINEL_API_URL || process.env.SENTINEL_PUBLIC_API_URL || "").trim().replace(/\/+$/, "");
  if (!key || !backend) return json(503, "Operator controls are not configured on the frontend server");

  // Browser requests to this route must come from this site (basic CSRF protection).
  const origin = request.headers.get("origin");
  if (origin && origin !== request.nextUrl.origin) return json(403, "Cross-origin operator requests are not allowed");

  const { path } = await ctx.params;
  const target = path.join("/");
  if (!ALLOWED.some(pattern => pattern.test(target))) return json(404, "Unsupported operator action");

  const body = await request.text();
  if (body.length > MAX_BODY_BYTES) return json(413, "Request body too large");

  const headers: Record<string, string> = { "Content-Type": "application/json", "X-Operator-Key": key };
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey.slice(0, 200);

  try {
    const response = await fetch(`${backend}/api/v1/${target}`, {
      method: "POST", headers, body: body || "{}", cache: "no-store", signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return json(502, "Backend unreachable");
  }
}
