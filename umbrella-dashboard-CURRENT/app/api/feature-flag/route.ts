import { NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { name, enabled, token } = (await req.json()) as {
    name: string;
    enabled: boolean;
    token: string;
  };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/feature-flags`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ name, enabled }),
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

export async function DELETE(req: NextRequest) {
  const { name, token } = (await req.json()) as { name: string; token: string };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/feature-flags/${encodeURIComponent(name)}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
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
