"""
bot.py — HeavenCloud entry point shim.
HeavenCloud's Python hosting runs bot.py by default.
This file simply delegates to main.py's entry point.
"""
from main import main

if __name__ == "__main__":
    main()
