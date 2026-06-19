"""
cogs/announcements.py — Announcements channel setup and posting.
"""
import httpx
import discord
from discord.ext import commands
from config import config


class Announcements(commands.Cog):
    CHANNEL_NAME = "umbrella-announcements"

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self._ensure_channels()

    async def _ensure_channels(self):
        if not self.bot.guilds:
            return
        guild = self.bot.guilds[0]
        ch_id = await self._get_setting("discord.announcements_channel")
        if ch_id:
            if self.bot.get_channel(int(ch_id)):
                return
        channel = discord.utils.get(guild.text_channels, name=self.CHANNEL_NAME)
        if channel is None:
            try:
                channel = await guild.create_text_channel(
                    self.CHANNEL_NAME,
                    topic="UmbrellaOS server announcements",
                    reason="UmbrellaOS auto channel setup",
                )
                print(f"[Announcements] Created #{channel.name}")
            except discord.Forbidden:
                print("[Announcements] Missing permission to create channel")
                return
        await self._save_setting("discord.announcements_channel", str(channel.id))
        if config.BRIDGE_CHANNEL_ID and channel.id != config.BRIDGE_CHANNEL_ID:
            await channel.send("📢 **Announcements channel ready.** Post updates here or use `/announce`.")

    async def _get_setting(self, key: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/settings",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                )
                if r.status_code != 200:
                    return None
                for s in r.json():
                    if s.get("key") == key:
                        return s.get("value") or None
        except Exception:
            pass
        return None

    async def _save_setting(self, key: str, value: str):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(
                    f"{config.UMBRELLA_API_URL}/api/v1/settings/{key}",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    json={"value": value},
                )
        except Exception as e:
            print(f"[Announcements] Could not save setting: {e}")

    @commands.slash_command(name="announce", description="Post to the announcements channel")
    async def announce(self, ctx: discord.ApplicationContext, message: str):
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.respond("You need Manage Messages.", ephemeral=True)
            return
        ch_id = await self._get_setting("discord.announcements_channel")
        channel = self.bot.get_channel(int(ch_id)) if ch_id else None
        if channel is None:
            await self._ensure_channels()
            ch_id = await self._get_setting("discord.announcements_channel")
            channel = self.bot.get_channel(int(ch_id)) if ch_id else None
        if channel is None:
            await ctx.respond("Announcements channel not found.", ephemeral=True)
            return
        await channel.send(f"📢 **Announcement**\n{message}")
        await ctx.respond("Posted.", ephemeral=True)

    @commands.slash_command(name="setup-channels", description="Create missing UmbrellaOS Discord channels")
    async def setup_channels(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("Administrator only.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        await self._ensure_channels()
        staff_id = await self._get_setting("discord.staff_alerts_channel")
        guild = ctx.guild
        if not staff_id:
            ch = discord.utils.get(guild.text_channels, name="umbrella-staff-alerts")
            if ch is None:
                ch = await guild.create_text_channel("umbrella-staff-alerts", reason="UmbrellaOS setup")
            await self._save_setting("discord.staff_alerts_channel", str(ch.id))
        await ctx.followup.send("Channels configured. Check #umbrella-announcements.", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(Announcements(bot))
