"""
run.py — HeavenCloud launcher for umbrella-discord.
Sits at repo root so the Pterodactyl egg's startup command can find it.
Changes cwd into the bot subdirectory so all relative imports work.
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(ROOT, "umbrella-discord-CURRENT")
os.chdir(BOT_DIR)
sys.path.insert(0, BOT_DIR)

exec(open(os.path.join(BOT_DIR, "main.py")).read())
