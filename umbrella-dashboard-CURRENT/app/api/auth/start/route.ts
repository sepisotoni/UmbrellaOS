// app/api/auth/start/route.ts — GET /api/auth/start?next=/dashboard
//
// Calls umbrella-core's POST /api/v1/auth/discord/authorize to mint a
// `state` + get the real Discord authorize URL, stashes `state` and the
// post-login `next` path in a short-lived cookie (so /api/auth/callback
// can recover them — Discord's redirect back doesn't round-trip anything
// but ?code and ?state), then 302s the browser to Discord.
import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/api";

const REDIRECT_URI =
  process.env.DASHBOARD_OAUTH_REDIRECT_URI ?? "http://localhost:3000/api/auth/callback";

export async function GET(request: NextRequest) {
  const next = request.nextUrl.searchParams.get("next") ?? "/dashboard";

  const { authorize_url, state } = await backend.post<{
    authorize_url: string;
    state: string;
  }>("/api/v1/auth/discord/authorize", { redirect_uri: REDIRECT_URI });

  const res = NextResponse.redirect(authorize_url);
  res.cookies.set("umbrella_oauth_state", state, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
  });
  res.cookies.set("umbrella_oauth_next", next, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 600,
    path: "/",
  });
  return res;
}
