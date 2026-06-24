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

        api_key = _read_env("ANTHROPIC_API_KEY")
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
    """OpenAI-backed LLM via langchain-openai."""

    def __init__(self, model: str | None = None) -> None:
        from langchain_openai import ChatOpenAI

        api_key = _read_env("OPENAI_API_KEY")
        self._model = ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key,
            temperature=0,
            max_tokens=4096,
        )
        self._name = model or "gpt-4o-mini"

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
    """Build LLM from config. provider: anthropic | openai."""
    provider = provider or "anthropic"
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
