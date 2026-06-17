# UmbrellaOS Discord Bot

Discord bot for bridging chat and events between Minecraft servers and Discord channels.

## Features

- **Chat Bridge**: Forward messages between Discord and Minecraft
- **Event Broadcasting**: Display server events (joins, leaves, deaths, achievements) in Discord
- **Configurable Modes**: Off, Partial (prefix-based), or Full bridging
- **Webhook Support**: Optional webhook for nicer message formatting

## Installation

1. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Configuration

- `DISCORD_BOT_TOKEN`: Your Discord bot token (required)
- `UMBRELLA_API_URL`: Umbrella Core API URL (e.g., `http://localhost:8765`) (required)
- `UMBRELLA_ADMIN_KEY`: Admin key for Umbrella Core API (required)
- `BRIDGE_CHANNEL_ID`: Discord channel ID for the bridge (required)
- `WEBHOOK_URL`: Optional Discord webhook URL for nicer formatting

## Bridge Modes

- **Off**: No message forwarding
- **Partial**: Only forward Discord messages starting with `/disc` (prefix stripped)
- **Full**: Forward all messages in both directions

## Cogs

### Chat Bridge (`cogs/chat_bridge.py`)
- Listens for messages in the bridge channel
- Forwards to Umbrella Core based on bridge mode
- Provides `send_to_discord()` method for Minecraft → Discord forwarding

### Events (`cogs/events.py`)
- Polls for Minecraft chat messages every 5 seconds
- Polls for server events every 10 seconds
- Formats and displays events in Discord with emojis

## Requirements

- Python 3.10+
- discord.py >= 2.3.0
- httpx >= 0.27.0
- python-dotenv >= 1.0.0
