"""Harness: the top-level entry point users interact with."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .block import Block, discover_blocks
from .config import HarnessConfig
from .pipeline import READ_SKILL_TOOL_NAME, ComposedPrompt, compose
from .provider import AnthropicProvider, ProviderReply


MAX_AGENT_STEPS = 10


@dataclass
class AskResult:
    text: str
    prompt: ComposedPrompt
    stop_reason: str
    steps: int = 1


class Harness:
    def __init__(
        self,
        config_path: str | Path | None = None,
        *,
        blocks_dir: str | Path | None = None,
        model: str | None = None,
        thinking: str | None = None,
        max_tokens: int | None = None,
        provider: AnthropicProvider | None = None,
    ):
        if config_path is not None:
            cfg = HarnessConfig.from_file(config_path)
        elif blocks_dir is not None:
            cfg = HarnessConfig(blocks_dir=Path(blocks_dir))
        else:
            raise ValueError("Provide either config_path or blocks_dir.")

        if model is not None:
            cfg.model = model
        if thinking is not None:
            cfg.thinking = thinking
        if max_tokens is not None:
            cfg.max_tokens = max_tokens

        self.config = cfg
        self.blocks: list[Block] = discover_blocks(cfg.blocks_dir)
        self.provider = provider or AnthropicProvider(
            model=cfg.model,
            thinking=cfg.thinking,
            max_tokens=cfg.max_tokens,
        )

    def inspect(self, user_message: str, *, use_skills: bool = False) -> ComposedPrompt:
        """Return the composed prompt *without* calling the API — for debugging."""
        return compose(self.blocks, user_message, use_skills=use_skills)

    def list_blocks(self) -> list[Block]:
        return list(self.blocks)

    def ask(self, user_message: str, *, use_skills: bool = False) -> AskResult:
        prompt = compose(self.blocks, user_message, use_skills=use_skills)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

        if not use_skills or not prompt.tools:
            reply = self.provider.send(
                system=prompt.system,
                messages=messages,
                tools=prompt.tools or None,
            )
            return AskResult(
                text=reply.text,
                prompt=prompt,
                stop_reason=reply.stop_reason,
                steps=1,
            )

        return self._agent_loop(prompt, messages)

    def _agent_loop(
        self,
        prompt: ComposedPrompt,
        messages: list[dict[str, Any]],
    ) -> AskResult:
        on_demand_by_name = {b.name: b for b in prompt.on_demand_blocks}
        skill_scripts_by_name = {b.name: b for b in prompt.skill_tool_blocks}

        reply: ProviderReply | None = None
        for step in range(1, MAX_AGENT_STEPS + 1):
            reply = self.provider.send(
                system=prompt.system,
                messages=messages,
                tools=prompt.tools,
            )
            if reply.stop_reason != "tool_use":
                return AskResult(
                    text=reply.text,
                    prompt=prompt,
                    stop_reason=reply.stop_reason,
                    steps=step,
                )

            tool_uses = [b for b in reply.raw_content if getattr(b, "type", None) == "tool_use"]
            messages.append({"role": "assistant", "content": reply.raw_content})

            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                tool_results.append(
                    self._execute_tool(tu, on_demand_by_name, skill_scripts_by_name)
                )
            messages.append({"role": "user", "content": tool_results})

        # Max steps exhausted.
        return AskResult(
            text=(reply.text if reply else "") + "\n\n[harness: max agent steps reached]",
            prompt=prompt,
            stop_reason="max_steps",
            steps=MAX_AGENT_STEPS,
        )

    def _execute_tool(
        self,
        tool_use: Any,
        on_demand_by_name: dict[str, Block],
        skill_scripts_by_name: dict[str, Block],
    ) -> dict[str, Any]:
        name = tool_use.name
        tool_input = tool_use.input or {}

        if name == READ_SKILL_TOOL_NAME:
            skill_name = tool_input.get("skill_name", "")
            block = on_demand_by_name.get(skill_name)
            if block is None:
                return _error_result(tool_use.id, f"unknown skill: {skill_name!r}")
            return {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": block.body,
            }

        block = skill_scripts_by_name.get(name)
        if block is None:
            return _error_result(tool_use.id, f"unknown tool: {name!r}")

        entry = block.entry_path()
        if entry is None or not entry.exists():
            return _error_result(tool_use.id, f"skill {name!r} has no runnable entry script")

        try:
            completed = subprocess.run(
                [sys.executable, str(entry)],
                input=json.dumps(tool_input),
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(block.dir_path),
            )
        except subprocess.TimeoutExpired:
            return _error_result(tool_use.id, f"skill {name!r} timed out")
        except Exception as e:
            return _error_result(tool_use.id, f"skill {name!r} failed to run: {e}")

        if completed.returncode != 0:
            return _error_result(
                tool_use.id,
                f"skill {name!r} exited {completed.returncode}: {completed.stderr.strip()}",
            )
        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": completed.stdout.strip() or "(no output)",
        }


def _error_result(tool_use_id: str, message: str) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": message,
        "is_error": True,
    }
