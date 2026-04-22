"""Load harness.yaml — the non-technical-user surface."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class HarnessConfig:
    blocks_dir: Path
    model: str = "claude-opus-4-7"
    thinking: str = "adaptive"         # "adaptive" | "disabled"
    max_tokens: int = 16000
    config_path: Path | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> "HarnessConfig":
        path = Path(path).resolve()
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        if "blocks_dir" not in data:
            raise ValueError(f"{path}: missing required field 'blocks_dir'")

        blocks_dir = Path(data["blocks_dir"])
        if not blocks_dir.is_absolute():
            blocks_dir = (path.parent / blocks_dir).resolve()

        return cls(
            blocks_dir=blocks_dir,
            model=data.get("model", "claude-opus-4-7"),
            thinking=data.get("thinking", "adaptive"),
            max_tokens=int(data.get("max_tokens", 16000)),
            config_path=path,
        )
