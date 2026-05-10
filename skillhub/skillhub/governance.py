from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request

from skillhub.manifest import has_high_risk
from skillhub.storage import load_allowlist


# Static namespace registry for the prototype.
NAMESPACES = {
    "acme": {"visibility_default": "private", "label": "Acme Inc. (private)"},
    "platform": {"visibility_default": "private", "label": "Platform team (private)"},
    "community": {"visibility_default": "public", "label": "Community (public)"},
}


@dataclass
class Identity:
    role: str  # "user" | "admin"
    actor: str  # display string for audit log


def _read_role(req: Request) -> str:
    role = (
        req.headers.get("x-role")
        or req.query_params.get("role")
        or req.cookies.get("skillhub_role")
        or "user"
    )
    return "admin" if role.lower() == "admin" else "user"


def identity(request: Request) -> Identity:
    r = _read_role(request)
    actor = request.headers.get("x-actor") or f"stub:{r}"
    return Identity(role=r, actor=actor)


def require_admin(request: Request) -> Identity:
    ident = identity(request)
    if ident.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required (stub)")
    return ident


def check_namespace_allowed(namespace: str) -> None:
    allow = load_allowlist()
    if allow and namespace not in allow:
        raise HTTPException(
            status_code=400,
            detail=f"namespace '{namespace}' not in allowlist {allow}",
        )


def classify_permissions(perms: list[str]) -> dict:
    return {
        "high_risk": has_high_risk(perms),
        "permissions": perms,
    }
