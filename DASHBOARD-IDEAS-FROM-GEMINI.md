# DASHBOARD-IDEAS-FROM-GEMINI.md

> Read-only audit comparing archived Gemini dashboard (`5cf4176`) against current Claude dashboard (`7b50428`).
> Ref: `umbrella-dashboard-CURRENT/src/`

---

## 1. Features / UI Elements Worth Keeping from the Gemini Dashboard

### 1.1 Command Palette (`CommandPalette.tsx`) — **HIGH VALUE, ENTIRELY MISSING**

The Gemini build had a full `⌘K` command palette triggered from the header. It supported:
- Keyboard navigation (arrow keys + Enter)
- Full-text search across page names AND their subtitles
- Categorised results (`Navigation` vs `Quick Actions`)
- A "Quick Actions" category — e.g. "Issue Network Punishment" launches the modal directly without navigating
- Mouse-hover synced to selected index
- ESC to close, ⌘K toggle

The current dashboard has **zero keyboard navigation**. This is a real operator-UX gap — staff doing fast triage should be able to jump pages without mouse.

**Port verdict:** Port the whole component. It's self-contained and only needs `setPage` wired in.

---

### 1.2 Global Header with Connection Status + User Pill (`Header.tsx`) — **MISSING**

The Gemini build had a dedicated `<Header>` component that sat above the sidebar+content split. It provided:
- **Connection status pill** with animated dot (`CORE CONNECTED` / `CORE DISCONNECTED`) and the backend version number (`v{healthInfo.version}`)
- **Broadcast button** in the header for one-click global announcements
- **`⌘K` search button** showing the keyboard shortcut hint
- **User pill** showing avatar initial, username, and role badge — clicking it navigated to Settings

The current dashboard has none of this. The sidebar has a bare "UmbrellaOS" text label and a logout button, with no connection status visible outside of the `DisconnectedBanner`. Staff have no persistent at-a-glance indicator of whether core is live.

**Port verdict:** Port the Header. Drop the Broadcast button shortcut for now if BroadcastModal isn't wired — but the connection pill and user pill are essential.

---

### 1.3 Collapsible Sidebar with Icon-Only Mode — **MISSING**

The Gemini sidebar had a `sidebarCollapsed` toggle (chevron button at the bottom) that switched the sidebar between full-width labels and icon-only `w-16` mode. The active state used a glowing purple border + `shadow-[0_0_12px_rgba(168,85,247,0.15)]` effect. The current sidebar is always full-width with no collapse affordance.

**Port verdict:** Worth adding the collapse button + `w-16` icon mode. Especially useful on smaller screens.

---

### 1.4 Punish Modal (`PunishModal.tsx`) — **MISSING, REAL FEATURE**

The Gemini dashboard had a fully wired punishment modal with:
- Punishment type selector grid: `TEMP_BAN | BAN | IP_BAN | TEMP_MUTE | MUTE | KICK | WARN` — toggled via button chips
- Duration chip selector for temporary types: `1d | 7d | 30d | 90d` — only shown when relevant
- **Server scope dropdown** populated from live API — `GLOBAL` or per-server
- **Preset reasons** — clickable chips that auto-fill the reason field (`GrimAC Flag: Reach & Hitbox Expansion`, etc.)
- Evidence URL field
- Real `api.createPunishment()` submission with toast on success

The current dashboard has a moderation page that lists punishments but no quick-issue modal accessible from anywhere on the dashboard. The only way to create a punishment is buried in the Moderation page.

**Port verdict:** Port the whole modal. It's the single highest-value action on the entire platform.

---

### 1.5 Broadcast Modal (`BroadcastModal.tsx`) — **MISSING, REAL FEATURE**

The Gemini dashboard had a Broadcast modal with:
- Server scope selector (`GLOBAL` or per-server from live API)
- Free-text message textarea with MiniMessage format hint
- **Quick templates** — four pre-written announcement strings (maintenance warning, double XP event, anticheat update, event start) as one-click fill buttons
- Real `api.broadcast()` submission

The current dashboard has no broadcast capability whatsoever.

**Port verdict:** Port the modal. Wire the Broadcast button in the Header.

---

### 1.6 Overview Page — Clickable Stat Cards + Fleet List + GrimAC Feed (`OverviewView.tsx`) — **PARTIALLY MISSING**

The Gemini overview had:
- **Clickable stat cards** that navigate to the relevant section on click (Servers → fleet page, Players → players page, etc.)
- **Secondary stat line** on each card: e.g. "Avg TPS: 19.8" on the Servers card, "Active bans: 3" on the Appeals card
- **Full fleet panel** (2/3 width) listing every server with: coloured status dot (pulse animation for online), server version, player count with max, and TPS with colour-coded value (green ≥19.5, amber ≥17, red below)
- **GrimAC activity feed** (1/3 width) as a live scrollable list of the 15 most recent violations with VL badge, check name, and timestamp
- "Manage Fleet →" and "All Flags →" links in panel headers

The current overview has stat cards (good) but no fleet list and no GrimAC feed inline. Users have to navigate away to see either.

**Port verdict:** Add the fleet panel and GrimAC feed to the current overview. The clickable cards and secondary stat lines are also worth adding.

---

### 1.7 DisconnectedBanner with Retry Button (`DisconnectedBanner.tsx`) — **PRESENT BUT WEAKER**

The Gemini banner had a `ServerOff` icon in a styled icon box, a clear two-line message explaining *why* (GET /health failed), an `Offline` badge, and a **"Retry Connection"** button with spinner that calls `checkHealth()` inline.

The current dashboard has a banner but it's simpler and lacks the retry button.

**Port verdict:** Merge the retry button + styled layout from the Gemini version.

---

### 1.8 Toast Notification System — **MISSING**

The Gemini dashboard had a full toast system managed via `DashboardContext`: `addToast()` / `removeToast()`, four types (`success | error | warning | info`), per-type coloured borders and icons, title + message structure, dismiss button, and `fixed bottom-4 right-4` positioning with `font-mono` micro-text style.

The current dashboard has no visible toast/notification layer. Actions complete silently.

**Port verdict:** Port the toast system — it's the primary feedback mechanism for all write actions (punishments, broadcasts, revokes).

---

### 1.9 Console View — WebSocket with HTTP Fallback + Log Colourisation (`ConsoleView.tsx`) — **WEAKER IN CURRENT**

The Gemini console:
- Attempted a real WebSocket connection (`api.getServerConsoleWebSocketUrl(serverId)`) and gracefully fell back to HTTP dispatch if WS was unavailable
- Had **connection status badge** in the page heading: `CONNECTED | CONNECTING | DISCONNECTED | ERROR`
- **Colour-coded log lines**: commands in purple-bold, errors in rose, warnings in amber, system/info lines in purple/muted, general output in slate
- "Clear" button with a buffer-cleared system message
- Smooth auto-scroll to bottom on new lines

The current console page exists but this level of WS/fallback plumbing and log colourisation should be verified.

**Port verdict:** If the current console lacks WS + colour coding, backport these patterns.

---

### 1.10 AI Tasks View — Three-tab Layout: Tasks / Copilot / Crash Risk (`AITasksView.tsx`) — **PARTIALLY PRESENT**

The Gemini AI view had three sub-tabs:
- **Tasks** — approve/reject queue with real `api.approveAITask()` / `api.rejectAITask()`
- **Copilot** — a chat widget with message history, loading dots, and real backend call
- **Crash Risk** — a per-server risk analysis panel using `api.getCrashRisk(serverId)` with `LOW/MEDIUM/HIGH/CRITICAL` badge styling

The current `AITasksPage` needs auditing — check whether crash risk and copilot sub-tabs are wired to real endpoints or still simulated.

---

### 1.11 Custom Scoped API Key Modal (`CreateApiKeyModal.tsx`) — **MISSING**

The Gemini Api Hub had a "Generate Scoped API Key" modal with:
- Fine-grained scope checkboxes: `read:servers`, `write:servers`, `exec:console`, `read:punishments`, `write:punishments`, `read:players`, `manage:plugins`, `manage:snapshots`
- Each scope with a human-readable description
- Checkbox rows that highlight on selection (`bg-cyan-950/30 border-cyan-500/40`)
- Key name/identifier field

This is real infrastructure — third-party integrations (Tebex, etc.) need scoped keys.

**Port verdict:** Port when the API key management endpoints are surfaced in the dashboard.

---

### 1.12 Entire Views Not in Current Dashboard

These pages existed in Gemini but are **entirely absent** from the current Claude dashboard:

| View | What it did |
|---|---|
| `AutomationView.tsx` + `CreateCronModal.tsx` | Cron task scheduler — BACKUP_WORLDS, memory scavengers, Discord relays — with enable/disable/run-now controls |
| `TopologyView.tsx` | Cluster node map with region filter, per-node server assignments, drain/restart actions |
| `SnapshotsView.tsx` | Time-travel snapshot capture + rollback studio with search/filter by tag |
| `DiscordView.tsx` | Live bridge chat feed, embed builder, slash command management, webhook config, status panel |
| `TranslationView.tsx` | Per-language translation key management with AI-powered test translation scratchpad |
| `ApiHubView.tsx` | API explorer (endpoint list + live test runner) + webhook subscription manager + API key list |
| `AIOperationalView.tsx` | Alternative AI panel layout with risk badge system |

These range from aspirational (snapshots, topology) to genuinely needed (automation scheduler, Discord bridge view, API hub).

---

## 2. Things the Gemini Dashboard Did Visually Better

### 2.1 Typography Stack
The Gemini CSS defined three distinct font roles:
- `Plus Jakarta Sans` — body/sans
- `JetBrains Mono` — `code`, `pre`, `.font-mono`
- `Space Grotesk` — `.font-display` headings

This gave headings a distinct character from body and terminal output. The current dashboard uses a single default `sans` stack.

### 2.2 Custom Scrollbars
The Gemini `index.css` defined thin 6px webkit scrollbars with dark-slate track and thumb, hover darkening — consistent with the dark theme. The current dashboard uses native browser scrollbars which look out of place on dark UIs.

### 2.3 Stat Card Active State Hover Glow per Category
Each Overview stat card had a per-category hover border colour that matched the content type:
- Servers → `hover:border-purple-500/40`
- Players → `hover:border-emerald-500/40`
- Flags → `hover:border-rose-500/40`
- Appeals → `hover:border-amber-500/40`

The current cards use a uniform accent. The per-category colour coding makes it easier to visually scan the dashboard at a glance.

### 2.4 Sidebar Active State — Glow Shadow
The active sidebar item had `shadow-[0_0_12px_rgba(168,85,247,0.15)]` which gave it a subtle glow. The current sidebar uses a `border-r-2 border-violet-500` approach which is fine but less distinctive.

### 2.5 Section Header Pattern in Panels
The Gemini fleet/GrimAC panels used `UPPERCASE TRACKING-WIDER FONT-MONO` section headers with border-bottom dividers and a "→ All X" link at the right. The current overview doesn't have a comparable layout for nested panels.

### 2.6 Form Field Design Consistency
The Gemini modals used `rounded-xl border border-[#1e1b4b] bg-[#070914] px-3.5 py-2.5` on inputs — slightly more rounded, with stronger padding. The current pages tend toward plainer form fields.

### 2.7 Punishment Type Chip Selector
Rather than a `<select>` dropdown for punishment type, the Gemini PunishModal used a button grid of chips. This is much faster for staff to tap on mobile and visually clearer about what options exist.

### 2.8 Scanline Animation CSS Utility
The Gemini CSS had a `.scanline-effect::after` keyframe animation — a cyan shimmer line that scrolled top-to-bottom on the terminal. Visual polish that would suit the Console page.

### 2.9 Page Descriptions Under Headings
Almost every Gemini view had a `<p className="text-xs text-slate-400 mt-1">` description line under the page title explaining what the section does. The current dashboard tends to omit these, making the UI slightly context-free for new staff.

### 2.10 Custom SVG Icons (`UmbrellaIcons.tsx`)
The Gemini build included hand-crafted SVG icons: `UmbrellaCoreIcon` (chip/processor motif), `UmbrellaBotIcon` (robot with umbrella antenna), and presumably others. These are unique to the brand. The current dashboard uses only generic Lucide icons.

---

## 3. Specific Components Worth Porting

Priority order:

| Priority | Component | Source File | Effort | Notes |
|---|---|---|---|---|
| 🔴 P0 | `PunishModal` | `modals/PunishModal.tsx` | Low | Self-contained, fully wired to API, highest-frequency action |
| 🔴 P0 | `BroadcastModal` | `modals/BroadcastModal.tsx` | Low | Self-contained, real API call, quick templates already written |
| 🔴 P0 | Toast system | `DashboardContext` + App render | Medium | Without this, all write actions are silent — port `addToast`/`removeToast` + the fixed bottom container |
| 🟠 P1 | `CommandPalette` | `command-palette/CommandPalette.tsx` | Low | Drop-in component, just needs `setPage` passed in |
| 🟠 P1 | `Header` | `layout/Header.tsx` | Low–Medium | Needs `useHealthCheck` data + user context; connection status pill is the key feature |
| 🟠 P1 | Overview fleet panel + GrimAC feed | `overview/OverviewView.tsx` (bottom grid) | Medium | Add the 2/3+1/3 grid below stat cards |
| 🟡 P2 | Sidebar collapse toggle | `layout/Sidebar.tsx` | Low | CSS toggle only, `w-16` icon-only mode |
| 🟡 P2 | `DisconnectedBanner` retry button | `common/DisconnectedBanner.tsx` | Low | Add retry logic to current banner |
| 🟡 P2 | Custom scrollbar CSS | `index.css` | Trivial | 10 lines, instant visual improvement |
| 🟡 P2 | Font stack (Space Grotesk / JetBrains Mono) | `index.css` | Trivial | Add `font-display` and proper mono font |
| 🟡 P2 | `UmbrellaIcons` SVG set | `common/UmbrellaIcons.tsx` | Trivial | Copy across, use in sidebar/headers |
| 🟢 P3 | `AutomationView` + `CreateCronModal` | `automation/`, `modals/` | High | Needs backend cron endpoints wired |
| 🟢 P3 | `DiscordView` (bridge tab) | `discord/DiscordView.tsx` | High | Bridge messages need a real endpoint |
| 🟢 P3 | `ApiHubView` (API explorer tab) | `api-hub/ApiHubView.tsx` | Medium | Useful for debugging; scoped API key modal first |
| 🟢 P3 | `CreateApiKeyModal` | `modals/CreateApiKeyModal.tsx` | Low | Port when API key management is surfaced |
| ⚪ P4 | `SnapshotsView` | `snapshots/SnapshotsView.tsx` | Very High | No backend snapshot endpoints exist yet |
| ⚪ P4 | `TopologyView` | `topology/TopologyView.tsx` | Very High | Requires node infrastructure model not in current core |
| ⚪ P4 | `TranslationView` | `translation/TranslationView.tsx` | High | Aspirational; translation API endpoints not built |

---

## Summary

The Gemini dashboard was bloated with fake/mock data (the `DashboardContext` seeded everything from `initialState.ts`) but it had significantly better **operator ergonomics** and **visual feedback loops**. The two biggest concrete gaps in the current Claude dashboard are:

1. **No way to issue a punishment from anywhere except the Moderation page** — the PunishModal and BroadcastModal from Gemini solve this
2. **No feedback when actions succeed or fail** — the toast system is a prerequisite for everything else

Fix those two first, then layer in the Header + CommandPalette for navigation speed.
