import { NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { discord_id, action, role_id, token } = (await req.json()) as {
    discord_id: string;
    action: "promote" | "demote" | "add";
    role_id: string;
    token: string;
  };

  const path =
    action === "add" ? "/api/v1/staff/add" : "/api/v1/staff/manage";

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ discord_id, action, role_id }),
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
