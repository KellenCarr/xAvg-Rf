from __future__ import annotations

import io
import json
import os
import sys
import tarfile
from pathlib import Path
from typing import Optional

import httpx
import typer
import yaml

app = typer.Typer(help="SkillHub CLI: search, install, submit, approve agent skills/tools.")

CONFIG_DIR = Path.home() / ".skillhub"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_REGISTRY_URL = "http://localhost:8765"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_config(d: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(d, indent=2))


def _client() -> httpx.Client:
    cfg = _load_config()
    base = os.environ.get("SKILLHUB_URL") or cfg.get("registry_url", DEFAULT_REGISTRY_URL)
    headers: dict[str, str] = {}
    token = os.environ.get("SKILLHUB_TOKEN") or cfg.get("connector_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["X-Role"] = cfg.get("role", "user")
    return httpx.Client(base_url=base, headers=headers, timeout=20.0)


def _print_table(rows: list[dict], cols: list[tuple[str, str]]) -> None:
    if not rows:
        typer.echo("(no entries)")
        return
    widths = {key: max(len(label), *(len(str(r.get(key, ""))) for r in rows)) for key, label in cols}
    typer.echo("  ".join(label.ljust(widths[key]) for key, label in cols))
    typer.echo("  ".join("-" * widths[key] for key, _ in cols))
    for r in rows:
        typer.echo("  ".join(str(r.get(key, "")).ljust(widths[key]) for key, _ in cols))


@app.command()
def connect(
    token: str = typer.Argument(..., help="bearer token (skh_...) for a registered connector"),
    registry_url: str = typer.Option(DEFAULT_REGISTRY_URL, "--registry-url", help="SkillHub base URL"),
):
    """Save a connector bearer token. Subsequent calls authenticate as the connector."""
    if not token.startswith("skh_"):
        typer.echo("token should start with 'skh_'", err=True)
        raise typer.Exit(1)
    cfg = _load_config()
    cfg["connector_token"] = token
    cfg["registry_url"] = registry_url
    cfg.pop("role", None)
    _save_config(cfg)
    # Verify against the server.
    try:
        with _client() as c:
            r = c.get("/api/connectors/me")
            if r.status_code != 200:
                typer.echo(f"server rejected token: {r.status_code} {r.text}", err=True)
                raise typer.Exit(2)
            me = r.json()
    except httpx.HTTPError as e:
        typer.echo(f"could not reach {registry_url}: {e}", err=True)
        raise typer.Exit(2)
    typer.echo(f"connected as '{me['name']}' (id={me['connector_id']}) scopes={me['scopes']}")


@app.command()
def login(
    role: str = typer.Option("user", help="user | admin"),
    registry_url: str = typer.Option(DEFAULT_REGISTRY_URL, help="registry base URL"),
):
    """Stub login: persists role + registry URL to ~/.skillhub/config.json."""
    role = "admin" if role.lower() == "admin" else "user"
    cfg = _load_config()
    cfg.update({"role": role, "registry_url": registry_url})
    cfg.pop("connector_token", None)
    _save_config(cfg)
    typer.echo(f"role={role} registry={registry_url} (stub auth)")


@app.command()
def whoami():
    """Print local identity and what the server says about the current credentials."""
    cfg = _load_config()
    local = {
        "registry_url": cfg.get("registry_url", DEFAULT_REGISTRY_URL),
        "auth": "connector" if cfg.get("connector_token") else "role",
        "role": cfg.get("role", "user"),
    }
    typer.echo("local: " + json.dumps(local))
    try:
        with _client() as c:
            r = c.get("/api/whoami")
            if r.status_code == 200:
                typer.echo("server: " + json.dumps(r.json()))
            else:
                typer.echo(f"server: {r.status_code} {r.text}", err=True)
    except httpx.HTTPError as e:
        typer.echo(f"server: unreachable ({e})", err=True)


@app.command()
def search(
    query: Optional[str] = typer.Argument(None),
    kind: Optional[str] = typer.Option(None, help="skill | mcp_server"),
    namespace: Optional[str] = typer.Option(None),
    status: Optional[str] = typer.Option(None),
):
    """Search the registry."""
    params = {k: v for k, v in [("q", query), ("kind", kind), ("namespace", namespace), ("status", status)] if v}
    with _client() as c:
        r = c.get("/api/entries", params=params)
        r.raise_for_status()
        data = r.json()
    rows = [
        {
            "id": f"{e['namespace']}/{e['name']}",
            "kind": e["kind"],
            "version": e["version"],
            "status": e["status"],
            "perms": str(len(e.get("permissions", []))),
            "description": e["description"][:60],
        }
        for e in data
    ]
    _print_table(rows, [("id", "ID"), ("kind", "KIND"), ("version", "VERSION"), ("status", "STATUS"), ("perms", "PERMS"), ("description", "DESCRIPTION")])


@app.command()
def info(target: str = typer.Argument(..., help="namespace/name")):
    """Show full manifest."""
    ns, name = _parse_target(target)
    with _client() as c:
        r = c.get(f"/api/entries/{ns}/{name}")
        if r.status_code == 404:
            typer.echo(f"not found: {target}", err=True)
            raise typer.Exit(1)
        r.raise_for_status()
    typer.echo(yaml.safe_dump(r.json(), sort_keys=False))


@app.command()
def add(
    target: str = typer.Argument(..., help="namespace/name"),
    project: Path = typer.Option(Path("."), "--project", help="target Claude Code project root"),
    yes: bool = typer.Option(False, "--yes", help="skip permission prompt"),
    allow_unapproved: bool = typer.Option(False, "--allow-unapproved", help="install entries with status != approved"),
):
    """Install a skill or MCP server into a Claude Code project."""
    ns, name = _parse_target(target)
    with _client() as c:
        r = c.get(f"/api/entries/{ns}/{name}")
        if r.status_code == 404:
            typer.echo(f"not found: {target}", err=True)
            raise typer.Exit(1)
        r.raise_for_status()
        m = r.json()

        if m["status"] != "approved" and not allow_unapproved:
            typer.echo(
                f"refusing: {target} has status='{m['status']}' (pass --allow-unapproved to override)",
                err=True,
            )
            raise typer.Exit(2)

        perms = m.get("permissions", [])
        typer.echo(f"{target}  kind={m['kind']}  version={m['version']}  status={m['status']}")
        typer.echo(f"declared permissions: {perms or '(none)'}")
        if not yes:
            ok = typer.confirm("Continue with install?", default=False)
            if not ok:
                raise typer.Exit(1)

        if m["kind"] == "skill":
            r2 = c.get(f"/api/entries/{ns}/{name}/payload")
            r2.raise_for_status()
            install_path = m["skill"]["install_path"].format(name=name)
            target_dir = project / install_path
            target_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(r2.content), mode="r:gz") as tar:
                _safe_extract(tar, target_dir)
            typer.echo(f"installed skill -> {target_dir}")
        elif m["kind"] == "mcp_server":
            mcp_path = project / ".mcp.json"
            doc = {"mcpServers": {}}
            if mcp_path.exists():
                try:
                    doc = json.loads(mcp_path.read_text())
                    doc.setdefault("mcpServers", {})
                except Exception as e:
                    typer.echo(f"warn: existing .mcp.json unparseable, replacing: {e}")
            key = m["mcp_server"]["mcp_json_key"]
            doc["mcpServers"][key] = {
                "command": m["mcp_server"]["command"],
                "args": m["mcp_server"]["args"],
                "env": m["mcp_server"]["env"],
            }
            mcp_path.parent.mkdir(parents=True, exist_ok=True)
            mcp_path.write_text(json.dumps(doc, indent=2))
            typer.echo(f"installed mcp_server '{key}' -> {mcp_path}")
        else:
            typer.echo(f"unknown kind: {m['kind']}", err=True)
            raise typer.Exit(2)


@app.command()
def submit(
    manifest: Path = typer.Argument(..., help="path to manifest.yaml"),
    payload: Optional[Path] = typer.Option(None, help="optional file to attach as payload (e.g. SKILL.md)"),
):
    """Submit a manifest. Server forces status=pending."""
    if not manifest.exists():
        typer.echo(f"missing manifest: {manifest}", err=True)
        raise typer.Exit(1)
    with _client() as c:
        files = None
        if payload and payload.exists():
            files = {"payload_file": (payload.name, payload.read_bytes())}
        data = {"manifest_yaml": manifest.read_text()}
        r = c.post("/api/entries", data=data, files=files)
        if r.status_code >= 400:
            typer.echo(f"submit failed [{r.status_code}]: {r.text}", err=True)
            raise typer.Exit(2)
        out = r.json()
    typer.echo(f"submitted {out['namespace']}/{out['name']} status={out['status']}")


@app.command()
def approve(target: str = typer.Argument(..., help="namespace/name")):
    """Approve a pending entry (admin role required)."""
    _set_status(target, "approve")


@app.command()
def reject(target: str = typer.Argument(..., help="namespace/name")):
    """Reject a pending entry (admin role required)."""
    _set_status(target, "reject")


@app.command()
def audit(limit: int = 50):
    """Read recent audit events (admin)."""
    with _client() as c:
        r = c.get("/api/audit", params={"limit": limit})
        if r.status_code == 403:
            typer.echo("admin role required (skillhub login --role admin)", err=True)
            raise typer.Exit(1)
        r.raise_for_status()
    for ev in r.json():
        typer.echo(json.dumps(ev))


def _set_status(target: str, action: str) -> None:
    ns, name = _parse_target(target)
    with _client() as c:
        r = c.post(f"/api/entries/{ns}/{name}/{action}")
        if r.status_code == 403:
            typer.echo("admin role required (skillhub login --role admin)", err=True)
            raise typer.Exit(1)
        if r.status_code == 404:
            typer.echo(f"not found: {target}", err=True)
            raise typer.Exit(1)
        r.raise_for_status()
        out = r.json()
    typer.echo(f"{target} -> status={out['status']} reviewer={out.get('reviewer')}")


def _parse_target(t: str) -> tuple[str, str]:
    if "/" not in t:
        typer.echo(f"expected 'namespace/name', got '{t}'", err=True)
        raise typer.Exit(1)
    ns, name = t.split("/", 1)
    return ns, name


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if not str(target).startswith(str(dest)):
            raise RuntimeError(f"unsafe path in tar: {member.name}")
    tar.extractall(dest)


if __name__ == "__main__":
    app()
