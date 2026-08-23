# SUBCHAT HANDBACK — PHASE16-DASHBOARD-P0

**Status:** ✅ All 5 tasks complete  
**Tip at handback:** `53e5347`  
**Branch:** `main`

---

## Commits Delivered

| Commit | Message |
|--------|---------|
| `054d34e` | dashboard: toast notification system — 5 types incl grim (P0 Task 1) |
| `04cc128` | dashboard: PunishModal — full punishment issue flow (P0 Task 2) |
| `79840b4` | dashboard: BroadcastModal — network broadcast with presets (P0 Task 3) |
| `a1184d7` | dashboard: sidebar live server instances panel + footer (P0 Task 4) |
| `53e5347` | dashboard: wire modals into app + CSS improvements (P0 Task 5) |

---

## What Was Built

### Task 1 — Toast Notification System
- **`src/components/ui/Toast.tsx`** — `ToastProvider` + `useToast()` hook
- Five types: `success` (emerald), `error` (rose), `warning` (amber), `info` (purple), `grim` (fuchsia — anticheat)
- Auto-dismiss after 5 seconds; dismiss X button; stacks newest-on-top at `bottom-4 right-4`
- Exact spec colours/icons: `CheckCircle2`, `AlertTriangle`, `Info`, `ShieldAlert`
- **`src/main.tsx`** — `<ToastProvider>` wraps `<App>` so `useToast()` is available everywhere

### Task 2 — PunishModal
- **`src/components/modals/PunishModal.tsx`**
- All 7 action types; duration select appears only for `TEMP_BAN` / `TEMP_MUTE`
- Server scope populated live from `GET /api/v1/dashboard/servers`
- 7 preset reason chips (spec-exact wording)
- Evidence URL field (monospace), IP ban checkbox with amber `AlertTriangle`
- On success/error: fires `useToast()` with correct type and message
- Footer: Cancel (grey outline) + "Confirm & Enforce" (`bg-rose-600` + `ShieldAlert`)

### Task 3 — BroadcastModal
- **`src/components/modals/BroadcastModal.tsx`**
- 4 spec-exact preset announcement rows (click to fill textarea)
- Scope select + "Flash on screen as Big Title" checkbox in `grid-cols-2`
- Posts to `POST /api/v1/bridge/message` with `{ message, scope, source: "DASHBOARD", big_title }`
- Footer: Cancel + "Send Broadcast" (`bg-cyan-600` + `Send`)

### Task 4 — Sidebar Live Instances Panel + Footer
- **`src/components/layout/Sidebar.tsx`** — full rewrite
- Navigation section now has "Navigation" label, `text-[10px] uppercase tracking-widest text-slate-500`
- Active state ported to spec: `bg-slate-800/90 text-cyan-300 border border-slate-700 shadow-sm`
- **Instances panel**: fetches `GET /api/v1/dashboard/servers` on mount, refreshes every 30 s
  - Status dots: emerald glow (online), amber pulse (TPS < 18), rose (offline)
  - Row: name mono, TPS (amber if < 18), pipe, players count
  - Click navigates to Console page
- **Footer**: `Server` icon + "Umbrella Core" + version badge from `GET /health`
  - Version badge: `bg-emerald-950/60 text-emerald-400 border-emerald-500/30 font-mono text-[10px]`
  - If health check fails: "Offline" badge in rose

### Task 5 — Wire Modals into App + CSS
- **`src/App.tsx`**: `PunishModal` and `BroadcastModal` state; floating action buttons bottom-left (cyan Broadcast, rose Punish); `ModerationPage` receives `onOpenPunish` callback
- **`src/components/pages/ModerationPage.tsx`**:
  - `onOpenPunish` prop threaded from App → ModerationPage → PunishmentsTab
  - "Issue New Punishment" button top-right of punishments tab (opens PunishModal)
  - Quick-ban icon button (`ShieldAlert`) on each punishment row — opens PunishModal with `player_uuid` pre-filled
- **`src/index.css`**:
  - Google Fonts import: `Plus Jakarta Sans` (body), `JetBrains Mono` (mono), `Space Grotesk` (display)
  - CSS custom properties: `--font-body`, `--font-mono`, `--font-display`
  - Custom scrollbars: 4px, violet-tinted (`rgba(99,102,241,…)`), Firefox `scrollbar-width: thin`

---

## Known Issues / Flags for Head Chat

### ⚠️ `POST /api/v1/ai/copilot` — Permission Not Mapped
The plugin API key needs `operational_intelligence.view` permission mapped on the backend. ChatResponder in AI Ops will return 403 until this is done. **Do not work around in the dashboard** — backend fix required.

### `POST /api/v1/bridge/message` — Endpoint Not Yet in `api.ts`
BroadcastModal calls this endpoint directly via `fetch` using `getBaseUrl()` (the canonical base-URL getter from `api.ts`). This works correctly but the endpoint is not added to the typed API client. A follow-up can add it to `api.ts` under a `bridge` export if desired.

### ModerationPage `onOpenPunish` Is Optional
The prop is typed `onOpenPunish?: (username?: string) => void` so any existing call sites that don't pass it (e.g., tests or other pages that import `ModerationPage`) are unaffected. When the prop is absent the quick-ban buttons simply don't render.

---

*Sub-chat closed. All tasks committed and pushed.*
