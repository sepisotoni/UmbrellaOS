import { NextRequest, NextResponse } from "next/server";

const BASE_URL = process.env.UMBRELLA_CORE_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { text, target_language, token } = (await req.json()) as {
    text: string;
    target_language: string;
    token: string;
  };
  try {
    const res = await fetch(`${BASE_URL}/api/v1/translation/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ text, target_language }),
      cache: "no-store",
    });
    const data = await res.json();
    if (!res.ok) return NextResponse.json({ error: JSON.stringify(data) }, { status: res.status });
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Unknown error" },
      { status: 500 }
    );
  }
}
