# UmbrellaOS Paper Plugin

Paper Minecraft plugin for UmbrellaOS integration.

## Requirements

- Paper 1.20.4+
- Java 17
- ProtocolLib 5.1.0+

## Building

```bash
mvn clean package
```

The built JAR will be located at `target/umbrella-plugin-1.0.0.jar`.

## Installation

1. Copy `target/umbrella-plugin-1.0.0.jar` to your server's `plugins/` directory.
2. Start the server to generate the default config.
3. Edit `plugins/UmbrellaOS/config.yml` to configure the plugin.

## Configuration

Edit `plugins/UmbrellaOS/config.yml`:

```yaml
umbrella:
  core_url: "http://localhost:8765"  # URL of your Umbrella Core backend
  admin_key: "changeme"               # Admin key from your Core .env
  verify_on_join: true                # Require verification on join
  bridge_mode_cache_seconds: 30        # How often to refresh bridge mode
  snapshot_interval_seconds: 300      # How often to take player snapshots
  replay_buffer_seconds: 300          # How many seconds of replay to buffer
  heartbeat_interval_seconds: 30      # How often to send heartbeat
```

Make sure to set `core_url` and `admin_key` to match your Core backend configuration.

## Features

- **Discord Verification**: Players must verify their Discord account before joining (optional)
- **Punishment Sync**: Automatically syncs bans and mutes from Core
- **Alt Detection**: Checks for potential alt accounts on join
- **Chat Bridge**: Forward Minecraft chat to Discord (configurable modes)
- **Player Snapshots**: Periodically captures player state (health, inventory, location)
- **Replay System**: Records player movement and combat events for replay
- **Heartbeat**: Reports server status (online count, TPS) to Core
- **Event Logging**: Logs player joins, quits, deaths, and achievements

## Commands

- `/verify` - Show your verification code (if in verification limbo)
- `/disc <message>` - Send a message to Discord (when bridge mode is partial or full)

## Bridge Modes

- `off` - Chat bridge disabled, all chat stays in-game
- `partial` - Chat stays in-game, players use `/disc` to send to Discord
- `full` - All chat is sent to Discord, not shown in-game

## Development

This plugin uses:
- Paper API 1.20.4
- ProtocolLib for packet tracking
- OkHttp for HTTP requests
- Gson for JSON serialization

All network operations are asynchronous to prevent blocking the main server thread.
