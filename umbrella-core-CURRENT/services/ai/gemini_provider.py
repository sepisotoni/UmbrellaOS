"""services/ai/gemini_provider.py — Google Gemini's generateContent API."""
from services.ai.base import HTTPProvider


class GeminiProvider(HTTPProvider):
    name = "gemini"
    display_name = "Gemini"
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def _endpoint_url(self, model: str) -> str:
        return f"{self._base_url}/models/{model}:generateContent"

    def _request_headers(self) -> dict:
        return {"x-goog-api-key": self._api_key}

    def _request_body(self, model, system_prompt, user_prompt, max_tokens, temperature) -> dict:
        return {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

    def _parse_generation(self, data: dict) -> tuple[str, int | None, int | None]:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return text, usage.get("promptTokenCount"), usage.get("candidatesTokenCount")
