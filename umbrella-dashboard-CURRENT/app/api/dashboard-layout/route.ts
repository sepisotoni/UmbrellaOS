// app/api/dashboard-layout/route.ts — same-origin route the client
// DashboardCustomizer leaf calls. Same reasoning as app/api/search/route.ts
// (step 4): the browser never talks to umbrella-core directly or holds the
// bearer token, this route reads the httpOnly session cookie server-side
// and forwards the actual capability call.
import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { saveLayout, resetLayout } from "@/lib/dashboard-layout";
import type { LayoutWidgetEntry } from "@/lib/types";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = (await request.json()) as { page_id?: string; widgets?: LayoutWidgetEntry[] };
  if (!body.page_id || !Array.isArray(body.widgets)) {
    return NextResponse.json({ error: "page_id and widgets are required" }, { status: 400 });
  }

  try {
    await saveLayout(body.page_id, body.widgets, session.token);
    return NextResponse.json({ saved: true });
  } catch {
    return NextResponse.json({ error: "failed to save layout" }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const pageId = request.nextUrl.searchParams.get("page_id");
  if (!pageId) {
    return NextResponse.json({ error: "page_id is required" }, { status: 400 });
  }

  try {
    await resetLayout(pageId, session.token);
    return NextResponse.json({ reset: true });
  } catch {
    return NextResponse.json({ error: "failed to reset layout" }, { status: 502 });
  }
}
