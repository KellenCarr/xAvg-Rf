"""Thin Anthropic SDK wrapper. Swap this file to support a different provider later."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import anthropic


@dataclass
class ProviderReply:
    text: str
    stop_reason: str
    raw_content: list[Any]           # full content blocks for appending back into messages
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


class AnthropicProvider:
    """Streaming calls to Claude, with prompt caching on the system prompt."""

    def __init__(
        self,
        model: str = "claude-opus-4-7",
        thinking: str = "adaptive",
        max_tokens: int = 16000,
        client: anthropic.Anthropic | None = None,
    ):
        self.model = model
        self.thinking = thinking
        self.max_tokens = max_tokens
        self.client = client or anthropic.Anthropic()

    def _thinking_param(self) -> dict[str, Any] | None:
        if self.thinking == "adaptive":
            return {"type": "adaptive"}
        if self.thinking == "disabled":
            return {"type": "disabled"}
        return None

    def send(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ProviderReply:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            # Cache the system prompt — it's the heaviest shared prefix.
            "system": [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": messages,
        }
        thinking = self._thinking_param()
        if thinking is not None:
            kwargs["thinking"] = thinking
        if tools:
            kwargs["tools"] = tools

        with self.client.messages.stream(**kwargs) as stream:
            final = stream.get_final_message()

        text = next(
            (b.text for b in final.content if getattr(b, "type", None) == "text"),
            "",
        )
        return ProviderReply(
            text=text,
            stop_reason=final.stop_reason or "",
            raw_content=list(final.content),
            input_tokens=final.usage.input_tokens,
            output_tokens=final.usage.output_tokens,
            cache_read_input_tokens=getattr(final.usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
        )
