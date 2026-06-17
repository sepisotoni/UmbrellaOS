"""
cogs/ai_alerts.py — Discord bot AI moderation alert cog.

Sends alerts to staff when AI moderation tasks are created.
Polls the API every 60 seconds for pending tasks.
"""
import asyncio
import discord
from discord.ext import commands, tasks
from config import config
import httpx


class AIAlerts(commands.Cog):
    """AI moderation alert cog for Discord-based staff notifications."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.alerted_task_ids = set()
        self.api_base_url = config.API_BASE_URL
    
    @tasks.loop(seconds=60)
    async def check_pending_tasks(self):
        """Poll API for pending AI tasks every 60 seconds."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_base_url}/api/v1/ai/tasks?status=pending",
                    headers={"X-Admin-Key": config.ADMIN_KEY},
                )
                if response.status_code != 200:
                    print(f"[AIAlerts] API error: {response.status_code}")
                    return
                
                tasks = response.json()
                
                # Get the staff alerts channel
                channel = self.bot.get_channel(config.STAFF_ALERTS_CHANNEL_ID)
                if not channel:
                    print(f"[AIAlerts] Staff alerts channel not found: {config.STAFF_ALERTS_CHANNEL_ID}")
                    return
                
                # Send alerts for new tasks
                for task in tasks:
                    if task["id"] not in self.alerted_task_ids:
                        await self.send_task_alert(channel, task)
                        self.alerted_task_ids.add(task["id"])
        
        except Exception as e:
            print(f"[AIAlerts] Error checking pending tasks: {e}")
    
    async def send_task_alert(self, channel: discord.TextChannel, task: dict):
        """Send an embed alert for a single AI task."""
        # Truncate summary to 200 chars
        summary = task["ai_summary"][:200] + "..." if len(task["ai_summary"]) > 200 else task["ai_summary"]
        
        # Confidence as percentage
        confidence_pct = int(task["ai_confidence"] * 100)
        
        # Create embed
        embed = discord.Embed(
            title="🤖 AI Moderation Task",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Type", value=task["task_type"], inline=True)
        embed.add_field(name="Player", value=task["player_uuid"] or "N/A", inline=True)
        embed.add_field(name="Summary", value=summary, inline=False)
        embed.add_field(name="Recommendation", value=task["ai_recommendation"], inline=True)
        embed.add_field(name="Confidence", value=f"{confidence_pct}%", inline=True)
        embed.add_field(
            name="Action",
            value="Review in Dashboard → AI Tasks",
            inline=False,
        )
        embed.set_footer(text=f"Task ID: {task['id']}")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[AIAlerts] Error sending alert: {e}")
    
    @check_pending_tasks.before_loop
    async def before_check_pending_tasks(self):
        """Wait for bot to be ready before starting the loop."""
        await self.bot.wait_until_ready()
    
    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.check_pending_tasks.cancel()


def setup(bot: discord.Bot):
    bot.add_cog(AIAlerts(bot))
