// app/api/auth/callback/route.ts — Discord redirects here with ?code&state.
//
// Exchanges them via umbrella-core's POST /api/v1/auth/discord/callback
// (which validates `state` against the pending row it created in /authorize
// and returns the real session token — see api/routers/auth.py), then
// stores that token as the dashboard's own httpOnly session cookie. The
// token value is opaque to the dashboard; it's forwarded verbatim as a
// Bearer header on every subsequent server-side backend call
// (lib/api.ts / lib/session.ts).
import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { backend } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/session";
import type { Session } from "@/lib/types";

const REDIRECT_URI =
  process.env.DASHBOARD_OAUTH_REDIRECT_URI ?? "http://localhost:3000/api/auth/callback";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const store = await cookies();
  const expectedState = store.get("umbrella_oauth_state")?.value;
  const next = store.get("umbrella_oauth_next")?.value ?? "/dashboard";

  if (!code || !state || !expectedState || state !== expectedState) {
    return NextResponse.redirect(new URL("/login?error=oauth_state", request.url));
  }

  let session: Session;
  try {
    session = await backend.post<Session>("/api/v1/auth/discord/callback", {
      code,
      state,
      redirect_uri: REDIRECT_URI,
    });
  } catch {
    return NextResponse.redirect(new URL("/login?error=oauth_exchange", request.url));
  }

  const res = NextResponse.redirect(new URL(next, request.url));
  res.cookies.set(SESSION_COOKIE, session.token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: session.expires_in,
    path: "/",
  });
  res.cookies.delete("umbrella_oauth_state");
  res.cookies.delete("umbrella_oauth_next");
  return res;
}
