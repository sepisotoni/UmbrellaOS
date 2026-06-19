"""
cogs/ai_alerts.py — Poll pending AI tasks and alert staff on Discord.
"""
import discord
from discord.ext import commands, tasks
from config import config
import httpx


class AIAlerts(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.alerted_task_ids: set[int] = set()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_pending_tasks.is_running():
            self.check_pending_tasks.start()

    def cog_unload(self):
        self.check_pending_tasks.cancel()

    @tasks.loop(seconds=60)
    async def check_pending_tasks(self):
        channel_id = config.STAFF_ALERTS_CHANNEL_ID or config.BRIDGE_CHANNEL_ID
        if not channel_id:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/ai/tasks?status=pending&limit=20",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                )
                if response.status_code != 200:
                    return
                for task in response.json():
                    tid = task["id"]
                    if tid in self.alerted_task_ids:
                        continue
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await self._send_alert(channel, task)
                        self.alerted_task_ids.add(tid)
        except Exception as e:
            print(f"[AIAlerts] {e}")

    async def _send_alert(self, channel: discord.TextChannel, task: dict):
        summary = (task.get("ai_summary") or "")[:200]
        conf = int(float(task.get("ai_confidence", 0)) * 100)
        embed = discord.Embed(title="AI Review Required", color=discord.Color.orange())
        embed.add_field(name="Type", value=task.get("task_type", "?"), inline=True)
        embed.add_field(name="Player", value=task.get("player_uuid") or "N/A", inline=True)
        embed.add_field(name="Summary", value=summary or "—", inline=False)
        embed.add_field(name="Recommendation", value=task.get("ai_recommendation", "review"), inline=True)
        embed.add_field(name="Confidence", value=f"{conf}%", inline=True)
        embed.set_footer(text=f"Task #{task['id']} — review in Dashboard → AI Tasks")
        await channel.send(embed=embed)

    @check_pending_tasks.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


def setup(bot: discord.Bot):
    bot.add_cog(AIAlerts(bot))
