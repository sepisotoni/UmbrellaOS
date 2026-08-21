import { redirect } from "next/navigation";
import { LogOut, ShieldAlert } from "lucide-react";
import { getSession } from "@/lib/session";

export default async function AccessDeniedPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const initials = session.user.username.slice(0, 2).toUpperCase();

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#070914] px-4 text-[#eef0ff]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(92,59,180,0.18),transparent_34%)]" />
      <section className="relative w-full max-w-[430px] rounded-[10px] border border-[#27304f] bg-[#070914]/95 px-8 py-9 text-center shadow-[0_24px_80px_rgba(0,0,0,0.38)]">
        <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-[#4a2e68] bg-[#21133c] text-[#c084fc]"><ShieldAlert className="size-6" /></div>
        <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#a78bfa]">UmbrellaOS</p>
        <h1 className="mt-2 text-[24px] font-semibold tracking-[-0.03em]">Access denied</h1>
        <p className="mx-auto mt-3 max-w-[310px] text-sm leading-6 text-[#a2a7b8]">Your account is authenticated, but it doesn’t have permission to view this area.</p>
        <div className="mt-7 flex items-center gap-3 rounded-lg border border-[#27304f] bg-[#0d1223] px-4 py-3 text-left">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#32206d] text-xs font-semibold text-white">{initials}</div>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-[#eef0ff]">{session.user.username}</p><p className="truncate text-xs text-[#8992b2]">{session.user.email ?? `Discord ID ${session.user.discord_id}`}</p></div>
          <span className="rounded-full border border-[#263d35] bg-[#10251b] px-2 py-1 text-[10px] font-medium text-[#86efac]">Signed in</span>
        </div>
        <form action="/api/auth/logout" method="post" className="mt-6"><button type="submit" className="inline-flex items-center gap-2 rounded-md bg-[#251653] px-4 py-2 text-sm font-medium text-[#f3efff] transition-colors hover:bg-[#32206d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8b5cf6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#070914]"><LogOut className="size-4" />Log out</button></form>
      </section>
    </main>
  );
}
