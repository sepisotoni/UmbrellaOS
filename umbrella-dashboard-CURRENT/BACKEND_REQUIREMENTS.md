# UmbrellaOS Command Center — Backend Requirements & Integration Specification

> **Target Audience:** Claude / Backend Engineering Team  
> **Architecture Target:** FastAPI + PostgreSQL + Redis/IPC Socket  
> **Authentication Method:** Header `X-Admin-Key` / Bearer JWT  
> **Status:** Production Dashboard Specification

---

## 1. Overview & Objectives

The **UmbrellaOS Command Center Dashboard** is built as a modular single-pane-of-glass management console for Minecraft server networks running Velocity, Paper/Purpur, and GrimAC anticheat. 

To achieve full operational parity with zero mock fallbacks, the backend FastAPI service must support the following REST endpoints, WebSocket streams, and data schemas.

---

## 2. Authentication & Security Headers

Every request issued by the dashboard includes:
- `X-Admin-Key: <token>`: Passed in API client headers.
- `Authorization: Bearer <jwt>`: Discord OAuth staff token.
- CORS configuration must allow origin header from the dashboard frontend:
  ```python
  from fastapi.middleware.cors import CORSMiddleware

  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"], # Or specific dashboard domain
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

---

## 3. Required REST API Endpoints & Schemas

### 3.1 Overview & Server Topology (`/api/v1/dashboard/overview`)

- **Method:** `GET`
- **Route:** `/api/v1/dashboard/overview`
- **Response Schema:**
```json
{
  "total_players": 148,
  "max_players": 1500,
  "active_servers": 6,
  "total_servers": 6,
  "average_tps": 19.9,
  "cluster_memory_used_mb": 14336,
  "cluster_memory_total_mb": 49152,
  "cluster_cpu_usage": 32.5,
  "servers": [
    {
      "id": "survival-alpha",
      "name": "Survival Alpha",
      "type": "PAPER",
      "status": "online",
      "tps": 19.8,
      "mspt": 24.2,
      "players_count": 84,
      "max_players": 250,
      "memory_mb": 4096,
      "max_memory_mb": 8192,
      "cpu_percent": 28.4,
      "version": "Paper 1.20.4-R0.1",
      "node": "Node-US-East-1",
      "host": "10.0.1.20",
      "port": 25565,
      "uptime": "14d 6h 12m"
    }
  ],
  "nodes": [
    {
      "id": "node-us-east-1",
      "name": "Node US-East-1",
      "region": "US-East (N. Virginia)",
      "ip": "198.51.100.22",
      "status": "HEALTHY",
      "cpu_usage": 38.5,
      "memory_usage_mb": 24576,
      "memory_total_mb": 65536,
      "disk_usage_gb": 180,
      "disk_total_gb": 1000,
      "active_containers": 5,
      "docker_version": "24.0.7",
      "uptime": "45d 18h"
    }
  ]
}
```

---

### 3.2 Server Lifecycle Operations

- **Start Server:** `POST /api/v1/hosting/servers/{id}/start`
- **Stop Server:** `POST /api/v1/hosting/servers/{id}/stop`
- **Restart Server:** `POST /api/v1/hosting/servers/{id}/restart`
- **Console Command:** `POST /api/v1/hosting/servers/{id}/command`
  - **Body:** `{"command": "tps"}`
  - **Response:** `{"status": "ok", "output": "TPS from last 1m, 5m, 15m: 19.98, 19.95, 19.92"}`

---

### 3.3 Real-Time WebSocket Console Stream

- **Route:** `WS /api/v1/hosting/servers/{id}/console`
- **Protocol:** WebSocket
- **Payload Format (JSON or raw ANSI text):**
```json
{
  "level": "INFO",
  "message": "[15:42:01 INFO]: [UmbrellaCore] Player Steve joined the game (127.0.0.1)",
  "timestamp": "15:42:01"
}
```

---

### 3.4 Player Analytics & Inspection

- **Get Online Players:** `GET /api/v1/players/online`
- **Inspect Player Dossier:** `GET /api/v1/players/{username}/inspect`
  - **Response Schema:**
```json
{
  "username": "VortexPvP",
  "uuid": "8c42c13d-5df7-4b72-a55a-69452b45e7aa",
  "ip_address": "192.0.2.45",
  "hwid": "HWID-8FA-41B0-9C21",
  "server": "Survival Alpha",
  "ping": 28,
  "client_brand": "LunarClient 1.20.4",
  "playtime_hours": 142.5,
  "first_joined": "2024-01-15 14:22:00",
  "suspicion_score": 78,
  "violations_count": 14,
  "is_banned": false,
  "is_muted": false,
  "known_alts": ["VortexAlt", "ShadowSniper99"],
  "inventory_peek": [
    {"slot": 0, "id": "minecraft:netherite_sword", "count": 1, "name": "Godblade", "enchants": ["Sharpness V", "Unbreaking III"]}
  ]
}
```

---

### 3.5 Punishments Ledger & Enforcement

- **Get Punishments:** `GET /api/v1/moderation/punishments?status=ACTIVE&limit=50`
- **Issue Punishment:** `POST /api/v1/moderation/punish`
  - **Body:**
```json
{
  "player_name": "BadActor99",
  "player_uuid": "optional-uuid",
  "type": "TEMP_BAN",
  "reason": "GrimAC Autoclicker Kurtosis spike (VL48)",
  "staff_name": "Console Admin",
  "server_scope": "GLOBAL",
  "expires_at": "2026-03-01",
  "evidence_url": "https://youtu.be/example"
}
```
- **Pardon Punishment:** `POST /api/v1/moderation/punishments/{id}/pardon`

---

### 3.6 Anticheat & GrimAC Real-Time Flags

- **Get Violations:** `GET /api/v1/moderation/grimac/violations`
- **Response Schema:**
```json
[
  {
    "id": "grim-vl-1049",
    "player_name": "VortexPvP",
    "server": "KitPvP-1",
    "check_name": "AimDeltaPrediction (Reach 3.42b)",
    "violation_level": 48,
    "details": "Sub-tick bounding box reach exceeded raytrace limit by 0.42 blocks.",
    "player_ping": 32,
    "tps_at_time": 19.9,
    "auto_mitigation_taken": "Packet Cancelled (Damage Zeroed)"
  }
]
```

---

### 3.7 Alt-Account Ring Detection & Graph

- **Get Alt Clusters:** `GET /api/v1/moderation/alts/clusters`
- **Bulk Ban Alt Cluster:** `POST /api/v1/moderation/alts/clusters/{id}/ban-all`

---

### 3.8 Appeals Desk & AI Triage

- **Get Appeals:** `GET /api/v1/moderation/appeals`
- **Resolve Appeal:** `POST /api/v1/moderation/appeals/{id}/resolve`
  - **Body:** `{"verdict": "ACCEPTED", "reason": "First offense, false-positive VL confirmed"}`

---

### 3.9 Connected Plugins Health & Heartbeats

- **Route:** `GET /api/v1/dashboard/plugins`
- **Response Schema:**
```json
[
  {
    "id": "hb-survival-alpha-umbrella",
    "name": "UmbrellaOS",
    "version": "v2.4.1",
    "server_id": "survival-alpha",
    "server_name": "Survival Alpha",
    "status": "healthy",
    "heartbeat_ms": 14,
    "last_seen": "1s ago",
    "active_features": ["PacketSniffer", "WorldDeltaWatcher", "HWIDTagger", "ChatAudit"]
  },
  {
    "id": "hb-survival-alpha-grim",
    "name": "GrimAC",
    "version": "2.3.69-PROD",
    "server_id": "survival-alpha",
    "server_name": "Survival Alpha",
    "status": "healthy",
    "heartbeat_ms": 12,
    "last_seen": "1s ago",
    "active_features": ["QuantumSimulation", "SubTickReach", "MovementDelta", "KurtosisClick"]
  }
]
```

---

### 3.10 Time-Travel Snapshots & Disaster Recovery

- **List Snapshots:** `GET /api/v1/hosting/snapshots`
- **Create Snapshot Checkpoint:** `POST /api/v1/hosting/snapshots`
  - **Body:** `{"server_id": "survival-alpha", "type": "MANUAL", "tags": ["pre-boss-fight"]}`
- **Execute Rollback:** `POST /api/v1/hosting/snapshots/{id}/rollback`

---

### 3.11 Staff RBAC & Centralized Logs

- **Get Staff List:** `GET /api/v1/staff`
- **Invite Staff:** `POST /api/v1/staff/invite`
- **Query Logs:** `GET /api/v1/logs?level=ERROR&limit=100`

---

## 4. Suggested Database Schema (PostgreSQL DDL)

```sql
-- Servers Table
CREATE TABLE IF NOT EXISTS servers (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'PAPER',
    status VARCHAR(32) NOT NULL DEFAULT 'offline',
    host VARCHAR(64) NOT NULL,
    port INTEGER NOT NULL,
    max_players INTEGER NOT NULL DEFAULT 100,
    memory_mb INTEGER NOT NULL DEFAULT 4096,
    node VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Punishments Table
CREATE TABLE IF NOT EXISTS punishments (
    id VARCHAR(64) PRIMARY KEY,
    player_name VARCHAR(64) NOT NULL,
    player_uuid VARCHAR(64),
    type VARCHAR(32) NOT NULL, -- PERM_BAN, TEMP_BAN, HWID_BAN, MUTE, WARN
    reason TEXT NOT NULL,
    staff_name VARCHAR(64) NOT NULL,
    server_scope VARCHAR(64) NOT NULL DEFAULT 'GLOBAL',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PARDONED, EXPIRED
    evidence_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- GrimAC Violations
CREATE TABLE IF NOT EXISTS grim_violations (
    id VARCHAR(64) PRIMARY KEY,
    player_name VARCHAR(64) NOT NULL,
    server VARCHAR(64) NOT NULL,
    check_name VARCHAR(128) NOT NULL,
    violation_level INTEGER NOT NULL DEFAULT 1,
    details TEXT,
    player_ping INTEGER,
    tps_at_time NUMERIC(4,2),
    auto_mitigation_taken TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Plugin Heartbeats
CREATE TABLE IF NOT EXISTS plugin_heartbeats (
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    server_id VARCHAR(64) REFERENCES servers(id) ON DELETE CASCADE,
    heartbeat_ms INTEGER NOT NULL DEFAULT 0,
    active_features JSONB NOT NULL DEFAULT '[]',
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## 5. Summary Checklist for Backend Implementation

- [ ] Ensure all responses follow camelCase or snake_case matching `dataAdapters.ts` normalization.
- [ ] Mount `/api/v1/dashboard/plugins` returning heartbeat status for active instances.
- [ ] Mount WebSocket endpoint at `/api/v1/hosting/servers/{id}/console` for bi-directional live log streaming.
- [ ] Enable CORS with credentials for local dev (`localhost:3000`) and production deployment.
- [ ] Validate `X-Admin-Key` middleware for write/lifecycle operations.
