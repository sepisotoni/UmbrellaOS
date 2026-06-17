"""
cogs/verification.py — Discord bot verification cog.

Handles DM-based player verification for cracked Minecraft servers.
"""
import httpx
import discord
from discord.ext import commands
from config import config


class Verification(commands.Cog):
    """Verification cog for Discord-based player verification."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle DM messages for verification codes."""
        # Only process DMs (not guild messages)
        if message.guild is not None:
            return
        
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Check if content is exactly 6 digits
        content = message.content.strip()
        if not content.isdigit() or len(content) != 6:
            return
        
        # POST to verification confirm endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.UMBRELLA_API_URL}/api/v1/verification/confirm",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    json={
                        "discord_id": str(message.author.id),
                        "discord_username": message.author.name,
                        "code": content,
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    await message.reply("✅ Verified! You can now play on the server.")
                elif response.status_code == 404:
                    await message.reply("❌ Invalid code. Please check and try again.")
                elif response.status_code == 400:
                    detail = response.json().get("detail", "")
                    if "expired" in detail.lower():
                        await message.reply("❌ Code expired. Rejoin the server for a new code.")
                    elif "used" in detail.lower():
                        await message.reply("✅ Already verified!")
                    else:
                        await message.reply("❌ Invalid code. Please check and try again.")
                else:
                    await message.reply("⚠️ Something went wrong. Please try again.")
                    
        except Exception as e:
            print(f"[Verification] Error confirming code: {e}")
            await message.reply("⚠️ Something went wrong. Please try again.")
    
    @commands.slash_command(name="verify", description="Check verification status")
    @commands.has_permissions(administrator=True)
    async def verify(
        self,
        ctx: discord.ApplicationContext,
        minecraft_username: str = commands.Option(
            str,
            description="Minecraft username to check",
            required=False,
        ),
    ):
        """Check verification status for a player."""
        if not minecraft_username:
            await ctx.respond("Please provide a Minecraft username.", ephemeral=True)
            return
        
        try:
            async with httpx.AsyncClient() as client:
                # First, get player UUID from username (this would need a player lookup endpoint)
                # For now, we'll just show a message that this feature requires player lookup
                await ctx.respond(
                    f"Verification status check for `{minecraft_username}` requires player UUID lookup. "
                    "This feature is pending implementation.",
                    ephemeral=True
                )
        except Exception as e:
            print(f"[Verification] Error checking status: {e}")
            await ctx.respond("⚠️ Something went wrong. Please try again.", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Verification(bot))
