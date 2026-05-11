"""Connector identity model.

A "connector" represents an AI agent (or fleet of agents) that has been
registered with this registry. Each connector has a name, a bearer token,
and a set of scopes. Tokens are stored as sha256 hashes; the plaintext is
shown once at creation time.

Storage: registry/.connectors.json (gitignored, treated as runtime state).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from skillhub.storage import registry_root

VALID_SCOPES = {"read", "install", "submit"}
DEFAULT_SCOPES = ["read", "install"]
TOKEN_PREFIX = "skh_"


def _store_path() -> Path:
    return registry_root() / ".connectors.json"


@dataclass
class Connector:
    id: str
    name: str
    token_hash: str
    token_prefix: str  # first 8 chars of the plaintext, for UI identification
    scopes: list[str]
    created_at: int
    created_by: str
    last_seen_at: Optional[int] = None
    status: str = "active"  # active | revoked

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "token_prefix": self.token_prefix,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
        }


def _load_all() -> list[Connector]:
    p = _store_path()
    if not p.exists():
        return []
    raw = json.loads(p.read_text() or "[]")
    return [Connector(**c) for c in raw]


def _save_all(conns: list[Connector]) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([asdict(c) for c in conns], indent=2))


def list_connectors() -> list[Connector]:
    return _load_all()


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def register(name: str, scopes: list[str], created_by: str) -> tuple[Connector, str]:
    """Create a connector. Returns (connector, plaintext_token).
    The plaintext token is the ONLY time the caller will ever see it."""
    name = name.strip()
    if not name:
        raise ValueError("connector name required")
    bad = [s for s in scopes if s not in VALID_SCOPES]
    if bad:
        raise ValueError(f"invalid scopes: {bad} (valid: {sorted(VALID_SCOPES)})")
    token = generate_token()
    conn = Connector(
        id=f"cn_{secrets.token_hex(6)}",
        name=name,
        token_hash=hash_token(token),
        token_prefix=token[: len(TOKEN_PREFIX) + 4],
        scopes=list(scopes),
        created_at=int(time.time()),
        created_by=created_by,
    )
    conns = _load_all()
    conns.append(conn)
    _save_all(conns)
    return conn, token


def revoke(connector_id: str) -> Optional[Connector]:
    conns = _load_all()
    for c in conns:
        if c.id == connector_id:
            c.status = "revoked"
            _save_all(conns)
            return c
    return None


def lookup_by_token(token: str) -> Optional[Connector]:
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    h = hash_token(token)
    for c in _load_all():
        if c.token_hash == h and c.status == "active":
            return c
    return None


def touch_last_seen(connector_id: str) -> None:
    conns = _load_all()
    changed = False
    for c in conns:
        if c.id == connector_id:
            c.last_seen_at = int(time.time())
            changed = True
            break
    if changed:
        _save_all(conns)
