// A plain anchor is enough here — the browser handles the navigation to
// /api/auth/start, no client-side state or interactivity involved, so this
// deliberately does NOT need 'use client' (Decision 6: scope client
// components to genuinely interactive leaves, not "any button").
export function LoginButton({ nextPath }: { nextPath: string }) {
  return (
    <a
      href={`/api/auth/start?next=${encodeURIComponent(nextPath)}`}
      className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
    >
      Sign in with Discord
    </a>
  );
}
