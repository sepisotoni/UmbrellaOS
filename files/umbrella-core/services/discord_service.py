"""
services/discord_service.py — Discord OAuth2 API client.
"""
import httpx

from config import get_settings

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordOAuthError(Exception):
    """Raised when Discord OAuth API calls fail."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def exchange_code(
    code: str,
    redirect_uri: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """Exchange an authorization code for Discord OAuth tokens."""
    settings = get_settings()
    cid = client_id or settings.discord_client_id
    csec = client_secret or settings.discord_client_secret
    if not cid or not csec:
        raise DiscordOAuthError("Discord OAuth is not configured", 503)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": cid,
                "client_secret": csec,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            raise DiscordOAuthError(
                "Failed to exchange authorization code with Discord",
                response.status_code,
            )
        return response.json()


async def fetch_user(access_token: str) -> dict:
    """Fetch the authenticated Discord user profile (id, username, avatar, email)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise DiscordOAuthError(
                "Failed to fetch Discord user profile",
                response.status_code,
            )
        return response.json()
