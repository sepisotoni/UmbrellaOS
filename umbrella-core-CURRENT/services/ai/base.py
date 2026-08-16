"""
services/ai/base.py — The AIProvider interface every model backend
implements. Adding a new provider means implementing this interface and
registering it in provider_factory.py — nothing else in the AI layer
(model router, orchestrator, capabilities) needs to change, the same
"one new implementation, everything else stays put" pattern used for
umbrella-daemon's Environment interface.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


class ProviderError(Exception):
    """Raised for any failure calling a provider — a bad API key, a rate
    limit, a network error, a malformed response. The model router treats
    every ProviderError identically (as a failure to record and fail over
    from); providers don't need finer-grained exception types than this
    unless a caller genuinely needs to branch on the failure reason."""


_ERROR_DETAIL_MAX_CHARS = 500


def truncate_for_error(detail: str, limit: int = _ERROR_DETAIL_MAX_CHARS) -> str:
    """
    Caps how much of a raw upstream response/exception string gets folded
    into a ProviderError message. Two reasons this exists rather than
    embedding the raw text directly, as the individual providers used to:

    1. Some providers' error bodies can be large (validation errors that
       echo back the full request, HTML error pages from a misconfigured
       proxy, etc.) - unbounded length here means an unbounded
       ProviderError message, which then flows into AIDecisionLog and any
       future logging of caught provider failures.
    2. Defense in depth: nothing in this codebase currently logs these
       messages, and no provider is known to echo back request
       authentication in its error body - but capping length here means
       that if observability logging is added later, or if a provider's
       error format ever changes to include more request context than
       expected, the blast radius of an accidental credential echo is a
       truncated fragment rather than a full response body.
    """
    if len(detail) <= limit:
        return detail
    return detail[:limit] + f"... [truncated, {len(detail)} chars total]"


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model_name: str
    latency_ms: int
    # Token usage, when the provider reports it — used for cost/usage
    # visibility later (Phase 8's observability), not required for Phase 5
    # to function, so left optional rather than every provider needing to
    # fake a value it doesn't actually have.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class AIProvider(ABC):
    """One backend capable of turning a system+user prompt into text."""

    name: str  # "openrouter" | "anthropic" | "gemini" — matches AIModelConfig.provider

    @abstractmethod
    async def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GenerationResult:
        """Raises ProviderError on any failure — network, auth, rate
        limit, or a response shape the provider didn't expect."""
        raise NotImplementedError


class HTTPProvider(AIProvider):
    """
    Shared request lifecycle for the three JSON-over-HTTPS providers
    (Anthropic, OpenRouter, Gemini): construct a request, send it, wrap
    network/status/shape failures as ProviderError, time it, return a
    GenerationResult. This was duplicated near-identically across all
    three provider files; what's actually provider-specific - the
    endpoint, auth mechanism, request body shape, and response parsing -
    is now the only thing each subclass implements.

    A subclass sets `display_name` (for error message prefixes) and
    `DEFAULT_BASE_URL`, and implements the four hook methods below.
    """

    display_name: str
    DEFAULT_BASE_URL: str

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        if not api_key:
            raise ProviderError(f"{self.display_name} API key is empty")
        self._api_key = api_key
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._transport = transport

    def _endpoint_url(self, model: str) -> str:
        raise NotImplementedError

    def _request_headers(self) -> dict:
        raise NotImplementedError

    def _request_body(
        self, model: str, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float
    ) -> dict:
        raise NotImplementedError

    def _parse_generation(self, data: dict) -> tuple[str, int | None, int | None]:
        """Returns (text, prompt_tokens, completion_tokens) from a
        successful response body. Let KeyError/IndexError/ValueError
        propagate on an unexpected shape - generate() below wraps
        whichever of those it raises into a ProviderError."""
        raise NotImplementedError

    async def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GenerationResult:
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(
                    self._endpoint_url(model),
                    headers=self._request_headers(),
                    json=self._request_body(model, system_prompt, user_prompt, max_tokens, temperature),
                )
        except httpx.RequestError as exc:
            raise ProviderError(f"{self.display_name} request failed: {exc}") from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"{self.display_name} returned {response.status_code}: {truncate_for_error(response.text)}"
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            data = response.json()
            text, prompt_tokens, completion_tokens = self._parse_generation(data)
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(f"{self.display_name} response had an unexpected shape: {exc}") from exc

        return GenerationResult(
            text=text,
            model_name=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
