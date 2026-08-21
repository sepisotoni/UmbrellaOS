import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { Sidebar } from "@/components/nav/sidebar";
import { Topbar } from "@/components/nav/topbar";
import { CommandPalette } from "@/components/command-palette/command-palette";

// The real auth boundary (middleware.ts only checks cookie presence).
// This is a server component: the /auth/me round trip happens once per
// navigation on the server, and the resolved role/permissions are real —
// straight from services/roles_service.py's role ladder, nothing
// hardcoded here.
export default async function DashboardShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  return (
    <div className="flex min-h-screen">
      <Sidebar permissions={session.user.permissions} token={session.token} />
      <div className="flex flex-1 flex-col">
        <Topbar user={session.user} />
        <main className="flex-1 p-6">{children}</main>
      </div>
      {/* Mounted once for the whole authenticated shell, not per-page — it
          reads its own query results from same-origin /api/search, so it
          doesn't need the session token passed in as a prop. */}
      <CommandPalette />
    </div>
  );
}
