import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/config";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const fetchSite = request.headers.get("sec-fetch-site");
  const origin = request.headers.get("origin");
  const crossSite = Boolean(fetchSite && fetchSite !== "same-origin" && fetchSite !== "none");
  let wrongOrigin = false;
  if (origin) {
    try {
      wrongOrigin = new URL(origin).origin !== request.nextUrl.origin;
    } catch {
      wrongOrigin = true;
    }
  }
  if (crossSite || wrongOrigin || (!origin && !fetchSite)) {
    return NextResponse.json({ detail: "Cross-site request blocked" }, { status: 403 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
