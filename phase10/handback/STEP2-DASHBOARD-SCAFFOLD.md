# Step 2 — Dashboard scaffold: manifest & handback

New `umbrella-dashboard/` app, Next.js 16, built from scratch per the
kickoff doc (not extended from `reference/umbrella-dashboard-OLD-REFERENCE-ONLY.zip`,
which was read only to confirm what NOT to repeat — nothing copied forward).

## What's in this step

Full file list (`find . -not -path './node_modules/*'`):

```
.env.example
app/(dashboard)/dashboard/page.tsx
app/(dashboard)/layout.tsx
app/(dashboard)/marketplace/[pluginId]/page.tsx
app/(dashboard)/marketplace/page.tsx
app/api/auth/callback/route.ts
app/api/auth/logout/route.ts
app/api/auth/start/route.ts
app/globals.css
app/layout.tsx
app/login/login-button.tsx
app/login/page.tsx
app/page.tsx
components/nav/sidebar.tsx
components/nav/topbar.tsx
components/nav/user-menu.tsx
lib/api.ts
lib/nav-config.ts
lib/session.ts
lib/types.ts
middleware.ts
next.config.ts
package.json
postcss.config.mjs
tsconfig.json
```

No page content beyond placeholders per the kickoff doc's step 2 scope
("no page content yet"). `app/(dashboard)/dashboard/page.tsx` and the two
`app/(dashboard)/marketplace/...` routes are stubs that exist only to
reserve the locked route names (Decisions 4 & 5) and confirm the shell
renders around them — actual Tier 1/3 content is steps 3 and 7.

## How each locked decision maps into this scaffold

- **Decision 4** (`app/marketplace`, not `app/plugins`): route created at
  `app/(dashboard)/marketplace/page.tsx`; nothing at `app/plugins`.
- **Decision 5** (one generic dynamic route for Tier 3): only
  `app/(dashboard)/marketplace/[pluginId]/page.tsx` exists — no
  per-plugin file, by construction.
- **Decision 6** (`'use client'` scoped to leaf interactive components):
  the only two client components in the whole tree are
  `components/nav/user-menu.tsx` (dropdown open/close state) and nothing
  else — `login-button.tsx` is deliberately a plain server-rendered
  anchor, not a client component, since a link needs no client JS.
  Everything else (layouts, sidebar, topbar, all three route handlers) is
  a server component / server-only module.
- **Auth wired to the real RBAC role ladder**: `lib/session.ts` never
  hardcodes a role→permission mapping. It calls the real
  `GET /api/v1/auth/me` on every protected navigation and reads
  `user.permissions` (already resolved server-side from
  `services/roles_service.py`'s role+extra_permissions union). Nav
  filtering (`lib/nav-config.ts`) is permission-key-based, matching the
  keys in `DEFAULT_PERMISSIONS` (currently only `marketplace.install.view`
  is used, gating the one nav item beyond the always-visible Dashboard
  link — more items get added here as later steps add pages, not
  restructured).
- **`middleware.ts`** is a fast, Edge-runtime cookie-presence check only —
  intentionally not the real auth boundary, since Edge middleware can't
  do the real `/auth/me` round trip cleanly alongside `next/headers` +
  `server-only`. The real check is `app/(dashboard)/layout.tsx`, a server
  component, which is where an unauthenticated or session-revoked request
  actually gets redirected to `/login`.
- **OAuth flow** (`app/api/auth/start`, `/callback`, `/logout`) drives the
  existing `api/routers/auth.py` Discord OAuth endpoints exactly as they
  exist today — no changes requested or made to the backend auth flow.
  `state` and the post-login `next` path round-trip through short-lived
  httpOnly cookies (Discord's own redirect back only carries `?code` and
  `?state`, nothing else); the real session token is stored httpOnly and
  is the *only* dashboard auth cookie.

## What is NOT independently verified, and why

The kickoff doc's discipline is "fresh venv/fresh `npm ci`, real test run,
not trusting the build session's self-report" for every step. Step 0 met
that bar (real pytest run, 790/790, plus a live capability-invoke script).
**Step 2 does not, and can't in this sandbox: this environment has no
network access** — `npm view next version` against the public registry
returns a hard 403, confirmed before writing any dashboard code. So
`npm ci` / `next build` / `next lint` have not been run against this
scaffold. Everything here is hand-written against Next.js 16 / React 19
App Router conventions I'm confident in, but "confident" is not the same
bar as "confirmed" — flagging that gap explicitly rather than reporting
a green build that didn't happen.

**Before this step is treated as done, in an environment with registry
access:**
1. `npm ci`
2. `npm run build` (catches the App Router route-group/dynamic-route
   wiring, the `cookies()`/`headers()` async API usage, and any
   `next/server`↔Edge-runtime import issues in `middleware.ts`)
3. `npm run lint`

If any of those surface issues, they're scaffold bugs to fix in this same
step, not something to carry into step 3.

## Explicitly declined during this step

Asked whether to route the "can't run `npm ci` here" problem through
v0.dev or similar external tooling instead. **Declined** — the kickoff
doc states this as a closed constraint ("Confirmed constraint: no v0 or
external mockup tooling. Build directly against the real backend"), and
the reasoning behind it (real capability registry / real RBAC / real API
shapes, not a mockup tool's guess) applies just as much to "compile this
for me" as to "generate this UI for me." The npm-registry gap is a sandbox
environment limitation, not a design decision to work around — it gets
closed by running the three commands above somewhere with registry
access, not by substituting a different tool for the build step itself.
