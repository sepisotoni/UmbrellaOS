import { NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { player_uuid, event_ids, token } = (await req.json()) as {
    player_uuid: string;
    event_ids: string[];
    token: string;
  };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/alts/false-positive`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ player_uuid, event_ids }),
      cache: "no-store",
    });
    const text = await res.text();
    if (!res.ok) return NextResponse.json({ error: text }, { status: res.status });
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
