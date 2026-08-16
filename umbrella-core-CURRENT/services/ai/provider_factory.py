"""
services/ai/provider_factory.py — Builds AIProvider instances from the
DB-backed Setting model (category="ai"), not from pydantic env config —
see config/settings.py's Phase 5 comment for why: this is what makes
providers togglable/configurable from the dashboard at runtime, without a
process restart.

Deliberately does not cache constructed providers: an operator can flip
`ai.openrouter_enabled` off or rotate a key from the dashboard at any time,
and the next call should see that immediately, not a stale cached instance.
Constructing an httpx-backed provider object is cheap (no connection is
opened until a request is actually made), so this costs nothing meaningful.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.anthropic_provider import AnthropicProvider
from services.ai.base import AIProvider, ProviderError
from services.ai.gemini_provider import GeminiProvider
from services.ai.openrouter_provider import OpenRouterProvider
from services.settings_service import SettingsService

# provider name -> (DB key for its API key, DB key for its enabled toggle, provider class)
_PROVIDER_REGISTRY: dict[str, tuple[str, str, type[AIProvider]]] = {
    "openrouter": ("ai.openrouter_key", "ai.openrouter_enabled", OpenRouterProvider),
    "anthropic": ("ai.anthropic_api_key", "ai.anthropic_enabled", AnthropicProvider),
    "gemini": ("ai.gemini_api_key", "ai.gemini_enabled", GeminiProvider),
}


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


class ProviderFactory:
    @staticmethod
    async def is_enabled(db: AsyncSession, provider_name: str) -> bool:
        entry = _PROVIDER_REGISTRY.get(provider_name)
        if entry is None:
            return False
        _, enabled_key, _ = entry
        value = await SettingsService.get_value(db, enabled_key)
        return _is_truthy(value)

    @staticmethod
    async def has_key_configured(db: AsyncSession, provider_name: str) -> bool:
        entry = _PROVIDER_REGISTRY.get(provider_name)
        if entry is None:
            return False
        key_setting, _, _ = entry
        value = await SettingsService.get_value(db, key_setting)
        return bool(value)

    @staticmethod
    async def available_providers(db: AsyncSession) -> list[str]:
        """Providers that are both enabled AND have a key configured —
        the actual set the model router may pick from."""
        available = []
        for name in _PROVIDER_REGISTRY:
            if await ProviderFactory.is_enabled(db, name) and await ProviderFactory.has_key_configured(db, name):
                available.append(name)
        return available

    @staticmethod
    async def build(db: AsyncSession, provider_name: str) -> AIProvider:
        """
        Construct a provider instance. Raises ProviderError if the
        provider name is unknown, disabled, or has no key configured —
        the model router treats this identically to any other
        ProviderError (skip and try the next candidate), so an operator
        disabling a provider mid-flight degrades gracefully rather than
        crashing whatever was mid-request.
        """
        entry = _PROVIDER_REGISTRY.get(provider_name)
        if entry is None:
            raise ProviderError(f"unknown AI provider {provider_name!r}")

        key_setting, enabled_key, provider_cls = entry

        if not await ProviderFactory.is_enabled(db, provider_name):
            raise ProviderError(f"provider {provider_name!r} is disabled (set {enabled_key}=true to enable)")

        api_key = await SettingsService.get_value(db, key_setting)
        if not api_key:
            raise ProviderError(f"provider {provider_name!r} has no API key configured ({key_setting})")

        return provider_cls(api_key=api_key)
