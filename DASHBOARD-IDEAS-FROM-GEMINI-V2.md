
# UmbrellaOS Dashboard Ideas — Full Reference



> Compiled from two archived builds:

> - **Gemini Push** — git ref `5cf4176` in `UmbrellaOS` repo

> - **Command Center** — `umbrellaos-command-center.zip`

>

> Compared against current Claude dashboard at `7b50428`.

> All builds are mock-data-only. This doc is a feature and UI reference — no code is being committed.



---



## LAYOUT OVERVIEW



### Current Claude Dashboard

```

\[Sidebar 224px fixed] | \[Page content, scrollable]

No header bar. Sidebar has nav links only. No live data visible anywhere except inside pages.

```



### Command Center Layout (Your Favourite)

```

\[Header 56px — full width, sticky]

  ↳ Zone 1: Brand + TPS pill + player count

  ↳ Zone 2 (xl+ only): 3 stat chips — Nodes online / Proxy type / Backend latency

  ↳ Zone 3: Quick Find (⌘K) | Broadcast button | Account avatar pill

─────────────────────────────────────────────

\[Sidebar 256px]           | \[Main content, max-w-7xl, p-6]

  ↳ Section 1: Nav links  |

    (14 items, with live  |

     count badges)        |

  ↳ Section 2: Instances  |

    (live server list,    |

     TPS + players each)  |

  ↳ Footer: version badge |

─────────────────────────────────────────────

```



### Gemini Push Layout

```

\[Header 56px — full width, sticky]

  ↳ Left: Brand wordmark + connection status pill (CORE CONNECTED / DISCONNECTED)

  ↳ Right: Broadcast button | Quick Find (⌘K) | User pill (avatar initial + username + role)

────────────────────────────────────────────

\[Sidebar 256px, collapsible to 64px] | \[Main content, max-w-7xl]

  ↳ Nav links with active glow       |

  ↳ Collapse toggle at bottom        |

────────────────────────────────────────────

```



**Layout verdict:** Port the Command Center three-zone header + the two-section sidebar (nav + instances panel). These are the two biggest ergonomic upgrades over the current build.



---



## 1. GLOBAL LAYOUT COMPONENTS



### 1.1 Header — Three Zones



**Zone 1 (always visible):**

- Animated `Radio` icon in a `bg-cyan-950/40 border-cyan-500/30` rounded box

- `Umbrella` in white, `OS` in `text-cyan-400` — uses `font-display` (Space Grotesk)

- A pill next to it: `bg-emerald-950/30 border-emerald-500/20` rounded-full with pulsing dot, showing `{avgTps} TPS • {onlinePlayersCount} Online` in `font-mono`



**Zone 2 (xl breakpoint only, hidden on smaller screens):**

- Three chips in a row, each `bg-slate-900/60 border-slate-800 px-3 py-1 rounded-lg font-mono text-xs`:

  - `Nodes: 3/5 Online` with `Server` icon in cyan

  - `Proxy: Velocity (Edge)` with `Globe` icon in emerald

  - `Backend: FastAPI (42ms)` with `Zap` icon in purple — latency in `text-emerald-400` bold



**Zone 3 (right side):**

- **Quick Find button** — `border-slate-800 bg-slate-900/90` with `Search` icon + "Quick Find" label + `⌘K` `<kbd>` badge

- **Broadcast button** — solid `bg-cyan-600 hover:bg-cyan-500` with `Megaphone` icon + "Broadcast" text. Always visible, not hidden at any breakpoint

- **Account avatar pill** — `border-slate-800 bg-slate-900/80` with:

  - User's avatar (or initial in `bg-cyan-950/80 border-cyan-500/40` box if no image)

  - A 2×2px status dot overlaid bottom-right of avatar: `bg-emerald-400 animate-pulse` (connected), `bg-cyan-400` (connecting), `bg-amber-400` (unauthorized), `bg-rose-400` (offline)

  - Username + role badge `bg-cyan-950/80 text-cyan-300 border-cyan-500/30` in uppercase mono

  - Clicking opens the `AccountModal`



---



### 1.2 Sidebar — Two Sections



**Section 1 — Navigation:**

- Section label: `text-\[10px] font-bold uppercase tracking-widest text-slate-500` — "Navigation"

- 14 nav items. Active state: `bg-slate-800/90 text-cyan-300 border border-slate-700 shadow-sm`. Inactive: `text-slate-400 hover:bg-slate-900/60 hover:text-slate-100`

- Each item: icon in `h-3.5 w-3.5`, label, and a live **badge** on the right side for some items:

  - **Players** → `{onlineCount} on` badge in `bg-emerald-500/20 text-emerald-300 border-emerald-500/30`

  - **Moderation** → pending appeals count (amber) OR grimac flags count (rose), whichever is more urgent

  - **AI Ops** → `{activeCrashCount} triage` in `bg-cyan-500/20 text-cyan-300 border-cyan-500/30`

  - **Settings** → feature flags count in `bg-slate-800 text-slate-400`

- Scrollable with `max-h-\[52vh] overflow-y-auto`



**Section 2 — Live Server Instances:**

- Header: `Instances ({servers.length})` in `text-\[10px] uppercase tracking-widest text-slate-500` + `Activity` icon in emerald on right

- Each server row:

  - Status dot: `bg-emerald-400 shadow-\[0\_0\_8px\_rgba(52,211,153,0.6)]` (online), `bg-amber-400 animate-pulse` (warning), `bg-cyan-400 animate-spin` (restarting), `bg-rose-500` (offline)

  - Server name in `font-mono text-\[11px]`

  - Right side: `{tps}` (amber if < 18, else slate) + pipe + `{playersCount}p` in mono

  - Clicking sets `selectedServerId` and navigates to Console tab

  - Active (currently viewing in console): `border-cyan-500/50 bg-cyan-950/30`



**Sidebar footer:**

- `border-t border-slate-800/80 bg-slate-900/40`

- `Server` icon + "Umbrella Core" + version badge `bg-emerald-950/60 text-emerald-400 border-emerald-500/30 font-mono text-\[10px]`



---



### 1.3 Command Palette (⌘K)



- Opens on `Cmd/Ctrl + K`, closes on `Escape` or re-press

- Full-screen overlay: `bg-black/80 backdrop-blur-sm`, centered card `max-w-2xl`

- Search header: `Search` icon + text input (autofocus) + `X` close button

- Results list with items grouped into `Navigation` and `Quick Actions` categories

- Each result row:

  - Icon (Lucide) + title in bold + subtitle description

  - Category badge (`Navigation` / `Quick Actions`) right-aligned in a small mono pill

  - Hover/selected state: `bg-purple-950/80 border border-purple-500/40` (Gemini) or `bg-slate-800` (Command Center)

  - Arrow key navigation synced with mouse hover

- Footer bar: "Navigate with mouse or arrow keys" | "Press ESC to close"

- **Quick Actions** beyond navigation:

  - "Issue Network Punishment" → opens PunishModal directly



---



### 1.4 Toast Notification System



Five types, each with distinct colour + icon, rendered fixed `bottom-4 right-4` in a flex-col stack:



| Type | Border | Background | Text | Icon |

|---|---|---|---|---|

| `success` | `border-emerald-500/40` | `bg-\[#0b1812]/95` | `text-emerald-300` | `CheckCircle2` in emerald |

| `error` | `border-rose-500/40` | `bg-\[#180b0f]/95` | `text-rose-300` | `AlertTriangle` in rose |

| `warning` | `border-amber-500/40` | `bg-\[#18130b]/95` | `text-amber-300` | `AlertTriangle` in amber |

| `info` | `border-purple-500/40` | `bg-\[#0b1318]/95` | `text-purple-300` | `Info` in purple |

| `grim` | `border-fuchsia-500/40` | `bg-fuchsia-950/95` | `text-fuchsia-300` | `ShieldAlert` in fuchsia — **anticheat-specific** |



Each toast: `rounded-xl border p-4 shadow-xl backdrop-blur-md font-mono text-xs`. Title in `font-bold text-white text-xs`. Message in `text-\[11px] text-slate-300 font-sans`. Dismiss `X` button top-right.



---



### 1.5 DisconnectedBanner



Shown at top of every page when core is unreachable:



- `border-rose-500/50 bg-rose-950/80 p-4 rounded-xl backdrop-blur-md shadow-xl`

- Left side: `ServerOff` icon in a `bg-rose-900/60 border-rose-500/40 rounded-lg h-9 w-9` box

- Bold white title "DISCONNECTED FROM CORE BACKEND" + `Offline` mono pill

- Subtitle: "Unable to reach FastAPI Core (`GET /health` failed). Live data cannot be updated until the connection is restored."

- Right side: **"Retry Connection"** button with `RefreshCw` icon (animates `animate-spin` while retrying). Calls `checkHealth()`. Shows "Testing Connection..." while pending.



---



## 2. OVERVIEW PAGE



### 2.1 Emergency Alert Banner (top, conditional)



Only shown when a server has TPS < 18 or significant GrimAC flags:



- Gradient: `bg-gradient-to-r from-amber-950/40 via-slate-900/80 to-slate-900/80 border-amber-500/30`

- Left: `Flame` icon (animate-pulse) in `bg-amber-900/40 border-amber-500/40 h-9 w-9 rounded-lg`

- Title: "Active Threat Radar \& Incident Mitigation" + `Level 2 Watch` pill in amber

- Body text names the affected server, its current TPS, and GrimAC violation count in the last 15 minutes

- Two action buttons right-side:

  - "Inspect \[Server]" → grey button with `Terminal` icon, navigates to console for that server

  - "AI Triage Diagnosis" → solid `bg-cyan-600` with `Sparkles` icon, navigates to AI Ops



### 2.2 Six-Metric Stat Row



Grid: `grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3`. Each card: `bg-\[#0c1017] border-slate-800 rounded-xl p-3.5`.



Inside each card:

- Top row: label `text-xs font-medium text-slate-400` + icon right-aligned

- Big number: `text-2xl font-bold font-mono text-white tracking-tight`

- Subline: `text-\[11px]` in relevant accent colour



Six metrics:

1\. **Cluster TPS** — `Activity` icon in emerald. Subline: "Stable (Target 20.0)"

2\. **Players Online** — `Users` icon in cyan. Subline: "Cap: {maxPlayers}"

3\. **Allocated RAM** — `HardDrive` icon in indigo. Shows `{GB} GB`. Subline: `/ {maxGB} GB provisioned`

4\. **Active Bans** — `Lock` icon in rose. Subline: "ACTIVE punishment records"

5\. **Pending Appeals** — `Scale` icon in amber. Subline: "{pendingCount} awaiting verdict"

6\. **GrimAC Flags** — `ShieldAlert` icon in fuchsia. Subline: "Action Required" if > threshold



### 2.3 Main Grid — Server Table + Quick Actions



Layout: `grid-cols-1 lg:grid-cols-3 gap-6`. Server table spans 2 columns, Quick Actions takes 1 column.



**Server table** (`<table>` with proper `<thead>/<tbody>`):

- Background: `bg-\[#0c1017] border-slate-800 rounded-xl overflow-hidden`

- Header row: `bg-slate-900/60 border-b border-slate-800 font-mono text-\[11px] text-slate-400`

- Columns: Instance / Core | Status | TPS | Players | Memory / CPU | GrimAC | Actions

- Each row `hover:bg-slate-900/40 transition-colors`:

  - **Instance col**: status dot with glow (`shadow-\[0\_0\_8px\_rgba(52,211,153,0.5)]` for online) + server name (hover: `text-cyan-300`) + version + host:port below in `text-\[10px] font-mono text-slate-500`

  - **Status**: coloured mono badge (online emerald / warning amber / restarting cyan / offline rose)

  - **TPS**: coloured — `text-emerald-400` if ≥ 18, `text-amber-400` if < 18

  - **Players**: `{count}` / `{max}` with max dimmed

  - **Memory/CPU**: GB value + a `w-20 h-1 bg-slate-800 rounded-full` progress bar filled with `bg-cyan-500` (or `bg-amber-500` if CPU > 80%)

  - **GrimAC**: `CheckCircle2` + "Shield" badge in emerald if enabled, else "N/A"

  - **Actions**: two icon buttons — `Terminal` (navigate to server console) + `RefreshCw` (graceful restart)



**Quick Actions column:**

- Header: "Executive Quick Actions" + `Zap` icon

- Four full-width action rows in `bg-\[#0c1017] p-4 space-y-3 rounded-xl`:

  1. "Issue Global Punishment / Ban" — `border-rose-500/20 bg-rose-950/20 text-rose-200` + `ShieldAlert` icon. Right label: "Modal →"

  2. "Dispatch Global Broadcast Notice" — `border-cyan-500/20 bg-cyan-950/20 text-cyan-200` + `Megaphone` icon. Right label: "Title / Chat →"

  3. "Flush Garbage Collector (GC Sweep)" — grey border + `RefreshCw` icon in emerald. Right label: "ZGC Fast"

  4. "Emergency Proxy Traffic Quarantine" — `border-amber-500/20 bg-amber-950/20 text-amber-200` + `AlertOctagon` icon. Right label: "Lock Rate"



**GrimAC Live Ticker mini-widget** (below quick actions):

- "GrimAC Live Threat Stream" header with `animate-ping` rose dot

- "View Center →" link right-aligned navigates to Moderation

- Shows last 3 violations as compact cards: `\[VL:{level}] {checkName}` in rose mono, player name in cyan, server in slate, details line below



---



## 3. MODERATION PAGE



### Layout and Sub-tabs



Four sub-tabs in a scrollable row, each with a count badge:



| Tab | Icon | Badge |

|---|---|---|

| Punishments Ledger | `Lock` | total count (neutral slate) |

| GrimAC Live Stream | `Activity` | count in `bg-rose-950/80 text-rose-300 border-rose-500/30` |

| Alt Account Rings | `Fingerprint` | count in `bg-amber-950/80 text-amber-300 border-amber-500/30` |

| Appeals Desk (AI Triage) | `FileText` | pending count in `bg-indigo-950/80 text-indigo-300 border-indigo-500/30` |



Active tab: `bg-slate-800 border border-slate-700 shadow-sm` with accent text colour per tab.

Page header has a solid `bg-rose-600 hover:bg-rose-500` "Issue New Punishment" button top-right.



### Tab 1 — Punishments Ledger



**Filters bar** (`bg-\[#0c1017] p-3 rounded-xl border-slate-800`):

- Left: `Search` icon + text input (search by player name, reason, or staff)

- Right: two `<select>` dropdowns:

  - Status: All / Active Only / Expired / Pardoned

  - Type: All / Bans (Perm/Temp/HWID) / Mutes / Warnings



**Table** (same `<table>` pattern as overview server table):

Columns: Player \& ID | Type | Reason \& Evidence | Issuer | Dates \& Scope | Status | Actions



- **Type badge** colours: BAN types → rose; MUTE → amber; WARN/KICK → slate

- **Reason column**: truncated with `Evidence` link (`ExternalLink` icon in cyan) if `evidenceUrl` exists

- **Dates column**: `createdAt` + expiry ("Exp: {date}" or "Permanent") + server scope — all `font-mono text-\[11px]`

- **Status badge**: ACTIVE → `bg-rose-950/60 text-rose-300 border border-rose-600`; PARDONED → emerald; else slate

- **Pardon button** (only on ACTIVE rows): `bg-slate-800 hover:bg-emerald-900/60 hover:text-emerald-200` — "Pardon"



### Tab 2 — GrimAC Live Stream



**Info header banner**: fuchsia border, `Activity` icon, "GrimAC Quantum Packet Prediction Engine" title, "14 Prediction Checks Active" badge with `animate-ping` dot.



Each violation card (`border-slate-800 bg-\[#0c1017] p-4 rounded-xl hover:border-slate-700`):

- Left: `VL{level}` in a `bg-rose-950/40 border-rose-500/30 h-8 w-8 rounded-lg font-bold font-mono text-xs` box

- Player name in bold white mono + `Failed: {checkName}` rose badge + `@{server}` + `Ping {ms}ms • TPS {tps}` in slate

- Details paragraph in `font-mono` below

- If `autoMitigationTaken`: `CheckCircle2` icon + "Autonomous Action: {action}" in cyan

- Right: two buttons — "Spectate" (grey) + "Ban Player" (rose solid, opens PunishModal)



### Tab 3 — Alt Account Rings



**Info banner**: amber border, `Fingerprint` icon, "Heuristic Alt Ring Clustering \& VPN Detector" title.



Cards in a `grid-cols-1 md:grid-cols-2 gap-4`:

Each cluster card (`border-slate-800 bg-\[#0c1017] p-5 rounded-xl`):

- Cluster ID (mono) + status badge top row:

  - `CONFIRMED\_ALT\_RING` → rose

  - `WHITELISTED\_HOUSEHOLD` → emerald

  - `UNDER\_REVIEW` → amber

- Root identifier in `text-cyan-400 font-mono`

- "Associated Accounts ({n}):" label + a flex-wrap row of mono pills, each account name in `bg-slate-900 border-slate-700 px-2 py-0.5 text-\[11px]`

- Notes line in italic slate

- Footer: "Confidence: {n}%" in amber bold + **"Bulk-Ban Cluster"** rose button (or "All Alts Blacklisted ({n})" text if already done)



### Tab 4 — Appeals Desk (AI Triage)



**Info banner**: indigo border, `Sparkles` icon, "AI Sentiment \& Remorse Appeal Analysis" title.



Each appeal ticket card (`border-slate-800 bg-\[#0c1017] p-5 space-y-4 rounded-xl`):

- **Header row**: player name bold + ID mono + status badge (emerald / rose / amber) + "Original Punishment: {reason}" in rose + submitted date right-aligned

- **Player Statement block**: `border-slate-800 bg-slate-900/70 p-3 rounded-lg font-mono italic` — quoted

- **AI Triage block** (`border-indigo-500/30 bg-indigo-950/20 p-3.5 rounded-lg`):

  - `Sparkles` icon + "Umbrella AI Recommendation: {action}" bold in indigo

  - "Authenticity Score: {n}/100" mono right-aligned

  - AI analysis paragraph in `font-mono text-\[11px]`

- **Verdict buttons** (only if status is PENDING or AI\_REVIEWED):

  - "Reject Appeal" — `border-rose-500/30 bg-rose-950/30` + `XCircle` icon

  - "Approve \& Unban" — solid `bg-emerald-600` + `CheckCircle2` icon



---



## 4. BAN / PUNISHMENT MODAL



Trigger: "Issue New Punishment" button on moderation page, Quick Actions on overview, sidebar ban button, GrimAC "Ban Player" button.



Modal: `max-w-lg rounded-xl border-slate-700 bg-\[#0f131a] shadow-2xl`



**Header**: rose icon box (`ShieldAlert`) + "Issue Punishment / Enforcement" + "Synchronized across Velocity Proxies and Game Nodes" subtitle



**Form fields:**

1\. **Player Username / UUID** — text input, `font-mono`, placeholder "e.g. VoidReaper\_X"

2\. **Action Type + Duration** — in a `grid-cols-2 gap-3`:

   - Action Type: `<select>` with options: Temporary Ban | Permanent Ban | **Hardware HWID Ban** | Temporary Mute | Permanent Mute | Kick Player | Formal Warning

   - Duration `<select>` (only shown for TEMP\_BAN / TEMP\_MUTE): 1 Day (24 Hours) | 7 Days (1 Week) | 30 Days (1 Month) | 90 Days (3 Months)

3\. **Server Scope** — `<select>`: "Network-Wide (Global Across All Instances)" + one entry per live server

4\. **Reason** — text input + quick preset chips below (4 shown):

   - "GrimAC Flag: Reach \& Hitbox Expansion"

   - "KillAura \& AutoClicker (Unfair Advantages)"

   - "Fly / Speed / Movement Exploit"

   - "Severe Chat Toxicity / Hate Speech"

   - (+ 3 more: Multi-Account Ban Evasion, Duplication Exploit, Malicious Lag Machine)

5\. **Evidence URL** — text input, placeholder "https://grim.umbrella-mc.net/logs/... or video url", `font-mono`

6\. **IP Ban checkbox** — "Also blacklist player's current IP address" + `AlertTriangle` icon in amber beside it



**Footer buttons**: Cancel (grey outline) + "Confirm \& Enforce" (`bg-rose-600` + `ShieldAlert` icon)



---



## 5. BROADCAST MODAL



Trigger: Header Broadcast button, Overview Quick Actions.



Modal: `max-w-lg rounded-xl border-slate-700 bg-\[#0f131a]`



**Header**: cyan icon box (`Megaphone`) + "Global Network Broadcast" + "Dispatch live titles, chat notices, and audio cues"



**Form fields:**

1\. **Broadcast Message** — `<textarea rows={3}>`, focus cyan border

2\. **Preset Announcements** (clickable rows, fill message field):

   - "⚠️ Server maintenance in 15 minutes! Please finish your games and save items."

   - "🎉 Double XP \& Drops event is now active across all game nodes!"

   - "🛡️ Network security update applied. Enjoy smooth 20.0 TPS gameplay."

   - "⚡ New Anarchy Season 2 raid event starting at the Nether spawn!"

3\. **Bottom row** (`grid-cols-2 gap-3`):

   - Target Scope `<select>`: All Network Nodes | Game Nodes Only (Survival/Skyblock/Bedwars) | Proxies Only

   - "Flash on screen as Big Title" — checkbox toggle



**Footer**: Cancel + "Send Broadcast" (`bg-cyan-600` + `Send` icon)



---



## 6. ACCOUNT MODAL



Trigger: Avatar pill in header right zone.



Modal: `max-w-2xl rounded-xl border-slate-800 bg-\[#0d1117] max-h-\[90vh]` — scrollable content



**Header**: `User` icon in cyan box + "Connected Account \& Backend Wire" + subtitle



**Status bar** below header (always visible): "Backend Status:" + coloured pill — `connected` emerald / `connecting` cyan / `unauthorized` amber / `offline` rose / `degraded` orange



**Three tabs**:



### Tab 1 — Profile

- Avatar (img with `border-cyan-500/40` or initial box fallback) with `CheckCircle2` dot overlay

- Username + discriminator + role badge + "Authenticated via Discord OAuth"

- Disconnect/Logout button top-right of card: `border-rose-500/30 bg-rose-950/30 text-rose-300`

- Two info cards (grid-cols-2):

  - Discord Account ID — mono value + copy button (toggles to `Check` icon for 2s)

  - Linked Minecraft Identity — username in `text-emerald-400` + "UUID Verified" label



### Tab 2 — Backend Integration (Render)

- Backend URL editable text input

- "Test Backend Health" button → calls `/health`, shows latency in success toast

- Status overview with all 5 states mapped to colours



### Tab 3 — Bearer Tokens \& Keys

- Session token — `<input type="password">` with `Eye/EyeOff` toggle button absolute right

- Admin key — same pattern, value in `text-cyan-300 font-mono`

- "Save Configuration" button → `setBackendBaseUrl` + `setAdminKey` + `setSessionToken` + `refreshBackendData()`



---



## 7. SETTINGS PAGE



### Layout



`grid-cols-1 lg:grid-cols-12 gap-6` — category nav takes 3 cols, form takes 9 cols.



**Left category nav** (3 col):

- "Categories" label `text-\[10px] uppercase tracking-wider text-slate-500`

- Each category button: `px-3 py-2.5 rounded-lg text-xs font-semibold`

  - Active: `bg-slate-800 text-cyan-300 border border-slate-700 shadow-sm` + cyan icon

  - Inactive: `text-slate-400 hover:bg-slate-900/80`

- API category has a `h-1.5 w-1.5 bg-cyan-400` dot badge (live indicator)

- Feature Flags category has a count badge



**Right form area** (9 col):

- **Category banner card**: `bg-\[#0d1117] border-slate-800 p-5 rounded-xl` — icon box + category name + backend support badge:

  - Supported → `bg-emerald-950/80 text-emerald-300 border-emerald-500/30` "POST /settings/{key} Active"

  - Not yet → `bg-amber-950/80 text-amber-300` "Client State (Backend In Progress)"

- **Fields card** below: `bg-\[#0c1017] border-slate-800 p-6 space-y-6 rounded-xl`



**Page header actions** (top-right):

- "Rotate Service Key" button (only when API category active): `border-amber-500/40 bg-amber-950/40 text-amber-300` + `RotateCw` icon — generates a new key locally and updates `adminKey`

- "Save Category" button: `bg-cyan-600` + `Save` icon — saves current category fields



### Nine Setting Categories and Their Fields



**1. General** (`Globe` icon):

- Network Display Name — text

- Server List Ping MOTD — text (MiniMessage format)

- Global Player Cap — number

- Maintenance Lockdown — **boolean toggle** ("ENABLED" / "DISABLED" pill button: `bg-emerald-950/60 text-emerald-300 border-emerald-500/30`)



**2. API \& Keys** (`Key` icon):

- FastAPI Backend URL — text

- Service Admin Key (X-Admin-Key) — **secret** (masked input with Eye toggle)

- Active User Session Bearer Token — **secret**

- API Rate Limit (Requests/Minute) — number



**3. Discord** (`Bot` icon):

- Discord Bot Application Token — **secret**

- Primary Discord Guild ID — text

- Require Discord Account Verification — boolean toggle

- Staff Anticheat Alert Channel ID — text

- Public Ban Announcements Channel ID — text



**4. AI Ops** (`Cpu` icon):

- Automated Appeal AI Review — boolean toggle

- AI Recommendation Acceptance Threshold (0–100) — number

- Google Gemini API Key — **secret**

- Automatic Crash Post-Mortem Generation — boolean toggle



**5. Moderation** (`ShieldCheck` icon):

- GrimAC Auto-Ban Confidence % — number

- Default Mute Duration (Seconds) — number

- Appeal Resubmission Cooldown (Hours) — number

- Alt Detection Aggressiveness — **select**: Low (Strict HWID Match Only) | Medium (HWID + Exact IP) | High (HWID + Subnet Cluster)



**6. Network** (`Radio` icon, marked "Client State"):

- Primary Proxy Hostname — text

- Packet Compression Threshold (Bytes) — number

- Velocity Modern Forwarding Secret — **secret**

- IP Forwarding Guard — boolean toggle



**7. Security** (`Lock` icon, marked "Client State"):

- Enforce Staff Multi-Factor Authentication (2FA) — boolean

- Dashboard Admin IP Whitelist (CIDR) — text, comma-separated

- Staff Session Timeout (Minutes) — number



**8. Database** (`Database` icon, marked "Client State"):

- PostgreSQL Connection URI — **secret**

- SQLAlchemy Connection Pool Size — number

- Max Pool Overflow — number



**9. Feature Flags** (`SlidersHorizontal` icon):

Custom UI instead of standard fields. Each flag card:

- Flag name + `flag.key` mono badge + `flag.category` pill

- Description in `font-mono text-\[11px]`

- "Environments: {list} • Modified by: {staff} ({date})" in `text-\[10px] text-slate-500`

- Right side: **Rollout slider** — `w-32` range input `min=0 max=100 step=5` with percentage label + `accent-cyan-500`; and **Enable/Disable toggle pill**: enabled → `bg-emerald-950/40 text-emerald-300 border-emerald-500/30` hover changes to rose (click to disable); disabled → `bg-slate-800 text-slate-400`



**Field rendering for text/number/secret/select:**

- `text`: `rounded-lg border-slate-800 bg-slate-900/90 p-2.5 text-xs text-white font-mono focus:border-cyan-500`

- `number`: same but `w-48` width

- `select`: `w-full sm:w-80` same styling

- `secret`: password input with `text-cyan-300 font-mono`, `Eye/EyeOff` button absolute right at `right-3 top-2.5`

- Label format: `text-xs font-bold text-white` + `(field.key)` in `text-\[10px] text-slate-500 font-normal font-mono` on same line

- Description below label: `text-\[11px] text-slate-400`

- Boolean: rendered as a pill button inline on the same row as label (not below it)



---



## 8. CONSOLE PAGE



### Layout



Full-height terminal in a `bg-\[#04060c]` (near-black) card with `rounded-xl border-slate-800 shadow-2xl`.



**Header controls row:**

- Page title: "Server Terminal \& Console" + **connection status badge** inline:

  - `CONNECTED` → `bg-emerald-950/80 text-emerald-300 border-emerald-800/40`

  - `CONNECTING` → amber

  - `DISCONNECTED / ERROR` → rose

- Server selector: `Server` icon + `<select>` with each server `{name} ({id})`

- Filter tabs: ALL | INFO | WARN | ERROR | GRIM — filters displayed log lines client-side

- Search/grep input field

- Auto-scroll toggle: `Play/Pause` icon button — pauses terminal from scrolling (still receives logs)

- Download/Export button: downloads buffer as `.txt`

- Clear button: inserts `\[UmbrellaOS Console] Terminal buffer cleared.` system line



**Terminal body** (`h-\[520px] overflow-y-auto font-mono text-xs`):



Log line colourisation:

- Lines starting with `>` (sent commands) → `text-purple-300 font-bold`

- Lines containing `ERROR` or `Exception` → `text-rose-400`

- Lines containing `WARN` → `text-amber-300`

- Lines starting with `\[UmbrellaOS` (system messages) → `text-purple-400/90`

- GrimAC lines → `text-fuchsia-300` (the `grim` type)

- Default output → `text-slate-300`



**Command input bar** (bottom, `border-t border-slate-800 mt-4 pt-3`):

- `>` prompt in `text-purple-400 font-bold`

- Text input: `bg-transparent text-white placeholder-slate-600 font-mono`

- "Send" button: `bg-purple-600 hover:bg-purple-500` + `Send` icon (disabled if empty)

- **Up/Down arrow** on the input navigates `commandHistory\[]` — up goes to previous command, down returns toward current



**WebSocket behaviour:**

- On mount: connects to `WS /hosting/servers/{selectedServerId}/console`

- If WS fails/errors: falls back to HTTP `POST /api/v1/servers/{id}/command`

- On server switch: disconnects current WS, reconnects to new server

- Status tracked as `connecting | connected | offline`



---



## 9. AI OPS PAGE



### Layout and Sub-tabs



Four tabs in a scrollable `overflow-x-auto` row:



| Tab | Icon | Accent | Description |

|---|---|---|---|

| Incident Copilot (Chat) | `Bot` | cyan | Main chat UI with AI |

| Crash Dumps \& Triage | `Flame` | amber | Crash reports with count badge |

| Post-Mortem Generator | `FileText` | indigo | AI-generated incident docs |

| Model Router \& Constitution | `Sliders` | emerald | Provider switching + system prompt |



Active tab: `bg-slate-800 border border-slate-700 shadow-sm` + accent text colour.



### Copilot Chat Tab



Layout: `grid-cols-1 lg:grid-cols-4 gap-6` — chat takes 3 cols, sidebar takes 1 col.



**Chat area** (`h-\[580px] rounded-xl border-slate-800 bg-\[#0c1017] overflow-hidden flex flex-col`):

- Message bubbles with icons: `Sparkles` in `bg-cyan-950/60 border-cyan-500/40` for AI; `User` in `bg-indigo-950/60 border-indigo-500/40` for staff

- AI messages: left-aligned. Staff messages: right-aligned (`flex-row-reverse`)

- Typing indicator: three animated dots when AI is responding

- Input bar at bottom: textarea + "Send" button (`bg-cyan-600`)



**Sample prompt chips** (5 clickable pills that fill the input):

- "Why is anarchy-s2 dropping TPS below 18?"

- "Check alt accounts and client brand for VoidReaper\_X"

- "Analyze the ender crystal crash from 04:12 UTC"

- "How many players are online on US vs EU proxies?"

- "Recommend JVM memory flags for 600 player Skyblock node"



**Sidebar** (1 col): recent chat sessions list + suggested actions panel



### Crash Dumps Tab



Each crash report card (`border-slate-800 bg-\[#0c1017] p-5 space-y-4 rounded-xl`):

- Severity badge: CRITICAL → rose; HIGH → orange; MEDIUM → amber

- Server name + timestamp + `status` pill (INVESTIGATING / RESOLVED / ACKNOWLEDGED)

- Stack trace snippet in a `bg-slate-900 font-mono text-\[11px] max-h-32 overflow-y-auto` block

- "Run AI Diagnosis" button → calls `api.diagnoseCrash(crashId)` — fills diagnosis panel below



### Post-Mortem Generator Tab



Form to generate a formal incident document:

- Select crash report from dropdown

- Affected services list

- Timeline inputs

- "Generate Post-Mortem" → AI produces structured markdown document



### Model Router Tab



- Active provider selector: radio-style chips for `gemini\_flash` | `anthropic\_claude` | `openrouter\_deepseek`

- "Strict Safety Guard" toggle

- Max tokens slider `min=256 max=8192`

- System prompt / AI constitution text — editable textarea with current constitution text

- "Save Model Config" button



---



## 10. PLAYERS PAGE



### Header stats row (`grid-cols-1 sm:grid-cols-4 gap-4`):

Each card `bg-\[#0d1117] border-slate-800 rounded-xl p-4`:

1\. **Total Profiles** — `Users` icon cyan. Subline: "Indexed across PostgreSQL"

2\. **Active Sessions** — `Activity` icon emerald. Shows online count

3\. **Flagged Accounts** — `ShieldAlert` icon rose. Count of suspicion > 50 or alts > 1

4\. **VPN Connections** — `Globe` icon amber. Count of `isVpn === true`



### Filter row:

- Search input with `Search` icon (name, UUID, IP)

- Filter chips: `ALL | ONLINE | FLAGGED` — `FLAGGED` = suspicion > 50 OR altCount > 1



### Player table columns:

- **Player**: avatar initial + username bold + UUID mono below

- **Status**: `ONLINE` green pill / `OFFLINE` slate

- **Suspicion Score**: `0–100` coloured badge — `< 30` emerald; `30–60` amber; `> 60` rose

- **Alt Accounts**: count badge — `> 1` shown in amber, `0–1` slate

- **Current Server**: clickable chip that jumps to console for that server (only shows if online)

- **HWID**: truncated hash in mono `text-slate-400`

- **Last Seen**: relative time

- **Actions**: `Eye` (view profile) + `Ban` icon (opens PunishModal pre-filled with username)



---



## 11. VERIFICATION PAGE



### Manual Link form (inline, toggled by "Create Manual Link" button):

- Discord ID field + Minecraft Username field

- Submit → calls `api.manualLinkDiscord()` + adds to list



### Verification links table:

Columns: Discord (tag + ID) | Minecraft (username + UUID) | Verified By | Linked At | Status | Actions



- **Verified By** badge: `BOT\_CODE` cyan / `MANUAL\_STAFF` amber / `OAUTH` emerald

- **Status**: `VERIFIED` emerald / `PENDING\_CODE` amber / `EXPIRED` rose

- **Actions**: Unlink button — `Unlink` icon, calls `api.unlinkAccount(id)` + `addToast`



---



## 12. STAFF PAGE



### Invite Staff form (in a slide-down panel when "Invite Staff Member" clicked):

- Discord ID input

- Role `<select>`: SUPERADMIN | ADMIN | MODERATOR | SUPPORT | DEVELOPER | VIEWER

- Submit → calls `api.inviteStaff()`



### Staff table:

Columns: Discord (avatar + tag) | Role | Minecraft Link | 2FA | Added | Status | Actions



- **Role badges** with colours: SUPERADMIN → rose; ADMIN → amber; MODERATOR → cyan; SUPPORT → slate; DEVELOPER → indigo; VIEWER → slate/dim

- **Avatar**: `<img>` with Discord CDN URL or default avatar

- **2FA**: `CheckCircle2` green (enabled) or `AlertTriangle` amber (disabled)

- **Status**: ACTIVE emerald / SUSPENDED rose

- Role filter chips above table: ALL | SUPERADMIN | ADMIN | MODERATOR | etc.



---



## 13. AUDIT LOG PAGE



### Header actions:

- Search field + level filter `<select>` + source filter `<select>`

- **Export Logs button** (`Download` icon) — downloads `umbrella-logs-{timestamp}.json`

- Refresh button (calls `api.getLogs()`)



### Log levels and colours:



| Level | Badge colour |

|---|---|

| `AUDIT` | cyan |

| `GRIM` | fuchsia |

| `COMMAND` | purple |

| `WARN` | amber |

| `ERROR` | rose |

| `INFO` | slate |

| `DEBUG` | slate/dim |



### Log entry row:

- Level badge (mono, coloured as above)

- Source: `api-gateway` / `proxy-us-01` / `survival-alpha` / etc. — in a grey pill

- Trace ID: `tr\_abc123` in `font-mono text-\[10px] text-slate-500`

- Timestamp: `text-slate-500 font-mono text-\[10px]`

- Message: `text-slate-200`

- Expandable `ChevronDown` to show `metadata` JSON if present



---



## 14. CSS / VISUAL PATTERNS



### Font stack (`index.css`)

```css

body { font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif; }

code, pre, .font-mono { font-family: 'JetBrains Mono', monospace; }

.font-display { font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif; }

```



### Custom scrollbars

```css

::-webkit-scrollbar { width: 6px; height: 6px; }

::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.6); }

::-webkit-scrollbar-thumb { background: rgba(71, 85, 105, 0.6); border-radius: 3px; }

::-webkit-scrollbar-thumb:hover { background: rgba(100, 116, 139, 0.9); }

```



### Scanline animation (console)

```css

@keyframes scanline {

  0% { transform: translateY(-100%); }

  100% { transform: translateY(1000%); }

}

.scanline-effect::after {

  content: ""; position: absolute; top: 0; left: 0; right: 0; height: 2px;

  background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.25), transparent);

  animation: scanline 8s linear infinite;

  pointer-events: none;

}

```



### Common repeated patterns



**Status dot** (all uses):

- Online: `bg-emerald-400 shadow-\[0\_0\_8px\_rgba(52,211,153,0.6)]` or `animate-pulse`

- Warning: `bg-amber-400 animate-pulse`

- Restarting: `bg-cyan-400 animate-spin`

- Offline: `bg-rose-500`



**Page section header pattern** (consistent across all views):

```

flex h-8 w-8 rounded-lg border border-{colour}-500/30 bg-{colour}-950/40 text-{colour}-400

  + h-4 w-4 icon inside

→ h1 text-base/xl font-bold text-white tracking-tight font-display

→ p text-xs text-slate-400

```



**Sub-tab button pattern**:

```

Active:   bg-slate-800 text-{accent}-400 border border-slate-700 shadow-sm

Inactive: text-slate-400 hover:bg-slate-900 hover:text-slate-200

Container: border-b border-slate-800 pb-2 overflow-x-auto flex items-center gap-2

```



**Info/status banner pattern** (used in GrimAC, Alt Detection, Appeals tabs):

```

rounded-xl border border-{colour}-500/30 bg-\[#0c1017] p-4 flex items-center justify-between

  Left: h-9 w-9 icon box + title h3 text-sm font-bold + description p text-xs text-slate-400

  Right: status/count indicator

```



**Table pattern** (punishments, overview servers, players):

```

rounded-xl border border-slate-800 bg-\[#0c1017] overflow-hidden

thead: border-b border-slate-800 bg-slate-900/60 font-mono text-\[11px] text-slate-400 py-3 px-4

tbody: divide-y divide-slate-800/60

tr: hover:bg-slate-900/40 transition-colors

```



**Secret input pattern**:

```

relative div → input type="password" text-cyan-300 font-mono pl-3 pr-10 + Eye/EyeOff button absolute right-3 top-2.5

```



**Boolean toggle pill pattern**:

```

Enabled:  bg-emerald-950/60 text-emerald-300 border-emerald-500/30  (hover → suggests rose)

Disabled: bg-slate-900 text-slate-400 border-slate-800

```



---



## 15. PRIORITY PORT LIST



| Priority | Item | Source | Effort |

|---|---|---|---|

| 🔴 P0 | Toast system (5 types incl. `grim`) | Both | Medium |

| 🔴 P0 | Punishment / Ban Modal | Both | Low |

| 🔴 P0 | Broadcast Modal | Both | Low |

| 🔴 P0 | Sidebar live server instances panel | CC Sidebar | Low |

| 🟠 P1 | Three-zone Header | CC Header | Medium |

| 🟠 P1 | Account Modal (profile + backend + keys) | CC AccountModal | Medium |

| 🟠 P1 | Command Palette (⌘K) | Both | Low |

| 🟠 P1 | Overview emergency alert banner | CC OverviewView | Medium |

| 🟠 P1 | Overview server table + Quick Actions column | CC OverviewView | Medium |

| 🟠 P1 | Console command history + filter tabs + export | CC ConsoleView | Medium |

| 🟠 P1 | AI Copilot sample prompt chips | CC AIOperationalView | Trivial |

| 🟠 P1 | Players filter chips (ALL/ONLINE/FLAGGED) | CC PlayersView | Low |

| 🟡 P2 | Moderation 4-sub-tab layout | CC ModerationView | High |

| 🟡 P2 | Moderation punishments table (full columns) | CC ModerationView | Medium |

| 🟡 P2 | Moderation GrimAC live stream tab | CC ModerationView | Medium |

| 🟡 P2 | Moderation alt rings tab | CC ModerationView | Medium |

| 🟡 P2 | Moderation appeals AI triage tab | CC ModerationView | Medium |

| 🟡 P2 | Settings left-nav + right-form layout | CC SettingsView | High |

| 🟡 P2 | Settings all 9 categories wired to backend | CC SettingsView | High |

| 🟡 P2 | Settings feature flags tab with rollout slider | CC SettingsView | Medium |

| 🟡 P2 | DisconnectedBanner retry button | Both | Low |

| 🟡 P2 | AI Crash Dumps tab | CC AIOperationalView | High |

| 🟡 P2 | Sidebar live badge counts (moderation/AI/players) | CC Sidebar | Low |

| 🟡 P2 | Sidebar collapse toggle (Gemini icon-only mode) | Gemini | Low |

| 🟡 P2 | Players suspicion score + HWID + current server col | CC PlayersView | Low |

| 🟡 P2 | Audit log export button | CC AuditView | Low |

| 🟡 P2 | Verification manual link form | CC VerificationView | Low |

| 🟡 P2 | Staff invite form + role-colour badges | CC StaffView | Low |

| 🟡 P2 | Custom scrollbars + font stack CSS | Both | Trivial |

| 🟡 P2 | Overview 6-stat row (RAM, bans, appeals, flags) | CC | Low |

| 🟢 P3 | Automation + CreateCronModal | Both | High |

| 🟢 P3 | API Hub + CreateApiKeyModal | Both | Medium |

| 🟢 P3 | Discord bridge view | Gemini | High |

| 🟢 P3 | AI Post-Mortem generator tab | CC | High |

| 🟢 P3 | AI Model Router config tab | CC | Medium |

| ⚪ P4 | Snapshots view | Both | Very High |

| ⚪ P4 | Topology / cluster map view | CC | Very High |

| ⚪ P4 | Translation management view | Both | High |

