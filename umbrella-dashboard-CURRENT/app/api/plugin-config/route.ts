// app/api/plugin-config/route.ts — same-origin route the client
// PluginConfigToggle leaf calls. Same reasoning as
// app/api/dashboard-layout/route.ts: the browser never talks to
// umbrella-core directly or holds the bearer token, this route reads the
// httpOnly session cookie server-side and forwards the actual capability
// call to `plugin.<plugin_id>.config.set`.
//
// Tier 2's write path is already platform-owned server-side
// (services/plugins/registration.py's _make_config_set_handler docstring)
// — this route doesn't add a second authorization boundary, it just keeps
// the bearer token off the client, identically to every other write path
// in this app.
import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { setPluginConfigValue } from "@/lib/plugin-config";
import { ApiError } from "@/lib/api";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = (await request.json()) as {
    plugin_id?: string;
    key?: string;
    value?: boolean;
  };
  if (!body.plugin_id || !body.key || typeof body.value !== "boolean") {
    return NextResponse.json(
      { error: "plugin_id, key, and a boolean value are required" },
      { status: 400 }
    );
  }

  try {
    await setPluginConfigValue(body.plugin_id, body.key, body.value, session.token);
    return NextResponse.json({ saved: true });
  } catch (err) {
    // Distinguish "the backend itself rejected this for permissions" (a
    // real 403 from plugin.<id>.config.set — see
    // services/plugins/registration.py) from a network/backend-down
    // failure, so PluginConfigToggle can tell the user which one
    // happened instead of one generic "save failed."
    if (err instanceof ApiError && err.status === 403) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    return NextResponse.json({ error: "failed to save config" }, { status: 502 });
  }
}
