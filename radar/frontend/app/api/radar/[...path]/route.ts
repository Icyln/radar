import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import {
  API_BASE_URL,
  BFF_MAX_REQUEST_BYTES,
  BFF_UPSTREAM_TIMEOUT_MS,
  BFF_WIDE_SEARCH_TIMEOUT_MS,
  SESSION_COOKIE,
  SESSION_MAX_AGE_SECONDS
} from "@/lib/config";

type Context = { params: Promise<{ path: string[] }> };

function isAuthExchange(path: string[]): boolean {
  return path.length === 2 && path[0] === "auth" && (path[1] === "login" || path[1] === "register");
}

function isSafeMethod(method: string): boolean {
  return method === "GET" || method === "HEAD" || method === "OPTIONS";
}

function sameOriginRequest(request: NextRequest): boolean {
  if (isSafeMethod(request.method)) return true;

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;

  const origin = request.headers.get("origin");
  if (origin) {
    try {
      return new URL(origin).origin === request.nextUrl.origin;
    } catch {
      return false;
    }
  }

  return fetchSite === "same-origin" || fetchSite === "none";
}

function jsonError(detail: string, status: number, requestId: string): NextResponse {
  const response = NextResponse.json({ detail }, { status });
  response.headers.set("X-Request-ID", requestId);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

async function forward(request: NextRequest, context: Context): Promise<NextResponse> {
  const requestId = request.headers.get("x-request-id")?.slice(0, 128) || randomUUID();

  if (!sameOriginRequest(request)) return jsonError("Cross-site request blocked", 403, requestId);

  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(contentLength) && contentLength > BFF_MAX_REQUEST_BYTES) {
    return jsonError("Request body is too large", 413, requestId);
  }

  const { path } = await context.params;
  if (!path.length || path.some((part) => !part || part === "." || part === "..")) {
    return jsonError("Invalid API path", 400, requestId);
  }

  const encodedPath = path.map(encodeURIComponent).join("/");
  const upstreamPath = path.length === 1 && (path[0] === "health" || path[0] === "ready")
    ? `/${encodedPath}`
    : `/api/v1/${encodedPath}`;
  const upstream = new URL(upstreamPath, API_BASE_URL);
  upstream.search = request.nextUrl.search;

  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  const headers = new Headers();
  headers.set("Accept", "application/json");
  headers.set("X-Request-ID", requestId);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const canHaveBody = !isSafeMethod(request.method);
  const body = canHaveBody ? await request.arrayBuffer() : undefined;
  if (body && body.byteLength > BFF_MAX_REQUEST_BYTES) return jsonError("Request body is too large", 413, requestId);

  let response: Response;
  try {
    const isWideRefresh = path.join("/") === "discovery/wide-search/refresh";
    response = await fetch(upstream, {
      method: request.method,
      headers,
      body: body && body.byteLength > 0 ? body : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(isWideRefresh ? BFF_WIDE_SEARCH_TIMEOUT_MS : BFF_UPSTREAM_TIMEOUT_MS)
    });
  } catch (error) {
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    const cause = error instanceof Error && error.cause && typeof error.cause === "object"
      ? error.cause as { code?: string }
      : undefined;
    const code = cause?.code;

    console.error(`[Radar BFF] ${requestId} ${request.method} ${upstream.toString()} failed`, error);

    if (process.env.NODE_ENV !== "production") {
      const hint = timedOut
        ? `Radar API timed out at ${API_BASE_URL}.`
        : `Cannot reach Radar API at ${API_BASE_URL}${code ? ` (${code})` : ""}. Make sure uvicorn is running on port 8000, or set RADAR_API_URL in frontend/.env.local.`;
      return jsonError(hint, timedOut ? 504 : 502, requestId);
    }

    return jsonError(timedOut ? "Radar API timed out" : "Radar API is unavailable", timedOut ? 504 : 502, requestId);
  }

  if (response.status === 204) {
    const result = new NextResponse(null, { status: 204 });
    result.headers.set("X-Request-ID", response.headers.get("x-request-id") || requestId);
    result.headers.set("Cache-Control", "no-store");
    return result;
  }

  const payload = (await response.json().catch(() => ({ detail: "Radar API returned an invalid response" }))) as Record<string, unknown>;

  if (isAuthExchange(path) && response.ok && typeof payload.access_token === "string") {
    const result = NextResponse.json({ user: payload.user }, { status: response.status });
    result.cookies.set(SESSION_COOKIE, payload.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: SESSION_MAX_AGE_SECONDS
    });
    result.headers.set("X-Request-ID", response.headers.get("x-request-id") || requestId);
    result.headers.set("Cache-Control", "no-store");
    return result;
  }

  const result = NextResponse.json(payload, { status: response.status });
  result.headers.set("X-Request-ID", response.headers.get("x-request-id") || requestId);
  result.headers.set("Cache-Control", "no-store");
  return result;
}

export function GET(request: NextRequest, context: Context) { return forward(request, context); }
export function POST(request: NextRequest, context: Context) { return forward(request, context); }
export function PUT(request: NextRequest, context: Context) { return forward(request, context); }
export function PATCH(request: NextRequest, context: Context) { return forward(request, context); }
export function DELETE(request: NextRequest, context: Context) { return forward(request, context); }
