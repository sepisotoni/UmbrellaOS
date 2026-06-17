"""
config.py — Discord bot configuration.

Loads configuration from environment variables using python-dotenv.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Discord bot configuration."""
    
    # Required
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    UMBRELLA_API_URL: str = os.getenv("UMBRELLA_API_URL", "")
    UMBRELLA_ADMIN_KEY: str = os.getenv("UMBRELLA_ADMIN_KEY", "")
    BRIDGE_CHANNEL_ID: int = int(os.getenv("BRIDGE_CHANNEL_ID", "0"))
    STAFF_ALERTS_CHANNEL_ID: int = int(os.getenv("STAFF_ALERTS_CHANNEL_ID", "0"))
    
    # Optional
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    
    def validate(self) -> None:
        """Validate required configuration."""
        if not self.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        if not self.UMBRELLA_API_URL:
            raise ValueError("UMBRELLA_API_URL is required")
        if not self.UMBRELLA_ADMIN_KEY:
            raise ValueError("UMBRELLA_ADMIN_KEY is required")
        if not self.BRIDGE_CHANNEL_ID or self.BRIDGE_CHANNEL_ID == 0:
            raise ValueError("BRIDGE_CHANNEL_ID is required")


config = Config()
