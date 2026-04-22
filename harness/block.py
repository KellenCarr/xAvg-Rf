"""Block: the single primitive the harness composes.

A block is a folder or a single markdown file with YAML frontmatter + body.
Folder form:  <blocks_dir>/<name>/BLOCK.md  (+ optional scripts, resources)
File form:    <blocks_dir>/<name>.md
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass
class Block:
    name: str
    description: str
    body: str
    load: str = "always"          # always | on_demand | when
    when: str | None = None        # regex string, required iff load == "when"
    entry: str | None = None       # path (relative to block dir) to an executable script
    source_path: Path | None = None
    dir_path: Path | None = None   # folder containing the block, for resolving entry/resources

    def matches(self, user_message: str) -> bool:
        """For load=='when' blocks: does this block's predicate match the current message?"""
        if self.load != "when" or not self.when:
            return False
        return re.search(self.when, user_message, re.IGNORECASE) is not None

    def entry_path(self) -> Path | None:
        if not self.entry or not self.dir_path:
            return None
        return self.dir_path / self.entry


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            f"{path}: missing YAML frontmatter. Every block must start with '---'."
        )
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return frontmatter, body


def _block_from_file(md_path: Path, dir_path: Path | None = None) -> Block:
    fm, body = _parse_markdown(md_path)

    missing = [k for k in ("name", "description") if k not in fm]
    if missing:
        raise ValueError(f"{md_path}: frontmatter missing required keys: {missing}")

    load = fm.get("load", "always")
    if load not in ("always", "on_demand", "when"):
        raise ValueError(
            f"{md_path}: invalid load strategy {load!r}; "
            f"must be one of 'always', 'on_demand', 'when'."
        )
    if load == "when" and not fm.get("when"):
        raise ValueError(f"{md_path}: load: when requires a 'when: <regex>' field.")

    return Block(
        name=fm["name"],
        description=fm["description"],
        body=body,
        load=load,
        when=fm.get("when"),
        entry=fm.get("entry"),
        source_path=md_path,
        dir_path=dir_path or md_path.parent,
    )


def discover_blocks(blocks_dir: Path) -> list[Block]:
    """Walk a directory and return every block found.

    - Any top-level ``*.md`` file is parsed as a block.
    - Any top-level subdirectory containing ``BLOCK.md`` is parsed as a block.
    """
    blocks_dir = Path(blocks_dir)
    if not blocks_dir.exists():
        raise FileNotFoundError(f"blocks_dir does not exist: {blocks_dir}")

    blocks: list[Block] = []
    for entry in sorted(blocks_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".md":
            blocks.append(_block_from_file(entry))
        elif entry.is_dir():
            block_md = entry / "BLOCK.md"
            if block_md.exists():
                blocks.append(_block_from_file(block_md, dir_path=entry))

    seen: dict[str, Path] = {}
    for b in blocks:
        if b.name in seen:
            raise ValueError(
                f"duplicate block name {b.name!r}: "
                f"{seen[b.name]} and {b.source_path}"
            )
        seen[b.name] = b.source_path
    return blocks
