// middleware.ts — runs on the Edge runtime, so it can only check for the
// session cookie's presence (no fetch to umbrella-core, no permission
// resolution — that needs the real /auth/me round trip, which happens in
// app/(dashboard)/layout.tsx, a server component, not here). This is a
// fast bounce for the common "no cookie at all" case; it is not the real
// auth boundary, the layout is.

import { NextRequest, NextResponse } from "next/server";

// Deliberately not importing SESSION_COOKIE from lib/session.ts here: that
// file pulls in next/headers + the server-only package, which belong in
// the Node/RSC runtime (the layout's real auth check), not the Edge
// runtime this middleware runs in. Same literal value, kept in sync by
// hand — small enough surface that a shared import isn't worth the
// runtime coupling.
const SESSION_COOKIE = "umbrella_session";

const PROTECTED_PREFIXES = ["/dashboard", "/marketplace", "/topology"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (!isProtected) return NextResponse.next();

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/marketplace/:path*", "/topology/:path*"],
};
