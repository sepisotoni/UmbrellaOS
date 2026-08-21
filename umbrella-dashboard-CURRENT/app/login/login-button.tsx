// A plain anchor is enough here — the browser handles the navigation to
// /api/auth/start, no client-side state or interactivity involved, so this
// deliberately does NOT need 'use client' (Decision 6: scope client
// components to genuinely interactive leaves, not "any button").
export function LoginButton({ nextPath }: { nextPath: string }) {
  return (
    <a
      href={`/api/auth/start?next=${encodeURIComponent(nextPath)}`}
      className="rounded-md bg-[#251653] px-4 py-2 text-sm font-medium text-[#f3efff] transition-colors hover:bg-[#32206d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8b5cf6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#070914]"
    >
      Sign in with Discord
    </a>
  );
}
