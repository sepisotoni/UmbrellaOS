import { NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { id, status, staff_notes, token } = (await req.json()) as {
    id: string;
    status: string;
    staff_notes: string;
    token: string;
  };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/appeals/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status, staff_notes }),
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
