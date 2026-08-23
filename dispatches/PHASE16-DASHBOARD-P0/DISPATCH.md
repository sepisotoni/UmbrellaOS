# DISPATCH: Dashboard P0 Ports — Toast, PunishModal, BroadcastModal, Sidebar Instances

**Type:** Sub-chat (write access)
**Scope:** `umbrella-dashboard-CURRENT/` only
**Write PAT:** [WRITE_PAT — see head chat]
**Repo:** https://github.com/sepisotoni/UmbrellaOS
**Tip:** 8b47e44

Read files lazily — only what you need. Commit after every task. Push after each commit.

---

## Reference docs

Before starting read:
- `DASHBOARD-IDEAS-FROM-GEMINI-V2.md` — pixel-perfect UI spec. Section 1.4 (Toast), Section 4 (PunishModal), Section 5 (BroadcastModal), Section 1.2 (Sidebar). These have exact CSS classes, colours, and behaviour specs.
- `umbrella-dashboard-CURRENT/src/lib/api.ts` — existing API calls (read lazily, search for relevant functions)
- `umbrella-dashboard-CURRENT/src/components/ui/index.tsx` — existing UI primitives

Do NOT deviate from the spec in the reference doc. Use the exact CSS classes, colours, and patterns described there.

---

## Known permission issue (flag from 16E sub-chat)

`POST /api/v1/ai/copilot` requires `operational_intelligence.view` permission. The plugin API key needs this permission mapped on the backend. Note this in the handback — do NOT work around it in the dashboard.

---

## Task 1 — Toast notification system

**New file:** `umbrella-dashboard-CURRENT/src/components/ui/Toast.tsx`
**Update:** `umbrella-dashboard-CURRENT/src/context/AuthContext.tsx` (or create a separate `ToastContext.tsx`)
**Update:** `umbrella-dashboard-CURRENT/src/main.tsx` — render toast container

Five toast types as per spec Section 1.4: `success`, `error`, `warning`, `info`, `grim`

Each toast:
- `rounded-xl border p-4 shadow-xl backdrop-blur-md font-mono text-xs`
- Title in `font-bold text-white text-xs`
- Message in `text-[11px] text-slate-300 font-sans`
- Dismiss X button top-right
- Auto-dismiss after 5 seconds
- Fixed `bottom-4 right-4` stack, newest on top

Colours exactly as per spec:
- `success`: `border-emerald-500/40 bg-[#0b1812]/95 text-emerald-300` + `CheckCircle2` icon
- `error`: `border-rose-500/40 bg-[#180b0f]/95 text-rose-300` + `AlertTriangle` icon
- `warning`: `border-amber-500/40 bg-[#18130b]/95 text-amber-300` + `AlertTriangle` icon
- `info`: `border-purple-500/40 bg-[#0b1318]/95 text-purple-300` + `Info` icon
- `grim`: `border-fuchsia-500/40 bg-fuchsia-950/95 text-fuchsia-300` + `ShieldAlert` icon (anticheat-specific)

Export `useToast()` hook with `addToast(type, title, message)` function.
Make it available everywhere — wrap App in the provider.

---

## Task 2 — Punishment / Ban Modal

**New file:** `umbrella-dashboard-CURRENT/src/components/modals/PunishModal.tsx`

Trigger: called with `<PunishModal open={bool} onClose={fn} prefillUsername={str|null} />`

Spec: Section 4 of reference doc. Key fields:
- Player username/UUID text input (`font-mono`, placeholder "e.g. VoidReaper_X")
- Action type `<select>`: Temporary Ban | Permanent Ban | Hardware HWID Ban | Temporary Mute | Permanent Mute | Kick Player | Formal Warning
- Duration `<select>` (only shown for TEMP_BAN / TEMP_MUTE): 1 Day | 7 Days | 30 Days | 90 Days
- Server scope `<select>`: "Network-Wide (Global)" + one entry per live server from `GET /api/v1/dashboard/servers`
- Reason text input + 7 preset reason chips below (see spec for exact wording)
- Evidence URL field (`font-mono`)
- IP Ban checkbox: "Also blacklist player's current IP address" + `AlertTriangle` amber icon

On submit: `POST /api/v1/punishments` with all fields. On success: `addToast('success', 'Punishment Issued', '{type} applied to {username}')`. On error: `addToast('error', 'Failed', err.message)`.

Footer: Cancel (grey outline) + "Confirm & Enforce" (`bg-rose-600` + `ShieldAlert` icon)

---

## Task 3 — Broadcast Modal

**New file:** `umbrella-dashboard-CURRENT/src/components/modals/BroadcastModal.tsx`

Trigger: `<BroadcastModal open={bool} onClose={fn} />`

Spec: Section 5 of reference doc. Key fields:
- Message textarea (3 rows, cyan focus border)
- 4 preset announcement chips (click to fill textarea):
  - "⚠️ Server maintenance in 15 minutes! Please finish your games and save items."
  - "🎉 Double XP & Drops event is now active across all game nodes!"
  - "🛡️ Network security update applied. Enjoy smooth 20.0 TPS gameplay."
  - "⚡ New Anarchy Season 2 raid event starting at the Nether spawn!"
- Target scope `<select>`: All Network Nodes | Game Nodes Only | Proxies Only
- "Flash on screen as Big Title" checkbox

On submit: `POST /api/v1/bridge/message` body `{ message, scope, source: "DASHBOARD" }`. On success: `addToast('success', 'Broadcast Sent', 'Message dispatched to network')`. On error: `addToast('error', 'Broadcast Failed', err.message)`.

Footer: Cancel + "Send Broadcast" (`bg-cyan-600` + `Send` icon)

---

## Task 4 — Sidebar live server instances panel

**Update:** `umbrella-dashboard-CURRENT/src/components/layout/Sidebar.tsx`

Add a second section below the nav links as per spec Section 1.2.

**Section header:** "Instances ({count})" in `text-[10px] uppercase tracking-widest text-slate-500` + `Activity` icon in emerald right-aligned.

Fetch servers from `GET /api/v1/dashboard/servers` on mount, refresh every 30 seconds.

Each server row:
- Status dot with glow: online = `bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]`, warning (TPS < 18) = `bg-amber-400 animate-pulse`, offline = `bg-rose-500`
- Server name in `font-mono text-[11px]`
- Right side: TPS value (amber if < 18, slate otherwise) + pipe + `{players}p` in mono
- On click: navigate to Console page with that server pre-selected

**Sidebar footer:** `border-t border-slate-800/80 bg-slate-900/40` — `Server` icon + "Umbrella Core" text + version from health check in `bg-emerald-950/60 text-emerald-400 border-emerald-500/30 font-mono text-[10px]` badge.

If health check fails, show "Offline" badge in rose instead of version.

---

## Task 5 — Wire modals into the app

Update `umbrella-dashboard-CURRENT/src/App.tsx`:
- Add `PunishModal` and `BroadcastModal` state (`open: bool`, `prefillUsername: str|null`)
- Add a "Issue Punishment" button somewhere accessible — at minimum in the header or as a floating action button
- Add a "Broadcast" button in a visible location

Update `umbrella-dashboard-CURRENT/src/components/pages/ModerationPage.tsx`:
- Add "Issue New Punishment" button top-right that opens PunishModal
- On each punishment row, add a quick-ban button that opens PunishModal with username pre-filled

Also add the quick CSS improvements to `umbrella-dashboard-CURRENT/src/index.css`:
- Custom scrollbars (spec Section 14)
- Font stack: `Plus Jakarta Sans` body, `JetBrains Mono` mono, `Space Grotesk` display
- Add Google Fonts import for all three at top of index.css

---

## Commit Instructions

- `dashboard: toast notification system — 5 types incl grim (P0 Task 1)`
- `dashboard: PunishModal — full punishment issue flow (P0 Task 2)`
- `dashboard: BroadcastModal — network broadcast with presets (P0 Task 3)`
- `dashboard: sidebar live server instances panel + footer (P0 Task 4)`
- `dashboard: wire modals into app + CSS improvements (P0 Task 5)`

When done write `dispatches/PHASE16-DASHBOARD-P0/SUBCHAT-HANDBACK.md` and push.

**Note for handback:** Flag the `POST /api/v1/ai/copilot` permission issue — plugin key needs `operational_intelligence.view` mapped on the backend before ChatResponder works.
