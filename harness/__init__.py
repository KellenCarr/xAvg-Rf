"""Harness — a flexible AI-model harness for context engineering."""
from .block import Block, discover_blocks
from .config import HarnessConfig
from .core import AskResult, Harness
from .pipeline import ComposedPrompt, compose
from .provider import AnthropicProvider, ProviderReply

__all__ = [
    "AnthropicProvider",
    "AskResult",
    "Block",
    "ComposedPrompt",
    "Harness",
    "HarnessConfig",
    "ProviderReply",
    "compose",
    "discover_blocks",
]
