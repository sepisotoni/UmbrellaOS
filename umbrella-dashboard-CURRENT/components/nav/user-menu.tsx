"use client";

// The one genuinely interactive leaf in the shell (Decision 6): a dropdown
// toggle. Logout itself is a plain form POST to a route handler — no
// client-side fetch needed for that part, just the open/closed state.
import { useState } from "react";

export function UserMenu({ username, role }: { username: string; role: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm hover:bg-white/5"
      >
        <span>{username}</span>
        {role && <span className="rounded bg-white/10 px-1.5 py-0.5 text-xs">{role}</span>}
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-40 rounded-md border border-[var(--border)] bg-[var(--background)] p-1 shadow-lg">
          <form action="/api/auth/logout" method="post">
            <button
              type="submit"
              className="w-full rounded px-3 py-2 text-left text-sm hover:bg-white/5"
            >
              Sign out
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
