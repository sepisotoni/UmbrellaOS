# UmbrellaOS Architecture: In-JVM Minecraft Plugin vs Daemon Specification

## 1. Architectural Overview

**Critical Architectural Directive:** UmbrellaOS **does not** utilize a standalone Linux host daemon (`systemd`, background `umbrella-daemon`, etc.). Instead, all telemetry, real-time metrics, cross-server command dispatches, and moderation events are gathered and processed directly inside the Java Virtual Machine (JVM) via the **`umbrella-core-bridge.jar`** (for Paper, Purpur, Folia) and **`umbrella-velocity-bridge.jar`** (for Velocity Proxy) Minecraft plugins.

```
+-------------------------------------------------------------------------+
|                           Umbrella Dashboard (Web UI)                   |
|                               (React + Vite)                            |
+------------------------------------+------------------------------------+
                                     |
                                     | HTTP REST & WebSocket (/api/v1/*)
                                     v
+-------------------------------------------------------------------------+
|                        UmbrellaOS REST Gateway API                      |
|                           (FastAPI / Node Server)                       |
+------------------------------------+------------------------------------+
                                     |
               +---------------------+---------------------+
               | Redis PubSub / Direct IPC Sockets         |
               v                                           v
+-----------------------------+             +-----------------------------+
|    Paper / Purpur Node 1    |             |    Velocity Edge Proxy      |
|  [umbrella-core-bridge.jar] |             | [umbrella-velocity-bridge]  |
|  - Real-time TPS / MSPT     |             | - Cross-Server Routing      |
|  - Heap Memory Telemetry    |             | - Player Connection Gateway |
|  - GrimAC Anticheat IPC     |             | - Global Chat Interception  |
|  - In-JVM Command Dispatch  |             | - Global Title Broadcasts   |
+-----------------------------+             +-----------------------------+
```

---

## 2. Why In-JVM Plugin over System Daemon?

1. **Zero Operating System Overhead**: System daemons have no native insight into Minecraft's internal game loop (`MinecraftServer.currentTick`, tick MSPT, ChunkProviderServer, or loaded entities). The in-JVM plugin accesses these data structures with nanosecond precision.
2. **Container & Pterodactyl Compatibility**: Server instances running inside Docker containers or Pterodactyl / Pelican panels cannot easily spawn background host daemons. Java plugins mount seamlessly into `/plugins/` across any hosting provider.
3. **Thread Safety & Dynamic Tick Execution**: In-JVM plugins can execute tasks on the main tick thread (`Bukkit.getScheduler().runTask()`) or asynchronously (`runTaskAsynchronously()`), avoiding chunk corruption or thread deadlocks during player bans, inventories, or world backups.

---

## 3. Plugin Telemetry & Heartbeat Specification

Every server node running `umbrella-core-bridge.jar` continuously sends heartbeat frames to `GET /api/v1/dashboard/plugins` and `POST /api/v1/telemetry/heartbeat`.

### Heartbeat JSON Payload Format:
```json
{
  "nodeId": "srv-survival-01",
  "nodeName": "Survival-Alpha",
  "software": "Purpur 1.21.1",
  "pluginVersion": "3.2.4-RC",
  "heartbeatMs": 14,
  "timestamp": "2026-08-22T10:24:00Z",
  "metrics": {
    "tps": 19.95,
    "mspt": 18.2,
    "playersOnline": 42,
    "maxPlayers": 100,
    "heapUsedMb": 3410,
    "heapAllocatedMb": 8192,
    "chunksLoaded": 1280,
    "entitiesCount": 2410
  },
  "activeFeatures": [
    "GRIM_AC_IPC_STREAM",
    "DISCORD_SRV_RELAY",
    "TRANSLATION_FILTER",
    "CRON_SCHEDULER_EXECUTOR"
  ]
}
```

---

## 4. Plugin Deployment & Hot-Reload Protocol

When the user uploads a `.jar` package through the **Plugins View** in UmbrellaOS:
1. The web client transmits the multipart `.jar` binary to `POST /api/v1/plugins/upload`.
2. The REST API distributes the JAR to the target node's `/plugins/` directory.
3. If **Hot-Reload / Load Immediately** is enabled, the bridge plugin executes `PluginManager.loadPlugin()` and `PluginManager.enablePlugin()` dynamically without requiring a full server reboot.
4. Live configuration changes (`config.yml`) are sent via `PUT /api/v1/plugins/{id}/config` and applied using `plugin.reloadConfig()`.
