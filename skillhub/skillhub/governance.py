from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request

from skillhub import connectors
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
    """Resolved request identity.

    kind: 'human' (role-based UI/CLI) or 'connector' (bearer token).
    role: 'user' | 'admin' for human, 'connector' for an agent.
    actor: display string for audit log.
    scopes: granted scopes (connectors only; humans get implicit '*').
    connector_id: set when kind='connector'.
    """

    kind: str
    role: str
    actor: str
    scopes: list[str]
    connector_id: Optional[str] = None

    def has_scope(self, scope: str) -> bool:
        if self.kind == "human":
            return True
        return scope in self.scopes


def _read_role(req: Request) -> str:
    role = (
        req.headers.get("x-role")
        or req.query_params.get("role")
        or req.cookies.get("skillhub_role")
        or "user"
    )
    return "admin" if role.lower() == "admin" else "user"


def _read_bearer(req: Request) -> Optional[str]:
    h = req.headers.get("authorization") or ""
    if h.lower().startswith("bearer "):
        return h.split(None, 1)[1].strip()
    return None


def identity(request: Request) -> Identity:
    token = _read_bearer(request)
    if token:
        conn = connectors.lookup_by_token(token)
        if conn is None:
            raise HTTPException(401, "invalid or revoked connector token")
        connectors.touch_last_seen(conn.id)
        return Identity(
            kind="connector",
            role="connector",
            actor=f"connector:{conn.name}",
            scopes=list(conn.scopes),
            connector_id=conn.id,
        )
    role = _read_role(request)
    actor = request.headers.get("x-actor") or f"stub:{role}"
    return Identity(kind="human", role=role, actor=actor, scopes=["*"])


def require_admin(request: Request) -> Identity:
    ident = identity(request)
    if ident.kind != "human" or ident.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required (stub)")
    return ident


def require_scope(scope: str):
    """FastAPI dependency factory: requires either human role OR connector scope."""

    def _dep(request: Request) -> Identity:
        ident = identity(request)
        if ident.kind == "human":
            return ident
        if scope not in ident.scopes:
            raise HTTPException(403, f"connector lacks scope '{scope}'")
        return ident

    return _dep


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
