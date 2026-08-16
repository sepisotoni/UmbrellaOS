"""services/ai/openrouter_provider.py — OpenRouter (aggregates many
underlying model vendors behind one API, OpenAI-compatible request shape)."""
from services.ai.base import HTTPProvider


class OpenRouterProvider(HTTPProvider):
    name = "openrouter"
    display_name = "OpenRouter"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def _endpoint_url(self, model: str) -> str:
        return f"{self._base_url}/chat/completions"

    def _request_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _request_body(self, model, system_prompt, user_prompt, max_tokens, temperature) -> dict:
        return {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    def _parse_generation(self, data: dict) -> tuple[str, int | None, int | None]:
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, usage.get("prompt_tokens"), usage.get("completion_tokens")
