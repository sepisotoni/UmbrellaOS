"""
cogs/chat_bridge.py — Discord-Minecraft chat bridge cog.

Handles forwarding messages between Discord and Minecraft.
"""
import httpx
import discord
from discord.ext import commands
from config import config


class ChatBridge(commands.Cog):
    """Chat bridge between Discord and Minecraft."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.bridge_channel_id = config.BRIDGE_CHANNEL_ID
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming Discord messages for bridging to Minecraft."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Only process messages in the bridge channel
        if message.channel.id != self.bridge_channel_id:
            return
        
        # Get bridge settings to determine if we should forward
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/bridge/settings",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    timeout=5.0
                )
                if response.status_code != 200:
                    print(f"[Chat Bridge] Failed to get bridge settings: {response.status_code}")
                    return
                
                settings = response.json()
                mode = settings.get("mode", "off")
                discord_to_mc = settings.get("discord_to_mc", True)
                
                if mode == "off":
                    return
                
                if not discord_to_mc:
                    return
                
                content = message.content
                # In partial mode, only forward messages starting with /disc
                if mode == "partial":
                    if not content.startswith("/disc"):
                        return
                    content = content[5:].strip()  # Remove /disc prefix
                
                # Forward message to Umbrella Core
                payload = {
                    "source": "discord",
                    "discord_id": str(message.author.id),
                    "message": content,
                    "channel_id": str(message.channel.id),
                }
                
                response = await client.post(
                    f"{config.UMBRELLA_API_URL}/api/v1/bridge/message",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    json=payload,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("forwarded"):
                        print(f"[Chat Bridge] Forwarded message from {message.author}")
                else:
                    print(f"[Chat Bridge] Failed to forward message: {response.status_code}")
                    
        except Exception as e:
            print(f"[Chat Bridge] Error processing message: {e}")
    
    async def send_to_discord(self, player_name: str, message: str, source: str = "minecraft"):
        """Send a message from Minecraft to Discord."""
        try:
            if config.WEBHOOK_URL:
                # Use webhook for nicer formatting
                async with httpx.AsyncClient() as client:
                    await client.post(
                        config.WEBHOOK_URL,
                        json={"content": message, "username": player_name},
                        timeout=5.0
                    )
            else:
                # Fallback to sending to channel directly
                channel = self.bot.get_channel(self.bridge_channel_id)
                if channel:
                    await channel.send(f"**[MC]** {player_name}: {message}")
                else:
                    print(f"[Chat Bridge] Could not find bridge channel")
        except Exception as e:
            print(f"[Chat Bridge] Error sending to Discord: {e}")


def setup(bot: discord.Bot):
    bot.add_cog(ChatBridge(bot))
