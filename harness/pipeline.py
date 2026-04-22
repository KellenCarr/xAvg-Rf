"""Composition pipeline: blocks + user message -> system prompt + tools.

Stages:
  1. filter    — pick the blocks that apply to this message
  2. inject    — add dynamic values (current date)
  3. render    — emit system prompt text + optional tool list
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .block import Block


READ_SKILL_TOOL_NAME = "read_skill"


@dataclass
class ComposedPrompt:
    """The final, inspectable output of the pipeline."""
    system: str
    tools: list[dict[str, Any]]
    loaded_blocks: list[Block] = field(default_factory=list)
    on_demand_blocks: list[Block] = field(default_factory=list)
    skill_tool_blocks: list[Block] = field(default_factory=list)


def _render_block(block: Block) -> str:
    return (
        f"<block name=\"{block.name}\">\n"
        f"{block.body}\n"
        f"</block>"
    )


def _render_on_demand_manifest(blocks: list[Block]) -> str:
    lines = [
        "The following skills are available. "
        f"Call the `{READ_SKILL_TOOL_NAME}` tool with the skill's name to load its full instructions.",
        "",
    ]
    for b in blocks:
        lines.append(f"- **{b.name}**: {b.description}")
    return "\n".join(lines)


def _read_skill_tool(on_demand_blocks: list[Block]) -> dict[str, Any]:
    names = [b.name for b in on_demand_blocks]
    return {
        "name": READ_SKILL_TOOL_NAME,
        "description": (
            "Load the full instructions for an available skill. "
            "Call this when the user's request matches one of the skill descriptions "
            "shown in the system prompt."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "enum": names,
                    "description": "The name of the skill to load.",
                },
            },
            "required": ["skill_name"],
            "additionalProperties": False,
        },
    }


def _entry_script_tool(block: Block) -> dict[str, Any]:
    return {
        "name": block.name,
        "description": (
            f"{block.description}\n\n"
            "Call with a single field 'input' containing the string to process. "
            "Returns the script's stdout as text."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input passed to the script on stdin as JSON.",
                },
            },
            "required": ["input"],
            "additionalProperties": False,
        },
    }


def compose(
    blocks: list[Block],
    user_message: str,
    *,
    use_skills: bool = False,
) -> ComposedPrompt:
    always = [b for b in blocks if b.load == "always"]
    when_matched = [b for b in blocks if b.load == "when" and b.matches(user_message)]
    on_demand = [b for b in blocks if b.load == "on_demand"]
    skill_scripts = [b for b in blocks if b.entry]

    parts: list[str] = []

    today = _dt.date.today().isoformat()
    parts.append(f"<context>\nToday's date: {today}\n</context>")

    for b in always + when_matched:
        parts.append(_render_block(b))

    loaded_blocks = list(always + when_matched)

    tools: list[dict[str, Any]] = []

    if use_skills:
        if on_demand:
            parts.append(_render_on_demand_manifest(on_demand))
            tools.append(_read_skill_tool(on_demand))
        for b in skill_scripts:
            tools.append(_entry_script_tool(b))

    system = "\n\n".join(parts)
    return ComposedPrompt(
        system=system,
        tools=tools,
        loaded_blocks=loaded_blocks,
        on_demand_blocks=on_demand if use_skills else [],
        skill_tool_blocks=skill_scripts if use_skills else [],
    )
