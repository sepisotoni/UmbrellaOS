// app/api/auth/logout/route.ts — POST-only (Next.js Router Handlers don't
// get CSRF protection for GET the way a same-origin POST-from-a-form does).
import { NextResponse } from "next/server";
import { backend } from "@/lib/api";
import { getSessionToken, SESSION_COOKIE } from "@/lib/session";

export async function POST(request: Request) {
  const token = await getSessionToken();
  if (token) {
    try {
      await backend.post(`/api/v1/auth/logout?session_token=${encodeURIComponent(token)}`, {});
    } catch {
      // Revoke is best-effort — the cookie clear below is what actually
      // matters for this browser; a dead token left behind server-side
      // expires on its own (SESSION_EXPIRY_DAYS).
    }
  }
  const res = NextResponse.redirect(new URL("/login", request.url));
  res.cookies.delete(SESSION_COOKIE);
  return res;
}
