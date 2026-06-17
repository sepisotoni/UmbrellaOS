"""
main.py — Discord bot entry point.

Starts the Discord bot with chat bridge and events cogs.
"""
import asyncio
import httpx
import discord
from discord import Intents
from config import config

# Validate configuration
config.validate()

# Create Discord bot with required intents
intents = Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    print(f"[Discord Bot] Logged in as {bot.user}")
    print(f"[Discord Bot] Bridge channel ID: {config.BRIDGE_CHANNEL_ID}")
    
    # Ping Umbrella Core to verify connectivity
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.UMBRELLA_API_URL}/api/v1/plugin/health",
                headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                timeout=5.0
            )
            if response.status_code == 200:
                print("[Discord Bot] Successfully connected to Umbrella Core")
            else:
                print(f"[Discord Bot] Warning: Umbrella Core returned status {response.status_code}")
    except Exception as e:
        print(f"[Discord Bot] Warning: Could not connect to Umbrella Core: {e}")


# Load cogs
bot.load_extension("cogs.chat_bridge")
bot.load_extension("cogs.events")
bot.load_extension("cogs.verification")
bot.load_extension("cogs.alt_alerts")
bot.load_extension("cogs.ai_alerts")

if __name__ == "__main__":
    print("[Discord Bot] Starting...")
    bot.run(config.DISCORD_BOT_TOKEN)
