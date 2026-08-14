import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, SESSION_COOKIE, SESSION_MAX_AGE_SECONDS } from "@/lib/config";

type Context = { params: Promise<{ path: string[] }> };

function isAuthExchange(path: string[]): boolean {
  return path.length === 2 && path[0] === "auth" && (path[1] === "login" || path[1] === "register");
}

async function forward(request: NextRequest, context: Context): Promise<NextResponse> {
  const { path } = await context.params;
  const upstream = new URL(`/api/v1/${path.join("/")}`, API_BASE_URL);
  upstream.search = request.nextUrl.search;

  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  const headers = new Headers();
  headers.set("Accept", "application/json");
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const canHaveBody = !["GET", "HEAD"].includes(request.method);
  const body = canHaveBody ? await request.arrayBuffer() : undefined;
  const response = await fetch(upstream, {
    method: request.method,
    headers,
    body: body && body.byteLength > 0 ? body : undefined,
    cache: "no-store"
  });

  if (response.status === 204) return new NextResponse(null, { status: 204 });

  const payload = (await response.json().catch(() => ({ detail: "Invalid API response" }))) as Record<string, unknown>;

  if (isAuthExchange(path) && response.ok && typeof payload.access_token === "string") {
    const result = NextResponse.json({ user: payload.user }, { status: response.status });
    result.cookies.set(SESSION_COOKIE, payload.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: SESSION_MAX_AGE_SECONDS
    });
    return result;
  }

  return NextResponse.json(payload, { status: response.status });
}

export function GET(request: NextRequest, context: Context) {
  return forward(request, context);
}
export function POST(request: NextRequest, context: Context) {
  return forward(request, context);
}
export function PUT(request: NextRequest, context: Context) {
  return forward(request, context);
}
export function PATCH(request: NextRequest, context: Context) {
  return forward(request, context);
}
export function DELETE(request: NextRequest, context: Context) {
  return forward(request, context);
}
