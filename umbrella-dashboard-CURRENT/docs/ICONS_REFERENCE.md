# UmbrellaOS Dashboard — Master Icon & Custom Vector Reference

This document catalogs all custom vector emblems, branded components, and Lucide icons utilized throughout the **UmbrellaOS Command Center**, detailing their component mappings, semantic roles, color schemes, and user interface workflows.

---

## 1. Custom Vector Brand & Subsystem Icons

All custom brand icons are located in `src/components/common/UmbrellaIcons.tsx` (and re-exported from `UmbrellaLogo.tsx`).

### A. `UmbrellaLogo` (Master OS Shield & Hex Emblem)
- **Component Source:** `src/components/common/UmbrellaLogo.tsx`
- **Design Archetype:** Geometric Cyber-Shield with Umbrella Canopy & Terminal J-Hook Node.
- **Locations Used:**
  - **Header Brand Bar** (`src/components/layout/Header.tsx`)
  - **Login Portal & Staff Gateway** (`src/components/auth/LoginView.tsx`)
- **Visual Features:**
  - Radial cyan ambient glow backdrop (`bg-cyan-500/25 blur-[6px]`)
  - Multi-faceted canopy wings with custom linear gradients (`#umbrella_grad_left`, `#umbrella_grad_right`, `#umbrella_grad_center`)
  - Central spine with stroke width `2px` and cybernetic J-hook terminal with glowing circular node (`#38bdf8`)
  - Supports configurable sizing (`sm`: 24px, `md`: 32px, `lg`: 44px, `xl`: 56px) and optional subtext badge.

### B. `UmbrellaBotIcon` (Discord Gateway & AI Copilot Agent)
- **Component Source:** `src/components/common/UmbrellaIcons.tsx`
- **Design Archetype:** Cybernetic bot helmet chassis with an integrated top umbrella canopy antenna, dual glowing optical visor eyes, audio receiver nodes, and an active HUD waveform.
- **Locations Used:**
  - **Sidebar Navigation**: Discord Hub item (`src/components/layout/Sidebar.tsx`)
  - **Discord Hub View**: Header banner and bot gateway telemetry (`src/components/discord/DiscordView.tsx`)
  - **AI Intelligence & Copilot**: Assistant avatar badge

### C. `UmbrellaCoreIcon` (JVM Bridge & Multi-Node Cluster Kernel)
- **Component Source:** `src/components/common/UmbrellaIcons.tsx`
- **Design Archetype:** Multi-core silicon CPU processor die with North/South/East/West bus traces and an integrated central micro-umbrella microprocessor silicon core.
- **Locations Used:**
  - **Sidebar Pinned Footer**: Pinned Umbrella Core cluster status indicator (`src/components/layout/Sidebar.tsx`)
  - **Cluster Overview**: JVM heap and thread health metrics
  - **Backend Bridge Status**: Node connection indicator

### D. `UmbrellaPluginIcon` (Minecraft Plugin Bytecode & Hot-Reload JAR)
- **Component Source:** `src/components/common/UmbrellaIcons.tsx`
- **Design Archetype:** Isometric cybernetic plugin package cube with an embossed umbrella rib stamp, internal module partition lines, and socket contact connector dots.
- **Locations Used:**
  - **Sidebar Navigation**: Plugins item (`src/components/layout/Sidebar.tsx`)
  - **Plugins View**: Header title banner and bytecode telemetry (`src/components/plugins/PluginsView.tsx`)
  - **Upload Plugin Modal**: Drag-and-drop target emblem

---

## 2. Master Lucide Icon Registry

| Icon Name | Lucide Identifier | Primary Module & Location | Semantic Role & UI Function | Styling & Color Code |
| :--- | :--- | :--- | :--- | :--- |
| **Activity** | `Activity` | Overview, Topology, Players | Cluster TPS, tick frequency, and active player session pulse | `text-emerald-400` / `text-cyan-400` |
| **AlertCircle** | `AlertCircle` | Toast Alerts, GrimAC, Appeals | Error states, validation banners, and high-severity violations | `text-rose-400` / `text-amber-400` |
| **AlertOctagon** | `AlertOctagon` | Overview, Console, Moderation | Immediate system emergency, memory leak alerts, and fatal crash triggers | `text-rose-500 animate-pulse` |
| **AlertTriangle** | `AlertTriangle` | Topology, Snapshots, Punishment Modal | Warning indicators, disk exhaustion alerts, and irreversible action notices | `text-amber-400` |
| **ArrowLeft** | `ArrowLeft` | Modal Pagination, Wizard Navigation | Back navigation step | `text-slate-400 hover:text-white` |
| **ArrowRight** | `ArrowRight` | Modal Step Forward, Breadcrumbs | Step forward progression and redirection | `text-slate-400 hover:text-white` |
| **ArrowUpRight** | `ArrowUpRight` | Overview, External Links, Discord Hub | External link redirects and jump-to-source triggers | `text-cyan-400` / `text-slate-500` |
| **Ban** | `Ban` | Moderation, Players, PunishModal | Player bans, IP/HWID hardware blacklists, and active punishment tags | `text-rose-400` / `bg-rose-950/80` |
| **Bell** | `Bell` | Header, Overview, Notification Feed | Notification drawer trigger and unread alerts count | `text-slate-300 hover:text-white` |
| **Bot** | `Bot` | Discord Hub, Automation, AI View | Discord bot status, autonomous background worker tasks | `text-indigo-400` / `text-cyan-400` |
| **BrainCircuit** | `BrainCircuit` | AI Intelligence, Copilot, Settings | Multi-LLM provider routing and deep reasoning diagnostics | `text-purple-400` / `text-cyan-400` |
| **Camera** | `Camera` | Snapshots, Backup History | Point-in-time state capture and backup trigger | `text-cyan-400` |
| **Check** | `Check` | Settings, Form Controls, Modals | Checkbox active confirmation, setting saved state | `text-emerald-400` |
| **CheckCircle2** | `CheckCircle2` | Toast Notification, Health Indicators | Successful API execution, healthy instance status | `text-emerald-400` |
| **ChevronDown** | `ChevronDown` | Dropdowns, Accordions, Header User Menu | Select dropdown chevron, collapsible panel indicator | `text-slate-400` |
| **ChevronLeft** | `ChevronLeft` | Table Pagination, Calendar Controls | Previous page in player and log tables | `text-slate-400 hover:text-white` |
| **ChevronRight** | `ChevronRight` | Table Pagination, Sidebar Submenus | Next page in player tables, item drill-down | `text-slate-400 hover:text-white` |
| **Clock** | `Clock` | Players, Snapshots, Moderation | Playtime duration, punishment expiry, backup schedule time | `text-slate-500` / `text-amber-300` |
| **Code2** | `Code2` | API Hub, Plugins, Console | REST endpoint schema view, JSON payload inspector | `text-cyan-400` |
| **Copy** | `Copy` | API Hub, Settings, Verification Modal | Copy API keys, player UUIDs, and webhook URLs to clipboard | `text-slate-400 hover:text-cyan-300` |
| **CornerDownLeft** | `CornerDownLeft` | Console, AI Copilot Input | Enter key submit indicator for CLI commands and chat | `text-slate-500` |
| **Cpu** | `Cpu` | Overview, Topology, Server Nodes | CPU core utilization percentage and thread allocation | `text-cyan-400` / `text-purple-400` |
| **Database** | `Database` | Settings, API Hub, Topology | PostgreSQL and Redis cluster connections, persistence metrics | `text-cyan-400` / `text-indigo-400` |
| **Download** | `Download` | Snapshots, Plugins, Logs | Snapshot tarball download and log export | `text-cyan-400 hover:text-cyan-300` |
| **ExternalLink** | `ExternalLink` | Discord Hub, Appeals, MC-Heads | Outbound links to Discord, Minecraft player lookups | `text-slate-400 hover:text-cyan-300` |
| **Eye** | `Eye` | Settings, Auth, API Key Modal | Reveal masked API secret keys and database credentials | `text-slate-400 hover:text-slate-200` |
| **EyeOff** | `EyeOff` | Settings, Auth, API Key Modal | Mask secret keys with password dots | `text-slate-400 hover:text-slate-200` |
| **FileCheck** | `FileCheck` | Verification View, Appeals | Verified staff identity, accepted ban appeal ticket | `text-emerald-400` |
| **FileCode** | `FileCode` | Plugins, Console, Diagnostics | Plugin `.yml` configuration editor and bytecode inspector | `text-cyan-400` |
| **FileText** | `FileText` | Crash Dumps, Audit Logs, Appeals | Stack trace log reader and appeal evidence notes | `text-slate-400` |
| **Filter** | `Filter` | Players, Moderation, Audit Log | Table column filtering by severity, rank, server scope | `text-slate-400` |
| **Fingerprint** | `Fingerprint` | Moderation, Players, Alt Clusters | HWID hardware hash and alt account fingerprinting | `text-purple-400` |
| **Flame** | `Flame` | Overview, Settings, Failover View | High stress / emergency failover and critical spike status | `text-amber-400` / `text-rose-400` |
| **Gamepad2** | `Gamepad2` | Players, Discord Hub, Topology | In-game Minecraft client session indicator | `text-emerald-400` |
| **Globe** | `Globe` | Topology, Overview, Language Hub | Velocity proxy ingress and player geographical location | `text-blue-400` / `text-emerald-400` |
| **HardDrive** | `HardDrive` | Snapshots, Topology, Storage Settings | Disk usage per server and S3 bucket quota | `text-cyan-400` / `text-slate-400` |
| **Hash** | `Hash` | Discord Hub, Verification | Discord text channels and ticket IDs | `text-slate-500` / `text-indigo-400` |
| **HeartHandshake** | `HeartHandshake` | Verification, Staff Roles | Staff account linking and verification confirmation | `text-emerald-400` |
| **History** | `History` | Snapshots, Audit Log, Moderation | State rollback points, punishment history records | `text-cyan-400` / `text-slate-400` |
| **Info** | `Info` | Toasts, Tooltips, System Help | Informational banners and field descriptions | `text-cyan-400` |
| **Key** | `Key` | API Hub, Auth, Security Settings | Scoped API bearer keys, Discord bot tokens | `text-amber-400` / `text-cyan-400` |
| **Languages** | `Languages` | Translation View, Global Chat | Real-time chat translation and language dictionary selector | `text-indigo-400` / `text-cyan-400` |
| **Layers** | `Layers` | Plugins, Topology, Automation | Server hierarchy layers and plugin dependency trees | `text-slate-400` |
| **LayoutDashboard**| `LayoutDashboard`| Sidebar, Overview | Command Center dashboard main tab | `text-cyan-400` |
| **Link** | `Link` | Discord Hub, Verification, Players | Linked account associations and webhook connections | `text-cyan-400` / `text-indigo-400` |
| **Lock** | `Lock` | Overview, Security Settings, Auth | Lockdown mode active, restricted admin routes | `text-amber-400` / `text-rose-400` |
| **Megaphone** | `Megaphone` | Header, BroadcastModal, Overview | Global cluster broadcast announcements | `text-cyan-400` |
| **MessageSquare** | `MessageSquare` | Discord Hub, Appeals, Staff Chat | In-game chat stream and appeal discussion thread | `text-slate-400` / `text-indigo-400` |
| **Network** | `Network` | Topology, Routing, Velocity | Multi-server node graph and proxy topology | `text-cyan-400` |
| **Palette** | `Palette` | Header, Settings Preferences | Dashboard design template and theme selector | `text-cyan-400` / `text-purple-400` |
| **PanelLeftClose** | `PanelLeftClose`| Header | Collapse sidebar toggle | `text-slate-400` |
| **PanelLeftOpen** | `PanelLeftOpen` | Header | Expand sidebar toggle | `text-slate-400` |
| **Pause** | `Pause` | Console, Snapshots, Automation | Pause live stream or suspend automated cron job | `text-amber-400` |
| **Play** | `Play` | Console, Automation, Snapshots | Resume live log feed or manually run automated task | `text-emerald-400` |
| **Plus** | `Plus` | API Hub, Staff, Automation | Create new record (API key, user, cron task) | `text-cyan-400` |
| **Radio** | `Radio` | Overview, Discord, Plugins | Real-time live socket connection state | `text-emerald-400 animate-pulse` |
| **RefreshCw** | `RefreshCw` | All Views, Table Headers | Manual data refresh and sync trigger | `text-slate-400 hover:text-cyan-400` |
| **RotateCcw** | `RotateCcw` | Snapshots, Server Controls | Server reboot and snapshot state restoration | `text-amber-400` |
| **Save** | `Save` | Settings, Config Editors | Save form values or configuration files | `text-emerald-400` |
| **Search** | `Search` | Header, CommandPalette, All Tables | Global search and table filter input | `text-slate-400` |
| **Send** | `Send` | Console, Discord Chat, Broadcast | Submit CLI command or send chat broadcast | `text-cyan-400` |
| **Server** | `Server` | Topology, Console, Overview | Individual Minecraft server node | `text-cyan-400` / `text-emerald-400` |
| **Shield** | `Shield` | Verification, Staff, Anticheat | Staff rank badge and security level | `text-purple-400` / `text-indigo-400` |
| **ShieldAlert** | `ShieldAlert` | Moderation, GrimAC, Appeals | Anticheat violation alerts and active ban appeals | `text-rose-400` / `text-amber-400` |
| **ShieldCheck** | `ShieldCheck` | Staff View, Verification | Verified staff member, 2FA security confirmed | `text-emerald-400` |
| **Sliders** | `Sliders` | Settings, Server Properties | Configuration tuning and preference adjustments | `text-slate-400` |
| **Sparkles** | `Sparkles` | AI Operations, Copilot, Templates | AI-generated recommendations and design theme presets | `text-cyan-400` / `text-purple-400` |
| **Terminal** | `Terminal` | Console, Command Runner | RCON interactive command line interface | `text-emerald-400` / `text-cyan-400` |
| **Trash2** | `Trash2` | Moderation, Plugins, API Keys | Delete resource or purge historical records | `text-rose-400 hover:text-rose-300` |
| **Upload** | `Upload` | Plugins, Snapshots | Upload `.jar` plugin or restore backup file | `text-cyan-400` |
| **UserCheck** | `UserCheck` | Verification, Staff View | Approved user identity verification | `text-emerald-400` |
| **Users** | `Users` | Players, Staff, Moderation | Player list and staff team roster | `text-cyan-400` / `text-slate-400` |
| **Volume2** | `Volume2` | Discord Hub, Voice Telemetry | Discord voice channel status and bitrate metrics | `text-indigo-400` |
| **Wifi** | `Wifi` | Players, Topology | Player ping / network latency measurement | `text-emerald-400` / `text-amber-400` |
| **X** | `X` | Modals, Search Inputs, Toast Alerts | Dismiss dialog or clear input | `text-slate-400 hover:text-white` |
| **Zap** | `Zap` | Header, Overview, AI View | Real-time socket event trigger, instant failover | `text-cyan-400` / `text-amber-400` |
