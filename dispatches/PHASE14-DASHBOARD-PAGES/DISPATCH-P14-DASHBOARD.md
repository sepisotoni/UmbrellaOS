# DISPATCH: Phase 14 — Dashboard Pages & Wiring

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/` only — do NOT touch `umbrella-core-CURRENT/`
**Write PAT:** [WRITE_PAT — see head chat or project credentials]
**Read-only PAT:** [READ_ONLY_PAT — see head chat or project credentials]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip at dispatch time:** 5abbf95

---

## Context

Read these files before touching any code:
- `PHASE14-AUDIT.md` — the full gap analysis. This is your spec. Every decision in this dispatch comes from it.
- `umbrella-dashboard-CURRENT/lib/types.ts` — all TypeScript types
- `umbrella-dashboard-CURRENT/lib/api.ts` — the backend API client (how to call core)
- `umbrella-dashboard-CURRENT/middleware.ts` — route protection
- `umbrella-dashboard-CURRENT/app/(dashboard)/layout.tsx` — dashboard shell (nav, sidebar)
- `umbrella-core-CURRENT/api/routers/` — all core endpoints (read-only reference)

The dashboard is a **Next.js App Router** project. Server components by default. Client components must have `"use client"` at the top. All backend calls in server components use the `backend` client from `lib/api.ts` which reads `UMBRELLA_CORE_API_URL` server-side. Never use `NEXT_PUBLIC_` prefixed env vars.

Styling: dark navy/purple theme. Match the existing pages exactly — same card styles, same color tokens, same shadcn/ui components. Look at `app/(dashboard)/activity/page.tsx` and `app/(dashboard)/fleet/page.tsx` for the established pattern.

---

## Tasks

### Task 1 — Fix `next.config.mjs` (do this first)

Remove `typescript: { ignoreBuildErrors: true }`. The build must pass with real type checking. Fix any type errors that surface.

---

### Task 2 — Fix `middleware.ts`

Add the missing protected route prefixes. Current config only guards `/dashboard`, `/marketplace`, `/topology`. Add:
- `/activity`, `/fleet`, `/settings`, `/plugin-sandbox`
- `/players`, `/moderation`, `/appeals`, `/ai-tasks`
- `/staff`, `/analytics`, `/alt-detection`, `/security`
- `/feature-flags`, `/translation`, `/observability`, `/knowledge`
- `/access-denied`

---

### Task 3 — Players pages

**`app/(dashboard)/players/page.tsx`** — Players list
- Server component
- Calls `GET /api/v1/players?username=&limit=50` via `backend`
- Table: username, UUID (truncated), last seen, status
- Search input (client component) that filters by username query param
- Each row links to `/players/[uuid]`

**`app/(dashboard)/players/[uuid]/page.tsx`** — Player detail
- Server component, param is `uuid`
- Calls `GET /api/v1/players/{uuid}` via `backend`
- Shows: username, UUID, Discord link status, join date, punishments count
- Action buttons (client): Kick, Warn, Ban — open a modal/sheet, POST to:
  - Kick: `POST /api/v1/moderation/kick` body `{ player_uuid, reason }`
  - Warn: `POST /api/v1/moderation/warn` body `{ player_uuid, reason }`
  - Ban: `POST /api/v1/moderation/ban` body `{ player_uuid, reason, expires_at? }`
- Shows active punishments from `GET /api/v1/moderation/active/{uuid}`
- "Trigger AI Review" button: `POST /api/v1/ai/review/player/{uuid}`

---

### Task 4 — Moderation & Punishments page

**`app/(dashboard)/moderation/page.tsx`**
- Tabs: "Punishments" | "Active Bans"
- Punishments: `GET /api/v1/punishments` — table with player, type, reason, staff, date, status, revoke button (`POST /api/v1/punishments/{id}/revoke`)
- Issue Punishment button: sheet form with player UUID, type (BAN/TEMP_BAN/KICK/WARN/MUTE), reason, optional expires_at — posts to `POST /api/v1/punishments`

---

### Task 5 — Appeals page

**`app/(dashboard)/appeals/page.tsx`**
- `GET /api/v1/appeals` — list of appeals
- Shows: player name, original punishment, appeal reason, submitted date, status
- Accept/Reject buttons: `PATCH /api/v1/appeals/{id}` body `{ status: "ACCEPTED" | "REJECTED", staff_notes: string }`
- "Trigger AI Review" per appeal: `POST /api/v1/ai/review/appeal/{id}`

---

### Task 6 — AI Tasks page

**`app/(dashboard)/ai-tasks/page.tsx`**
- `GET /api/v1/ai/tasks` — pending AI review queue
- Shows: type, target, AI recommendation, confidence, created date
- Approve: `POST /api/v1/ai/tasks/{id}/approve`
- Deny: `POST /api/v1/ai/tasks/{id}/deny`
- Second section — Pending AI config requests: `GET /api/v1/ai/config/pending`
- Approve/reject: `POST /api/v1/ai/config/{id}/approve` or `/reject`

---

### Task 7 — Staff Management page

**`app/(dashboard)/staff/page.tsx`**
- `GET /api/v1/staff/discord-members` — Discord server members
- Table: username, Discord ID, current role, actions
- Promote/demote: `POST /api/v1/staff/manage` body `{ discord_id, action: "promote"|"demote", role_id }`
- Add staff: `POST /api/v1/staff/add` body `{ discord_id, role_id }`
- Role options from `GET /api/v1/roles`

---

### Task 8 — Alt Detection page

**`app/(dashboard)/alt-detection/page.tsx`**
- `GET /api/v1/alts/flagged` — flagged players with suspicion scores
- `GET /api/v1/alts/groups` — known alt groups
- Flagged table: username, score, flags count, link to `/players/[uuid]`
- Alt groups: member UUIDs, confidence score
- Mark false positive: `POST /api/v1/alts/false-positive` body `{ player_uuid, event_ids }`

---

### Task 9 — Security Events page

**`app/(dashboard)/security/page.tsx`**
- `GET /api/v1/security/events`
- Table: timestamp, event type, actor, target, severity (color-coded badge)
- Client-side filter by severity

---

### Task 10 — Feature Flags page

**`app/(dashboard)/feature-flags/page.tsx`**
- `GET /api/v1/feature-flags` — all flags
- Each flag: name, enabled toggle (`POST /api/v1/feature-flags` body `{ name, enabled: bool }`), delete (`DELETE /api/v1/feature-flags/{name}`)
- Create new flag: name + enabled toggle form

---

### Task 11 — Translation page

**`app/(dashboard)/translation/page.tsx`**
- `GET /api/v1/translation/language/all` — all player language prefs
- Table: player UUID, detected language, confidence, last updated
- Manual translate: text input + `POST /api/v1/translation/translate` body `{ text, target_language }` → result inline

---

### Task 12 — Knowledge pages

**`app/(dashboard)/knowledge/page.tsx`** — Search input, invokes `knowledge.entry.search` capability
**`app/(dashboard)/knowledge/[id]/page.tsx`** — Entry viewer, fetches via `knowledge.entry.search` with `{ query: id, limit: 1 }`
- Shows: channel name, content, timestamp
- Makes command palette search links resolve

---

### Task 13 — Observability / Logs page

**`app/(dashboard)/observability/logs/page.tsx`**
- `GET /api/v1/logs?level=&limit=100`
- Table: timestamp, level (color-coded badge), logger, message
- Client-side filter by level
- If `?trace=<id>` query param present, highlight/filter to that trace ID
- Makes command palette log search links resolve

---

### Task 14 — Update sidebar navigation

Add nav entries for every new page. Group as:
- **Network:** Overview, Fleet, Topology
- **Players:** Players, Alt Detection
- **Moderation:** Moderation, Appeals, AI Tasks
- **Staff:** Staff, Security
- **System:** Feature Flags, Translation, Observability, Knowledge, Plugin Sandbox, Marketplace, Settings, Activity

Icons from `lucide-react`: Users, Shield, MessageSquare, Brain, Users2, GitBranch, Lock, Flag, Globe, ScrollText, BookOpen.

---

## Code Standards

- Server component by default — `async function Page()`, fetch at top, render
- Client interactivity in separate `"use client"` files in the same directory, e.g. `moderation-actions.tsx`
- shadcn/ui only: `Card`, `Table`, `Badge`, `Button`, `Sheet`, `Dialog`, `Input`, `Select`, `Tabs`
- Error states: show an error card — don't crash the page
- Loading: add `loading.tsx` for data-heavy pages
- No `any` types without justification
- Icons from `lucide-react` only

---

## Commit Instructions

- One commit per task minimum, e.g. `dashboard: add players list and detail pages (P14 Task 3)`
- Push to `main` after each commit
- Do NOT touch anything outside `umbrella-dashboard-CURRENT/`
- When all tasks done, write `dispatches/PHASE14-DASHBOARD-PAGES/SUBCHAT-HANDBACK.md` with:
  - All commits made (SHA + message)
  - Anything that couldn't be completed and why
  - Any decisions the head chat should know about
  - Any type errors found and how resolved

---

## Verification before handback

- Every new page has a sidebar nav entry
- Every `href` in `lib/search.ts` resolves to a real page
- `middleware.ts` protects every new route
- `typescript.ignoreBuildErrors` removed from `next.config.mjs`
- No uncommitted changes
