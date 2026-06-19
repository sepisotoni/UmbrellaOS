"""Discord bot entry point."""
import httpx
import discord
from discord import Intents
from config import config

config.validate()

intents = Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = discord.Bot(intents=intents)


@bot.event
async def on_ready():
    print(f"[Discord Bot] Logged in as {bot.user}")
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{config.UMBRELLA_API_URL}/health", timeout=5.0)
            print("[Discord Bot] Core OK" if r.status_code == 200 else f"[Discord Bot] Core {r.status_code}")
    except Exception as e:
        print(f"[Discord Bot] Core unreachable: {e}")

    if config.BRIDGE_CHANNEL_ID:
        ch = bot.get_channel(config.BRIDGE_CHANNEL_ID)
        if ch:
            await ch.send("🟢 **UmbrellaOS Discord Bot** is online")


for ext in ("cogs.chat_bridge", "cogs.events", "cogs.ai_alerts", "cogs.ai_config",
            "cogs.mc_commands", "cogs.announcements"):
    try:
        bot.load_extension(ext)
        print(f"[Discord Bot] Loaded {ext}")
    except Exception as e:
        print(f"[Discord Bot] Failed {ext}: {e}")

if __name__ == "__main__":
    bot.run(config.DISCORD_BOT_TOKEN)
