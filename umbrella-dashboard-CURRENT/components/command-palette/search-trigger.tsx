"use client";

// A click affordance for people who don't know the Cmd+K shortcut yet —
// dispatches the same custom event command-palette.tsx listens for, no
// shared state/context needed between these two independently-mounted
// leaves.
export function SearchTrigger() {
  return (
    <button
      onClick={() => window.dispatchEvent(new Event("umbrella:open-command-palette"))}
      className="flex items-center gap-2 rounded-md border border-[var(--border)] px-3 py-1.5 text-xs opacity-60 hover:opacity-100"
    >
      <span>Search…</span>
      <kbd className="rounded bg-white/10 px-1">⌘K</kbd>
    </button>
  );
}
