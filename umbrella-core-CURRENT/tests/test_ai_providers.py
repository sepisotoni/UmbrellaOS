"""
tests/test_ai_providers.py - Tests for services/ai/{openrouter,anthropic,
gemini}_provider.py, using httpx.MockTransport injected through each
provider's real constructor (same pattern as tests/test_daemon_client.py).
"""
import json

import httpx
import pytest

from services.ai.anthropic_provider import AnthropicProvider
from services.ai.base import ProviderError
from services.ai.gemini_provider import GeminiProvider
from services.ai.openrouter_provider import OpenRouterProvider


@pytest.mark.asyncio
async def test_openrouter_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello from the model"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    provider = OpenRouterProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    result = await provider.generate("some-model", "system prompt", "user prompt")

    assert result.text == "hello from the model"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5
    assert result.model_name == "some-model"


@pytest.mark.asyncio
async def test_openrouter_rejects_empty_api_key():
    with pytest.raises(ProviderError):
        OpenRouterProvider(api_key="")


@pytest.mark.asyncio
async def test_openrouter_http_error_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="invalid api key")

    provider = OpenRouterProvider(api_key="bad-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="401"):
        await provider.generate("some-model", "sys", "user")


@pytest.mark.asyncio
async def test_openrouter_malformed_response_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = OpenRouterProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="unexpected shape"):
        await provider.generate("some-model", "sys", "user")


@pytest.mark.asyncio
async def test_openrouter_network_error_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = OpenRouterProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="request failed"):
        await provider.generate("some-model", "sys", "user")


@pytest.mark.asyncio
async def test_anthropic_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "hello from claude"}],
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
        )

    provider = AnthropicProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    result = await provider.generate("claude-x", "system", "user")

    assert result.text == "hello from claude"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 8


@pytest.mark.asyncio
async def test_anthropic_sends_system_prompt_as_top_level_field():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured["system"] = body.get("system")
        captured["messages"] = body.get("messages")
        return httpx.Response(200, json={"content": [{"text": "ok"}]})

    provider = AnthropicProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    await provider.generate("claude-x", "you are a helpful bot", "hi there")

    assert captured["system"] == "you are a helpful bot"
    assert captured["messages"] == [{"role": "user", "content": "hi there"}]


@pytest.mark.asyncio
async def test_anthropic_rejects_empty_api_key():
    with pytest.raises(ProviderError):
        AnthropicProvider(api_key="")


@pytest.mark.asyncio
async def test_anthropic_http_error_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(529, text="overloaded")

    provider = AnthropicProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="529"):
        await provider.generate("claude-x", "sys", "user")


@pytest.mark.asyncio
async def test_gemini_generate_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-key"
        assert "key" not in request.url.params
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}],
                "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3},
            },
        )

    provider = GeminiProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    result = await provider.generate("gemini-x", "system", "user")

    assert result.text == "hello from gemini"
    assert result.prompt_tokens == 7
    assert result.completion_tokens == 3


@pytest.mark.asyncio
async def test_gemini_sends_system_instruction_separately():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured["systemInstruction"] = body.get("systemInstruction")
        captured["contents"] = body.get("contents")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    provider = GeminiProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    await provider.generate("gemini-x", "be nice", "hello")

    assert captured["systemInstruction"] == {"parts": [{"text": "be nice"}]}
    assert captured["contents"] == [{"role": "user", "parts": [{"text": "hello"}]}]


@pytest.mark.asyncio
async def test_gemini_rejects_empty_api_key():
    with pytest.raises(ProviderError):
        GeminiProvider(api_key="")


@pytest.mark.asyncio
async def test_gemini_malformed_response_raises_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    provider = GeminiProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderError, match="unexpected shape"):
        await provider.generate("gemini-x", "sys", "user")
