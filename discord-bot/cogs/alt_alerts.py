"""
cogs/alt_alerts.py — Discord bot alt detection alert cog.

Sends alerts to staff when players are flagged as potential alts.
"""
import discord
from discord.ext import commands
from config import config


class AltAlerts(commands.Cog):
    """Alt detection alert cog for Discord-based staff notifications."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
    
    async def check_new_player(
        self,
        player_uuid: str,
        score: int,
        triggers: list,
        username: str,
    ):
        """
        Send alert when a new player is flagged as potential alt.
        Called after POST /alts/check returns score >= 80.
        """
        if score < 80:
            return
        
        # Get the staff alerts channel
        channel = self.bot.get_channel(config.STAFF_ALERTS_CHANNEL_ID)
        if not channel:
            print(f"[AltAlerts] Staff alerts channel not found: {config.STAFF_ALERTS_CHANNEL_ID}")
            return
        
        # Determine color based on score
        if score >= 95:
            color = discord.Color.red()
            risk_level = "CRITICAL"
        elif score >= 80:
            color = discord.Color.yellow()
            risk_level = "HIGH"
        else:
            color = discord.Color.orange()
            risk_level = "MEDIUM"
        
        # Create embed
        embed = discord.Embed(
            title="🚨 Potential Alt Detected",
            color=color,
        )
        embed.add_field(name="Player", value=username, inline=True)
        embed.add_field(name="Score", value=f"{score}/100", inline=True)
        embed.add_field(name="Risk Level", value=risk_level, inline=True)
        embed.add_field(
            name="Triggers",
            value=", ".join(triggers) if triggers else "None",
            inline=False,
        )
        embed.add_field(
            name="Action",
            value=f"Review in dashboard → Players → {username}",
            inline=False,
        )
        embed.set_footer(text=f"UUID: {player_uuid}")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[AltAlerts] Error sending alert: {e}")


def setup(bot: discord.Bot):
    bot.add_cog(AltAlerts(bot))
