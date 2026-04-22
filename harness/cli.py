"""CLI: ``python -m harness <chat|inspect|list>``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import Harness


def _build_harness(args: argparse.Namespace) -> Harness:
    if args.config:
        return Harness(args.config)
    if args.blocks_dir:
        return Harness(blocks_dir=args.blocks_dir)
    default_config = Path("harness.yaml")
    if default_config.exists():
        return Harness(default_config)
    raise SystemExit(
        "No config found. Pass --config harness.yaml or --blocks-dir <path>."
    )


def cmd_list(args: argparse.Namespace) -> None:
    h = _build_harness(args)
    if not h.blocks:
        print(f"No blocks found in {h.config.blocks_dir}")
        return
    print(f"{len(h.blocks)} block(s) in {h.config.blocks_dir}:\n")
    for b in h.blocks:
        load = b.load
        tag = f"[{load}]"
        if b.load == "when":
            tag += f" when={b.when!r}"
        if b.entry:
            tag += f" +script({b.entry})"
        print(f"  {b.name:<24} {tag}")
        print(f"    {b.description}")


def cmd_inspect(args: argparse.Namespace) -> None:
    h = _build_harness(args)
    prompt = h.inspect(args.message, use_skills=args.skills)
    print("─── SYSTEM PROMPT ───")
    print(prompt.system)
    print("─── TOOLS ───")
    if not prompt.tools:
        print("(none)")
    for t in prompt.tools:
        print(f"  - {t['name']}: {t['description'].splitlines()[0]}")
    print("─── LOADED BLOCKS ───")
    for b in prompt.loaded_blocks:
        print(f"  always/when: {b.name}")
    for b in prompt.on_demand_blocks:
        print(f"  on_demand:   {b.name}")
    for b in prompt.skill_tool_blocks:
        print(f"  skill+tool:  {b.name}")


def cmd_chat(args: argparse.Namespace) -> None:
    h = _build_harness(args)
    print(f"harness: {len(h.blocks)} block(s) loaded. skills={'on' if args.skills else 'off'}.")
    print("Type a message. Ctrl-D or empty line to exit.\n")
    try:
        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                print()
                break
            if not line:
                break
            result = h.ask(line, use_skills=args.skills)
            print(f"\nclaude> {result.text}\n")
            if result.steps > 1:
                print(f"  (agent loop: {result.steps} step(s))\n")
    except KeyboardInterrupt:
        print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--config", help="path to harness.yaml")
    parser.add_argument("--blocks-dir", help="path to a blocks directory (if no config)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list all discovered blocks")
    p_list.set_defaults(func=cmd_list)

    p_inspect = sub.add_parser(
        "inspect", help="show the composed system prompt for a message (no API call)"
    )
    p_inspect.add_argument("message", help="the user message to inspect against")
    p_inspect.add_argument("--skills", action="store_true", help="include on-demand blocks and skill tools")
    p_inspect.set_defaults(func=cmd_inspect)

    p_chat = sub.add_parser("chat", help="interactive chat REPL")
    p_chat.add_argument("--skills", action="store_true", help="enable on-demand blocks and skill tools")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
