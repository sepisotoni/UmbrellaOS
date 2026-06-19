"""
cogs/mc_commands.py — Discord bot cog for Minecraft command execution.

Handles !mc and !mc-ai commands from Discord staff.
"""
import httpx
import discord
from discord.ext import commands
from config import config


class MCCommands(commands.Cog):
    """Minecraft command execution from Discord."""
    
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.pending_ai_commands = {}  # Store pending AI commands for reaction handling
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle incoming Discord messages for MC commands."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Check if user has Admin or Owner role
        if not self._has_staff_role(message.author, message.guild):
            return
        
        content = message.content.strip()
        
        # Handle !mc command (direct command execution)
        if content.lower().startswith("!mc "):
            command = content[4:].strip()
            if not command:
                await message.reply("⚠️ Command cannot be empty")
                return
            
            # Queue the command via API
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{config.UMBRELLA_API_URL}/api/v1/mc/command",
                        headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                        json={
                            "command": command,
                            "requested_by_discord_id": str(message.author.id),
                            "requested_by_username": message.author.display_name,
                        },
                        timeout=5.0
                    )
                    
                    if response.status_code == 201:
                        await message.reply(f"⚡ Command queued: `{command}`")
                    else:
                        await message.reply(f"❌ Failed to queue command: {response.status_code}")
                        
            except Exception as e:
                await message.reply(f"❌ Error: {e}")
        
        # Handle !mc-ai command (AI-powered command generation)
        elif content.lower().startswith("!mc-ai "):
            natural_language = content[7:].strip()
            if not natural_language:
                await message.reply("⚠️ Please describe what you want to do")
                return
            
            # Get OpenRouter API key
            api_key = await self._get_openrouter_api_key()
            if not api_key:
                await message.reply("❌ AI commands require OpenRouter API key in Dashboard → Settings → AI")
                return
            
            # Translate natural language to MC command
            suggested_command = await self._translate_to_mc_command(natural_language, api_key)
            
            if not suggested_command:
                await message.reply("❌ Failed to generate command. Please try again.")
                return
            
            # Show suggestion and add reactions
            embed = discord.Embed(
                title="🤖 AI Command Suggestion",
                description=f"**Your request:** {natural_language}\n\n**Suggested command:** `{suggested_command}`",
                color=discord.Color.blue()
            )
            
            msg = await message.reply(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")
            
            # Store for reaction handling
            self.pending_ai_commands[msg.id] = {
                "user_id": message.author.id,
                "command": suggested_command,
                "original_message": message
            }
            
            # Wait for reaction (60 second timeout)
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    timeout=60.0,
                    check=lambda r, u: u.id == message.author.id and r.message.id == msg.id and str(r.emoji) in ["✅", "❌"]
                )
                
                if str(reaction.emoji) == "✅":
                    # Execute the command
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.post(
                                f"{config.UMBRELLA_API_URL}/api/v1/mc/command",
                                headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                                json={
                                    "command": suggested_command,
                                    "requested_by_discord_id": str(message.author.id),
                                    "requested_by_username": message.author.display_name,
                                },
                                timeout=5.0
                            )
                            
                            if response.status_code == 201:
                                await msg.reply("✅ Executing command...")
                            else:
                                await msg.reply(f"❌ Failed to execute: {response.status_code}")
                    except Exception as e:
                        await msg.reply(f"❌ Error: {e}")
                else:
                    await msg.reply("❌ Cancelled")
                    
            except TimeoutError:
                await msg.reply("⏱ Timed out")
            finally:
                # Clean up
                if msg.id in self.pending_ai_commands:
                    del self.pending_ai_commands[msg.id]
    
    def _has_staff_role(self, member: discord.Member, guild: discord.Guild) -> bool:
        """Check if user has Admin or Owner role."""
        if not guild or not member:
            return False
        
        # Check for Admin role
        admin_role = discord.utils.get(guild.roles, name="Admin")
        if admin_role and admin_role in member.roles:
            return True
        
        # Check for Owner role
        owner_role = discord.utils.get(guild.roles, name="Owner")
        if owner_role and owner_role in member.roles:
            return True
        
        return False
    
    async def _get_openrouter_api_key(self) -> str | None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config.UMBRELLA_API_URL}/api/v1/settings",
                    headers={"X-Admin-Key": config.UMBRELLA_ADMIN_KEY},
                    timeout=5.0,
                )
                if response.status_code != 200:
                    return None
                for s in response.json():
                    if s.get("key") == "ai.openrouter_key" and s.get("value") not in (None, "", "***"):
                        return s["value"]
        except Exception as e:
            print(f"[MC Commands] Error getting API key: {e}")
        return None
    
    async def _translate_to_mc_command(self, natural_language: str, api_key: str) -> str | None:
        """Translate natural language to Minecraft command using OpenRouter API."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://umbrellaos.app",
                        "X-Title": "UmbrellaOS"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-exp:free",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Convert natural language to a Minecraft server console command. "
                                    "Return ONLY the raw command, no explanation, no backticks. "
                                    "Examples: "
                                    "make it daytime → time set day "
                                    "ban Steve for griefing → ban Steve griefing "
                                    "expand border by 500 → worldborder add 500"
                                )
                            },
                            {"role": "user", "content": natural_language}
                        ],
                        "max_tokens": 60,
                        "temperature": 0.1
                    }
                )
                
                if response.status_code != 200:
                    print(f"[MC Commands] OpenRouter API error: {response.status_code}")
                    return None
                
                result = response.json()
                command = result["choices"][0]["message"]["content"].strip()
                return command.strip('`').strip()
                
        except Exception as e:
            print(f"[MC Commands] Error translating command: {e}")
            return None


def setup(bot: discord.Bot):
    """Load the MCCommands cog."""
    bot.add_cog(MCCommands(bot))
