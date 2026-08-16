// app/api/search/route.ts — same-origin route the client command palette
// calls. Keeps the session token server-side the same way every other
// backend call in this app does (lib/api.ts) — the browser only ever
// talks to this route, never to umbrella-core directly, so the bearer
// token never has to exist in client-side JS.
import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { runFederatedSearch } from "@/lib/search";

export async function GET(request: NextRequest) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ results: [] }, { status: 401 });
  }

  const query = request.nextUrl.searchParams.get("q") ?? "";
  const results = await runFederatedSearch(query, session.user, session.token);
  return NextResponse.json({ results });
}
