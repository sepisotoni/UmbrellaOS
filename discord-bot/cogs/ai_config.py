"""
cogs/ai_config.py — Request AI config changes from Discord (owner/admin).
"""
import httpx
import discord
from discord.ext import commands
from config import config


class AIConfigCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(name="ai-config", description="Request an AI configuration change")
    async def ai_config(
        self,
        ctx: discord.ApplicationContext,
        action_type: discord.Option(
            str,
            choices=["plugin_config", "discord_config", "dashboard_layout"],
            description="Config domain",
        ),
        request: str,
    ):
        if not self._is_staff(ctx.author, ctx.guild):
            await ctx.respond("Staff only.", ephemeral=True)
            return
        await ctx.defer()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{config.UMBRELLA_API_URL}/api/v1/ai/config/request",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    json={"action_type": action_type, "natural_language": request},
                )
                if response.status_code != 200:
                    await ctx.followup.send(f"Failed: {response.text[:300]}")
                    return
                data = response.json()
                embed = discord.Embed(title="AI Config Pending Approval", color=discord.Color.blue())
                embed.add_field(name="Type", value=data["action_type"], inline=True)
                embed.add_field(name="ID", value=str(data["id"]), inline=True)
                embed.add_field(name="Proposal", value=(data.get("ai_interpretation") or "")[:500], inline=False)
                embed.set_footer(text="Approve in Dashboard → AI Config")
                await ctx.followup.send(embed=embed)
        except Exception as e:
            await ctx.followup.send(f"Error: {e}")

    def _is_staff(self, member: discord.Member, guild: discord.Guild | None) -> bool:
        if not guild or not member:
            return False
        for name in ("Owner", "Admin", "owner", "admin"):
            role = discord.utils.get(guild.roles, name=name)
            if role and role in member.roles:
                return True
        return member.guild_permissions.administrator


def setup(bot: discord.Bot):
    bot.add_cog(AIConfigCog(bot))
