"""LLM abstraction for agent. Injectable for testing.

Uses Anthropic by default (ANTHROPIC_API_KEY), OpenAI as fallback.
Both via langchain wrappers. Tests inject a FakeLLM.
"""

from typing import Any, Protocol

from app.core.config import settings
from app.core.exceptions import LLMError


class LLM(Protocol):
    """Minimal LLM interface: async invoke with messages, return text."""

    async def ainvoke(self, messages: list[dict[str, str]]) -> str: ...

    @property
    def model_name(self) -> str: ...


class AnthropicLLM:
    """Anthropic-backed LLM via langchain-anthropic."""

    def __init__(self, model: str | None = None) -> None:
        from langchain_anthropic import ChatAnthropic

        api_key = settings.anthropic_api_key or _read_env("ANTHROPIC_API_KEY")
        self._model = ChatAnthropic(
            model=model or settings.ai_default_model,
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )
        self._name = model or settings.ai_default_model

    async def ainvoke(self, messages: list[dict[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = [
            SystemMessage(content=m["content"]) if m["role"] == "system"
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        try:
            resp = await self._model.ainvoke(lc_messages)
        except Exception as exc:
            raise LLMError(f"anthropic call failed: {exc}") from exc
        return resp.content if isinstance(resp.content, str) else str(resp.content)

    @property
    def model_name(self) -> str:
        return self._name


class OpenAILLM:
    """OpenAI-backed LLM via langchain-openai. Supports OpenAI-compatible gateways."""

    def __init__(self, model: str | None = None) -> None:
        from langchain_openai import ChatOpenAI

        api_key = settings.openai_api_key or _read_env("OPENAI_API_KEY")
        resolved_model = model or settings.ai_model or "gpt-4o-mini"
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "api_key": api_key,
            "temperature": 0,
            "max_tokens": 4096,
        }
        if settings.ai_base_url:
            kwargs["base_url"] = settings.ai_base_url
        self._model = ChatOpenAI(**kwargs)
        self._name = resolved_model

    async def ainvoke(self, messages: list[dict[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = [
            SystemMessage(content=m["content"]) if m["role"] == "system"
            else HumanMessage(content=m["content"])
            for m in messages
        ]
        try:
            resp = await self._model.ainvoke(lc_messages)
        except Exception as exc:
            raise LLMError(f"openai call failed: {exc}") from exc
        return resp.content if isinstance(resp.content, str) else str(resp.content)

    @property
    def model_name(self) -> str:
        return self._name


def get_llm(provider: str | None = None) -> LLM:
    """Build LLM from config. provider: anthropic | openai.

    Auto-detects: if AI_PROVIDER unset and ANTHROPIC_API_KEY missing but
    OPENAI_API_KEY present, defaults to openai (supports OpenAI-compatible gateways).
    """
    import os

    if provider is None:
        provider = settings.ai_provider
        if provider == "anthropic" and not (settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")):
            if settings.openai_api_key or os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
    if provider == "anthropic":
        return AnthropicLLM()
    if provider == "openai":
        return OpenAILLM()
    raise LLMError(f"unknown LLM provider: {provider}")


def _read_env(key: str) -> str:
    import os

    val = os.environ.get(key, "")
    if not val:
        raise LLMError(f"missing env var: {key}")
    return val
