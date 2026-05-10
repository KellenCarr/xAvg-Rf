from __future__ import annotations

import re
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,49}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+][\w.-]+)?$")

Status = Literal["pending", "approved", "rejected"]
Visibility = Literal["private", "public"]


class _Common(BaseModel):
    apiVersion: Literal["skillhub/v0"] = "skillhub/v0"
    namespace: str
    name: str
    version: str
    description: str = Field(min_length=1, max_length=500)
    author: str
    status: Status = "pending"
    reviewer: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)
    visibility: Visibility = "private"
    signature: str = "UNSIGNED-PROTOTYPE"

    @field_validator("namespace", "name")
    @classmethod
    def _name_ok(cls, v: str) -> str:
        if not NAME_RE.match(v):
            raise ValueError(f"must match {NAME_RE.pattern}")
        return v

    @field_validator("version")
    @classmethod
    def _semver_ok(cls, v: str) -> str:
        if not SEMVER_RE.match(v):
            raise ValueError("must be semver (e.g. 1.2.3)")
        return v


class SkillBody(BaseModel):
    entrypoint: str = "payload/SKILL.md"
    install_path: str = ".claude/skills/{name}/"


class McpBody(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    mcp_json_key: str


class SkillEntry(_Common):
    kind: Literal["skill"]
    skill: SkillBody = Field(default_factory=SkillBody)


class McpEntry(_Common):
    kind: Literal["mcp_server"]
    mcp_server: McpBody


Manifest = Annotated[Union[SkillEntry, McpEntry], Field(discriminator="kind")]


class _Wrapper(BaseModel):
    """Internal wrapper used to validate either kind via discriminator."""

    root: Manifest


def parse_manifest(data: dict) -> Union[SkillEntry, McpEntry]:
    return _Wrapper(root=data).root


def manifest_to_dict(m: Union[SkillEntry, McpEntry]) -> dict:
    return m.model_dump(mode="json", exclude_none=False)


HIGH_RISK_PERMS_PREFIXES = ("write_files", "run_shell", "network")


def has_high_risk(perms: list[str]) -> bool:
    return any(p.split(":", 1)[0] in HIGH_RISK_PERMS_PREFIXES for p in perms)
