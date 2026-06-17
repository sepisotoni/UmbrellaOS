"""
cogs/events.py — Discord bot events cog.

Polls for Minecraft events and forwards them to Discord.
"""
import asyncio
import httpx
import discord
from discord.ext import commands, tasks
from config import config


class Events(commands.Cog):
    """Events cog for polling and forwarding Minecraft events."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.bridge_channel_id = config.BRIDGE_CHANNEL_ID
        self.last_seen_id = 0
        self.last_event_id = 0
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start background polling tasks when bot is ready."""
        self.poll_messages.start()
        self.poll_events.start()
        print("[Events] Background polling tasks started")
    
    def cog_unload(self):
        """Clean up background tasks when cog is unloaded."""
        self.poll_messages.cancel()
        self.poll_events.cancel()
    
    @tasks.loop(seconds=5)
    async def poll_messages(self):
        """Poll for new Minecraft chat messages every 5 seconds."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/bridge/messages?source=minecraft&limit=20",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    timeout=5.0
                )
                if response.status_code == 200:
                    messages = response.json()
                    # Process messages newer than last_seen_id
                    for msg in messages:
                        if msg["id"] > self.last_seen_id:
                            self.last_seen_id = msg["id"]
                            # Get player name from message or use UUID
                            player_name = msg.get("player_uuid", "Unknown")
                            # Send to Discord via chat bridge
                            chat_bridge = self.bot.get_cog("ChatBridge")
                            if chat_bridge:
                                await chat_bridge.send_to_discord(
                                    player_name,
                                    msg["message"],
                                    "minecraft"
                                )
        except Exception as e:
            print(f"[Events] Error polling messages: {e}")
    
    @tasks.loop(seconds=10)
    async def poll_events(self):
        """Poll for Minecraft events every 10 seconds."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/bridge/messages?source=minecraft&limit=50",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    timeout=5.0
                )
                if response.status_code == 200:
                    messages = response.json()
                    # Process messages newer than last_event_id
                    for msg in messages:
                        if msg["id"] > self.last_event_id:
                            self.last_event_id = msg["id"]
                            # Check if this is an event (could be indicated by message format or metadata)
                            # For now, we'll parse event types from message content
                            await self.handle_event_message(msg)
        except Exception as e:
            print(f"[Events] Error polling events: {e}")
    
    async def handle_event_message(self, msg: dict):
        """Handle an event message from Minecraft."""
        message = msg.get("message", "")
        player_name = msg.get("player_uuid", "Unknown")
        
        # Parse event types from message content
        event_emoji = ""
        formatted_message = ""
        
        if "joined the server" in message.lower():
            event_emoji = "🟢"
            formatted_message = f"{event_emoji} **{player_name}** joined the server"
        elif "left the server" in message.lower():
            event_emoji = "🔴"
            formatted_message = f"{event_emoji} **{player_name}** left the server"
        elif "died" in message.lower():
            event_emoji = "💀"
            formatted_message = f"{event_emoji} **{player_name}** died: {message}"
        elif "earned" in message.lower() or "achievement" in message.lower():
            event_emoji = "🏆"
            formatted_message = f"{event_emoji} **{player_name}** earned: {message}"
        elif "server is online" in message.lower():
            event_emoji = "🟢"
            formatted_message = f"{event_emoji} Server is online"
        elif "server is shutting down" in message.lower():
            event_emoji = "🔴"
            formatted_message = f"{event_emoji} Server is shutting down"
        else:
            # Not a recognized event, skip
            return
        
        # Send to Discord
        channel = self.bot.get_channel(self.bridge_channel_id)
        if channel:
            await channel.send(formatted_message)
        else:
            print(f"[Events] Could not find bridge channel")


def setup(bot: discord.Bot):
    bot.add_cog(Events(bot))
