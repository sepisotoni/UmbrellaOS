// app/api/marketplace-install/route.ts — same-origin route the client
// MarketplaceInstallButton leaf calls. Same reasoning as
// app/api/plugin-config/route.ts and app/api/dashboard-layout/route.ts:
// the browser never talks to umbrella-core directly or holds the bearer
// token, this route reads the httpOnly session cookie server-side and
// forwards the actual capability call.
//
// Unlike plugin-config's route, both verbs here (POST install, DELETE
// uninstall) hit real destructive: true capabilities server-side
// (marketplace.install.install / marketplace.install.uninstall —
// capabilities/marketplace.py) — this route doesn't add a second
// authorization boundary, `marketplace.install.manage` is already
// enforced on every call by the registry itself, same as Tier 2's
// plugin.<id>.config.set is. This route only keeps the bearer token off
// the client and turns the backend's real error shape into one the leaf
// component can branch on (403 forbidden vs. 404 not-found/version vs.
// generic failure).
import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { installPlugin, uninstallPlugin } from "@/lib/marketplace-listings";
import { ApiError } from "@/lib/api";

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = (await request.json()) as { plugin_id?: string; version?: string };
  if (!body.plugin_id || !body.version) {
    return NextResponse.json(
      { error: "plugin_id and version are required" },
      { status: 400 }
    );
  }

  try {
    const install = await installPlugin(body.plugin_id, body.version, session.token);
    return NextResponse.json({ install });
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    if (err instanceof ApiError && err.status === 404) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    if (err instanceof ApiError && err.status === 409) {
      return NextResponse.json({ error: "conflict" }, { status: 409 });
    }
    return NextResponse.json({ error: "failed to install plugin" }, { status: 502 });
  }
}

export async function DELETE(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const pluginId = request.nextUrl.searchParams.get("plugin_id");
  if (!pluginId) {
    return NextResponse.json({ error: "plugin_id is required" }, { status: 400 });
  }

  try {
    await uninstallPlugin(pluginId, session.token);
    return NextResponse.json({ uninstalled: true });
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    if (err instanceof ApiError && err.status === 404) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    return NextResponse.json({ error: "failed to uninstall plugin" }, { status: 502 });
  }
}
