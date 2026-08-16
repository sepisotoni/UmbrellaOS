"""services/ai/anthropic_provider.py — Anthropic's Messages API."""
from services.ai.base import HTTPProvider

ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicProvider(HTTPProvider):
    name = "anthropic"
    display_name = "Anthropic"
    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"

    def _endpoint_url(self, model: str) -> str:
        return f"{self._base_url}/messages"

    def _request_headers(self) -> dict:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

    def _request_body(self, model, system_prompt, user_prompt, max_tokens, temperature) -> dict:
        return {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    def _parse_generation(self, data: dict) -> tuple[str, int | None, int | None]:
        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        return text, usage.get("input_tokens"), usage.get("output_tokens")
