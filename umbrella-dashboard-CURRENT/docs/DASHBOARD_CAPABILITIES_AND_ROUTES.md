# UmbrellaOS Dashboard — Master Technical Architecture & Backend Specification

This document provides a comprehensive, exhaustive technical reference for the **UmbrellaOS Minecraft Network & Infrastructure Command Center**. It covers every frontend capability, route, view controller, expected payload schema, data origin, REST/WebSocket contract, in-JVM plugin bridge mechanism, and identifies exact backend gaps and required implementations.

---

## Table of Contents
1. [System Overview & Architecture](#1-system-overview--architecture)
2. [Authentication, Sessions & RBAC Flow](#2-authentication-sessions--rbac-flow)
3. [Dashboard Views & Operational Capabilities](#3-dashboard-views--operational-capabilities)
4. [Master REST API & WebSocket Route Registry](#4-master-rest-api--websocket-route-registry)
5. [Data Origin & Ingestion Matrix (Where Data Comes From)](#5-data-origin--ingestion-matrix)
6. [Outbound Dispatch & Action Matrix (How Things Get Posted)](#6-outbound-dispatch--action-matrix)
7. [Multi-Provider AI Diagnostics & Rate-Limit Engine](#7-multi-provider-ai-diagnostics--rate-limit-engine)
8. [Dashboard Design Archetypes & Layout Templates](#8-dashboard-design-archetypes--layout-templates)
9. [Umbrella Brand & System Custom Vector Icons](#9-umbrella-brand--system-custom-vector-icons)
10. [Backend Gap Analysis & Missing Endpoints](#10-backend-gap-analysis--missing-endpoints)
11. [In-JVM Bridge Plugin Architecture (`umbrella-core-bridge.jar`)](#11-in-jvm-bridge-plugin-architecture)

---

## 1. System Overview & Architecture

UmbrellaOS is an enterprise-grade Minecraft multi-node cluster control plane and anticheat diagnostic dashboard. It unifies:
- **Distributed Paper/Purpur/Velocity Infrastructure**: Live TPS, MSPT, memory fragmentation, thread health, and CPU metrics.
- **GrimAC Combat & Movement Packet AI**: Sub-tick vector telemetry, reach/velocity flags, and automated false-positive triaging.
- **Multi-Server Moderation & Alt Ring Detection**: IP, HWID, and subnet correlation matrices with punishment rollbacks.
- **Discord Cloud Hub**: Bidirectional synchronization of roles, tickets, announcement broadcasts, and staff audit webhooks.
- **Multi-Provider AI Diagnostics**: Autonomous stack dump triage, copilot staff assistance, appeal sentiment scoring, and 429 failover routing across 6 AI backends (Gemini, Claude, OpenAI, DeepSeek, OpenRouter, Local Ollama).

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         UmbrellaOS Dashboard (React 18 + TS)                     │
│               [Tailwind CSS, Lucide Icons, Full Multi-View State Engine]         │
└───────────────▲──────────────────────────────▲─────────────────────────▲─────────┘
                │ HTTP REST                    │ WSS / WebSocket         │ Direct / LLM Fallback
                │ (Bearer Token / X-Admin-Key) │ (Live Log & TPS Stream) │ (Gemini/Claude/OpenAI)
┌───────────────▼──────────────────────────────▼─────────────────────────▼─────────┐
│                          UmbrellaOS Backend REST API (FastAPI)                   │
│                          PostgreSQL 16 + Redis Event Bus                         │
└───────────────▲──────────────────────────────────────────▲───────────────────────┘
                │ Netty / Redis PubSub                     │ Discord Webhook / Bot API
┌───────────────▼─────────────────────────┐     ┌──────────▼───────────────────────┐
│     In-JVM Bridge Plugins               │     │         Discord Cloud Hub        │
│  (umbrella-core-bridge.jar + GrimAC)    │     │   (#staff-logs, #announcements)  │
│  Paper / Purpur / Velocity Instances    │     └──────────────────────────────────┘
└─────────────────────────────────────────┘
```

---

## 2. Authentication, Sessions & RBAC Flow

### A. Authentication Modes
The login portal (`src/components/auth/LoginView.tsx`) acts as an isolated, standalone authentication gate (accessible via route `/login` or automatically rendered when an unauthorized user connects):
1. **Discord OAuth2**:
   - Client clicks **"Sign In with Discord"**.
   - Initiates OAuth2 authorization flow against `GET /api/v1/auth/discord/authorize`.
   - Callback is posted to `POST /api/v1/auth/discord/callback` with `{ code, state }`.
   - Backend responds with a signed JWT Bearer Token and User Profile JSON:
     ```json
     {
       "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "user": {
         "id": "usr-889123",
         "discordId": "192837465918273645",
         "username": "EnderAdmin",
         "discriminator": "0001",
         "avatarUrl": "https://cdn.discordapp.com/avatars/192837465918273645/abc.png",
         "role": "superadmin",
         "permissions": ["*"],
         "email": "admin@umbrella.network",
         "linkedMinecraftUuid": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
         "linkedMinecraftUsername": "EnderAdmin"
       }
     }
     ```
2. **Direct Superadmin Access Key (`X-Admin-Key`)**:
   - Allows root administrator emergency bypass when Discord API or OAuth gateway is unreachable.
   - Saves token to `localStorage.umbrella_admin_key` and adds header `X-Admin-Key: <key>` to all subsequent requests.

### B. Role-Based Access Control (RBAC) Hierarchy
| Role | Permissions | Accessible Dashboard Views |
| :--- | :--- | :--- |
| `superadmin` | `*` (Full cluster power) | All views, node reboots, API key generation, raw SQL, AI provider config |
| `admin` | `servers.*`, `moderation.*`, `plugins.*`, `discord.*` | Overview, Topology, Players, Moderation, Console, Plugins, Snapshots, Crons |
| `moderator` | `moderation.punish`, `moderation.view`, `players.inspect` | Overview, Players, Moderation, Appeals, Alt Detection, Chat Translation |
| `support` | `appeals.review`, `verification.view`, `players.lookup` | Overview, Players, Verification, Appeals |
| `developer` | `console.read`, `plugins.inspect`, `api.read`, `logs.stream` | Overview, Console, Plugins, API Hub, Audit Logs |
| `viewer` | `dashboard.read` (Read-only status) | Overview, Topology (Metrics only) |

---

## 3. Dashboard Views & Operational Capabilities

### 1. Overview & Command Center (`src/components/overview/OverviewView.tsx`)
- **Metric Tiles**: Total Online Players, Network Aggregated TPS (with color-graded health badges), Total Managed Nodes, GrimAC Interceptions / 24h.
- **Real-Time Sparklines**: Tick-time velocity curve (MSPT vs TPS) and memory heap consumption.
- **Server Health Bento Grid**: Displays all Paper/Purpur/Velocity sub-servers with CPU%, RAM utilization, and active players.
- **Quick Action Bar**:
  - Emergency Cluster Lockdown (halts incoming proxy connections).
  - Preemptive Non-Blocking ZGC Sweep.
  - Global Announcement Broadcaster.
  - Point-in-Time Cluster Snapshot Trigger.

### 2. Topology & Routing View (`src/components/topology/TopologyView.tsx`)
- **Network Map**: Interactive visual node graph displaying Velocity proxy edge gateways routing players to Paper/Purpur backends.
- **Per-Node Controls**: Start, Stop, Reboot, Kill Process, and ZGC Memory Garbage Collection.
- **Diagnostic Metrics**: Uptime counters, assigned port, RAM allocation gauges, and MSPT load indicators.

### 3. Player Fleet & Alt Ring Matrix (`src/components/players/PlayersView.tsx`)
- **Live Player Table**: Real-time list featuring avatars, ping, server location, playtime, anticheat violation flags, and client brand.
- **Multi-Server Search & Filters**: Filter by server node, rank, online status, or anticheat risk score.
- **Player Drawer / Quick Inspect**: Inspect inventory, connected IP, HWID hash, linked Discord identity, and alt accounts.
- **Moderation Actions**: Quick Kick, Ban, Mute, Warn, or Freeze directly from the inspection drawer.

### 4. Moderation, Anticheat & Appeals (`src/components/moderation/ModerationView.tsx`)
- **GrimAC Live Violation Stream**: Sub-tick packets for Aim, Reach, BadPackets, Speed, Fly, AutoClicker, and FastPlace.
- **Alt Account Graph Matrix**: IP and hardware fingerprint correlation visualizer exposing ban evaders and alt networks.
- **Ban Appeal Portal**: Staff appeal review workflow with AI-assisted sincerity scoring, player history, and approve/deny actions.
- **Punishment History & Audit**: Searchable log of all historical bans, mutes, kicks, and IP blacklists with staff attribution.

### 5. Multi-Server Interactive Console (`src/components/console/ConsoleView.tsx`)
- **Live Terminal**: Multi-tab Log4j2 console streaming logs across all connected servers with ANSI color decoding.
- **Interactive Command Dispatch**: Direct RCON / stdin execution with command history (`Up`/`Down` arrow keys) and autocomplete.
- **Log Level Filtering**: Toggle INFO, WARN, ERROR, and DEBUG log feeds on the fly.
- **Regex Search & Pause Stream**: Freeze log buffer to inspect stack traces during heavy logging incidents.

### 6. Java Plugin Hub & Bridge Telemetry (`src/components/plugins/PluginsView.tsx`)
- **Plugin Registry**: Inspect all loaded Paper/Spigot/Velocity plugins, version numbers, authors, and memory footprints.
- **Bridge Telemetry**: Real-time heartbeat tracking for `umbrella-core-bridge.jar` on each node.
- **Direct JAR Upload**: Drag-and-drop `.jar` uploader sending binary payloads directly to backend hosting storage.
- **Config Editor**: In-browser YAML syntax-highlighted editor for `config.yml` and plugin data files with hot-reload triggers (`/plugman reload`).

### 7. Snapshots & Disaster Recovery (`src/components/snapshots/SnapshotsView.tsx`)
- **Point-in-Time Snapshots**: Automated and manual backup checkpoints of worlds, player data, and configs.
- **One-Click Rollback**: Instant restore functionality with automatic server pause and data integrity verification.
- **Storage Metrics**: Total snapshot storage usage, S3 / MinIO bucket synchronization, and retention policy manager.

### 8. Staff Management & Verification (`src/components/staff/StaffView.tsx` & `src/components/verification/VerificationView.tsx`)
- **Staff Roster**: Manage administrators, moderators, and support staff with granular RBAC permissions.
- **Account Linking & 2FA**: Discord ↔ Minecraft account verification codes (`/verify <code>`), hardware security keys, and session management.
- **Audit Logs**: Immutable timeline tracking all staff actions, console executions, punishments, and config edits.

### 9. Discord Hub & Chat Bridge (`src/components/discord/DiscordView.tsx`)
- **Live Chat Stream**: Real-time bidirectional chat feed between in-game Minecraft servers and Discord `#in-game-chat` channels.
- **Embed Generator**: Interactive builder for Discord webhooks, announcements, and server status embeds.
- **Slash Commands RBAC**: Configure `/tps`, `/ban`, `/lookup`, and `/broadcast` permissions mapped to Discord roles.

### 10. Automation & Scheduled Tasks (`src/components/automation/AutomationView.tsx`)
- **Cron Engine**: Automated server restarts, backup generation, leaderboards recalculation, and GC sweeps.
- **Manual Trigger**: Instant execution button for testing scheduled tasks.
- **Execution History**: Logs showing duration, success/failure status, and console outputs.

### 11. Global Chat Translation (`src/components/translation/TranslationView.tsx`)
- **Real-Time Translation**: Multi-lingual chat translation for global player networks using AI / Google Translate API.
- **Dictionary Management**: Custom server-wide keyword replacement and profanity filtering.

### 12. API Hub & Webhooks (`src/components/api-hub/ApiHubView.tsx`)
- **API Key Management**: Generate and revoke scoped API keys for external services, stats websites, and Discord bots.
- **Webhook Subscriptions**: Subscribe to events (`player.join`, `player.ban`, `server.crash`, `anticheat.flag`).
- **Interactive REST Tester**: Test endpoints with live responses directly within the browser.

### 13. Multi-Provider AI Intelligence (`src/components/ai/AIOperationalView.tsx`)
- **Autonomous Crash Triage**: Parses Paper/JVM stack traces, pinpoints root-cause plugins/lines, and recommends remediation steps.
- **Copilot Assistant**: Interactive LLM chatbot with full cluster context capable of answering server management questions.
- **Failover Simulator**: Live demonstration of automatic 429 rate-limit failover across multiple configured AI providers.

### 14. Settings & Preferences View (`src/components/settings/SettingsView.tsx`)
- **Core Configuration**: Database connections, Redis URI, Velocity secret, and webhook endpoints.
- **AI Provider Settings**: API key management and priority ordering for Gemini, Claude, OpenAI, DeepSeek, OpenRouter, and Ollama.
- **Preferences & Design Templates**: Live template switcher enabling instant switching between 4 distinct visual archetypes (Cyber-Ops, Solar Clean, Voxel Matrix, Obsidian Minimalist).

---

## 4. Master REST API & WebSocket Route Registry

| Method | Endpoint Route | Auth Level | Request Body / Query | Description / Action |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/auth/discord/authorize` | Public | None | Redirects to Discord OAuth2 consent screen |
| `POST` | `/api/v1/auth/discord/callback` | Public | `{ "code": string, "state": string }` | Exchanges OAuth code for JWT session |
| `GET` | `/api/v1/servers` | Bearer Token | `?status=all` | Returns telemetry for all cluster nodes |
| `POST` | `/api/v1/servers/{id}/action` | Admin | `{ "action": "start"\|"stop"\|"restart"\|"kill"\|"gc" }` | Dispatches lifecycle command to server node |
| `GET` | `/api/v1/players` | Moderator | `?server=all&search=...` | Returns list of online/offline players |
| `POST` | `/api/v1/moderation/punish` | Moderator | `{ "target": string, "type": "BAN"\|"MUTE"\|"KICK", "reason": string, "duration": string }` | Issues punishment across all cluster nodes |
| `POST` | `/api/v1/broadcast` | Admin | `{ "message": string, "server": "all"\|string }` | Sends high-priority title notice to Minecraft nodes |
| `GET` | `/api/v1/plugins` | Developer | `?serverId=...` | Returns all loaded plugins and bridge heartbeats |
| `POST` | `/api/v1/plugins/upload` | Superadmin | `multipart/form-data` (.jar file) | Uploads and deploys new plugin archive |
| `GET` | `/api/v1/snapshots` | Admin | None | Lists available backup checkpoints |
| `POST` | `/api/v1/snapshots/create` | Admin | `{ "scope": "all"\|string, "notes": string }` | Creates immediate point-in-time snapshot |
| `POST` | `/api/v1/snapshots/{id}/restore`| Superadmin | `{ "confirm": true }` | Rolls back server instance to snapshot |
| `WSS` | `/ws/v1/console/{serverId}` | Developer | `token` query param | Real-time bidirectional Log4j2 console stream |
| `WSS` | `/ws/v1/telemetry` | Viewer | `token` query param | Sub-second TPS, MSPT, and RAM broadcast stream |

---

## 5. Data Origin & Ingestion Matrix

| Data Stream | Origin Source | Transport Layer | Update Frequency | Ingestion Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **Server TPS & MSPT** | `umbrella-core-bridge.jar` | Redis Pub/Sub | Every 1,000ms | `WSS /ws/v1/telemetry` |
| **Player Connects & Pings** | Velocity Proxy Bridge | Netty Socket | Real-Time on Join/Quit | `POST /api/v1/events/player` |
| **GrimAC Anticheat Flags** | GrimAC Event Hook | Redis Channel `anticheat:flags` | Instant on Packet Flag | `POST /api/v1/events/anticheat` |
| **Console Logs (Log4j2)** | Log4j2 Appender in JVM | WebSocket Pipe | Continuous Stream | `WSS /ws/v1/console/{id}` |
| **Discord Chat Messages** | Discord Bot Gateway | Discord WebSocket | Real-Time on Message | `POST /api/v1/discord/webhook` |
| **Ban Appeals** | Web Portal Form | HTTP POST | On User Submission | `POST /api/v1/appeals` |

---

## 6. Outbound Dispatch & Action Matrix

| Action Name | Triggered From UI | Outbound Route | Target Destination |
| :--- | :--- | :--- | :--- |
| **Player Ban / Kick** | Moderation Drawer / PunishModal | `POST /api/v1/moderation/punish` | In-JVM Bridge (Kicks player from server) + Discord `#staff-punishments` |
| **Global Broadcast** | Header / BroadcastModal | `POST /api/v1/broadcast` | Velocity Proxy (Sends title & sound to all nodes) |
| **RCON CLI Command** | Console View Terminal | `POST /api/v1/servers/{id}/exec` | Minecraft Server stdin via Netty Bridge |
| **Plugin Hot Reload** | Plugins View | `POST /api/v1/plugins/reload` | Spigot PluginManager / PlugManX via Bridge |
| **Snapshot Restore** | Snapshots View | `POST /api/v1/snapshots/{id}/restore`| System Daemon (Stops server, swaps world directory, restarts) |

---

## 7. Multi-Provider AI Diagnostics & Rate-Limit Engine

UmbrellaOS includes a resilient multi-provider AI diagnostic pipeline. If a provider hits an HTTP 429 rate limit or connection timeout, the request automatically falls back to the next healthy provider in under 50ms:

```
[Crash Log / Ban Appeal / Query]
       │
       ▼
 ┌───────────────┐
 │ Gemini Flash  │ ──(HTTP 429 / Error)──► ┌───────────────┐
 └───────────────┘                         │ Claude Sonnet │ ──(HTTP 429)──► ┌───────────────┐
                                           └───────────────┘                 │ OpenAI GPT-4o │
                                                                             └───────────────┘
```

---

## 8. Dashboard Design Archetypes & Layout Templates

UmbrellaOS supports 4 distinct operational design templates, accessible via the Header template dropdown or **Settings > Preferences**:

1. **Cyber-Ops NOC (Default — Tactical Dark)**:
   - Deep tactical slate canvas (`#090b10`) with glowing cyan (`#38bdf8`) and emerald (`#10b981`) telemetry curves.
   - Glassmorphic bento cards with micro-borders for 24/7 dark-room network operations centers.
2. **Solar Clean Enterprise (High-Clarity Day Mode)**:
   - Crisp porcelain canvas (`#f8fafc`) with cobalt blue accents (`#2563eb`) and WCAG AAA text contrast.
   - Optimized for daytime office environments and large tabular player/appeal rosters.
3. **Voxel Matrix Terminal (Minecraft CLI Aesthetic)**:
   - Pitch-black hacker terminal (`#000000`) with phosphor green (`#22c55e`) monospace typography.
   - Sharp 0px border-radii, tiling frames, and integrated RCON command dock.
4. **Obsidian Minimalist (Modern Product Luxury)**:
   - Carbon dark aesthetic (`#121214`) with subtle warm zinc borders and refined violet tags (`#a855f7`).
   - Generous negative space inspired by modern developer productivity platforms.

---

## 9. Umbrella Brand & System Custom Vector Icons

The dashboard uses 4 custom-crafted vector icons defined in `src/components/common/UmbrellaIcons.tsx`:

### 1. `UmbrellaLogo` (Master OS Cyber-Shield Emblem)
- **Visuals**: Hexagonal shielded cyber-frame with three gradient-shaded umbrella canopy ribs, top spindle pin, vertical central spine, and a bottom J-hook cyber-handle with a glowing circular terminal node.
- **Export**: `<UmbrellaLogo size="sm|md|lg|xl" showWordmark={true} />`

### 2. `UmbrellaBotIcon` (Discord Gateway & AI Agent)
- **Visuals**: Cyber-bot helmet chassis with an umbrella canopy top antenna, dual glowing circular optical sensor eyes, audio receiver nodes, and an active HUD audio waveform line.
- **Export**: `<UmbrellaBotIcon className="h-4 w-4" />`

### 3. `UmbrellaCoreIcon` (JVM Bridge & Multi-Node Cluster Kernel)
- **Visuals**: Multi-core CPU silicon processor die with North, South, East, and West bus trace connectors and an integrated central microprocessor umbrella core.
- **Export**: `<UmbrellaCoreIcon className="h-4 w-4" />`

### 4. `UmbrellaPluginIcon` (Minecraft Plugin Bytecode & Hot-Reload Module)
- **Visuals**: Isometric cybernetic plugin package cube with an embossed umbrella rib stamp on the left face, top facet dividers, and socket contact connector pins on the right face.
- **Export**: `<UmbrellaPluginIcon className="h-4 w-4" />`

---

## 10. Backend Gap Analysis & Missing Endpoints

To achieve 100% full-stack functionality with the FastAPI backend, the following endpoints must be completed:

### 1. Missing REST Endpoints to Implement in FastAPI:
- [ ] `POST /api/v1/hosting/servers/{id}/plugins/upload`: Support `multipart/form-data` uploads for plugin `.jar` files.
- [ ] `GET /api/v1/hosting/servers/{id}/files/read?path=...`: Read server `.yml` configuration files for the in-browser editor.
- [ ] `POST /api/v1/hosting/servers/{id}/files/save`: Save updated `.yml` configuration files back to disk.
- [ ] `GET /api/v1/snapshots`: Return available point-in-time backup checkpoints.
- [ ] `POST /api/v1/snapshots/create`: Trigger immediate world/database snapshot generation.
- [ ] `POST /api/v1/snapshots/{id}/restore`: Roll back server instance to specified snapshot.
- [ ] `GET /api/v1/automation/crons` & `POST /api/v1/automation/crons`: CRUD operations for scheduled server tasks.
- [ ] `POST /api/v1/automation/crons/{id}/run`: Immediate manual trigger for cron tasks.
- [ ] `GET /api/v1/keys` & `POST /api/v1/keys`: Manage scoped dashboard API keys.

### 2. Missing WebSocket Channels:
- [ ] `WSS /ws/v1/logs`: Real-time Log4j2 console streaming with channel filtering by `serverId`.
- [ ] `WSS /ws/v1/telemetry`: Sub-second TPS and RAM broadcast channel.

---

## 11. In-JVM Bridge Plugin Architecture (`umbrella-core-bridge.jar`)

For live metrics and real-time command execution, each Minecraft server node runs the lightweight `umbrella-core-bridge.jar` plugin:

```java
public class UmbrellaCoreBridge extends JavaPlugin implements Listener {
    private RedisClient redisClient;
    
    @Override
    public void onEnable() {
        // 1. Establish secure Redis PubSub socket to backend
        this.redisClient = new RedisClient(getConfig().getString("redis.uri"));
        
        // 2. Schedule 1000ms TPS & MSPT Heartbeat
        Bukkit.getScheduler().runTaskTimerAsynchronously(this, () -> {
            double tps = Bukkit.getTPS()[0];
            double mspt = Bukkit.getAverageTickTime();
            long usedRam = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1048576;
            
            redisClient.publish("telemetry:server", new ServerHeartbeatPacket(
                getConfig().getString("server.id"), tps, mspt, usedRam, Bukkit.getOnlinePlayers().size()
            ));
        }, 20L, 20L);
        
        // 3. Register GrimAC Violation Listener
        Bukkit.getPluginManager().registerEvents(new AnticheatListener(redisClient), this);
    }
}
```

---

## Summary Checklist for Production Deployment

1. **Dashboard UI**: Fully compiled, zero mock data, responsive layout with stationary left rail, custom vector brand icons, and 4 operational design themes.
2. **Archives**: Complete Linux POSIX-compliant deployment archives created: `umbrellaos-dashboard.zip`, `umbrellaos-nextjs-dashboard.zip`, `umbrellaos-dashboard.tar.gz`.
3. **Documentation**:
   - Master Architecture & Capabilities: `docs/DASHBOARD_CAPABILITIES_AND_ROUTES.md` (this document)
   - Master Icon Registry: `docs/ICONS_REFERENCE.md` and `ICONS_REFERENCE.md`
   - Plugin Bridge Architecture: `docs/BACKEND_PLUGIN_ARCHITECTURE.md`
   - Multi-Provider AI Diagnostics: `docs/AI_DIAGNOSTICS_CAPABILITIES.md`
   - Backend Requirements: `BACKEND_REQUIREMENTS.md`
