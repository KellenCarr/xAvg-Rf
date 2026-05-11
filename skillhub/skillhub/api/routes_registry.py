from __future__ import annotations

import io
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from skillhub import connectors, storage
from skillhub.governance import (
    NAMESPACES,
    check_namespace_allowed,
    identity,
    require_admin,
    require_scope,
)
from skillhub.manifest import manifest_to_dict, parse_manifest

router = APIRouter(prefix="/api", tags=["registry"])


# ---------- meta ----------


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/whoami")
def whoami(request: Request) -> dict:
    ident = identity(request)
    out = {
        "kind": ident.kind,
        "role": ident.role,
        "actor": ident.actor,
        "scopes": ident.scopes,
    }
    if ident.connector_id:
        out["connector_id"] = ident.connector_id
    return out


@router.get("/namespaces")
def namespaces() -> dict:
    return NAMESPACES


# ---------- registry ----------


@router.get("/entries")
def list_entries(
    request: Request,
    q: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    namespace: Optional[str] = None,
    visibility: Optional[str] = None,
    ident=Depends(require_scope("read")),
) -> list[dict]:
    idx = storage.read_index()
    out = idx["entries"]
    if q:
        ql = q.lower()
        out = [e for e in out if ql in e["name"].lower() or ql in e["description"].lower()]
    if kind:
        out = [e for e in out if e["kind"] == kind]
    if status:
        out = [e for e in out if e["status"] == status]
    if namespace:
        out = [e for e in out if e["namespace"] == namespace]
    if visibility:
        out = [e for e in out if e["visibility"] == visibility]
    return out


@router.get("/entries/{namespace}/{name}")
def get_entry(namespace: str, name: str, ident=Depends(require_scope("read"))) -> dict:
    try:
        m = storage.load_manifest(namespace, name)
    except FileNotFoundError:
        raise HTTPException(404, f"{namespace}/{name} not found")
    return manifest_to_dict(m)


@router.get("/entries/{namespace}/{name}/payload")
def get_payload(namespace: str, name: str, ident=Depends(require_scope("install"))) -> StreamingResponse:
    try:
        storage.load_manifest(namespace, name)
    except FileNotFoundError:
        raise HTTPException(404, f"{namespace}/{name} not found")
    data = storage.make_payload_tar(namespace, name)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{name}.tar.gz"'},
    )


@router.post("/entries")
async def submit_entry(
    request: Request,
    manifest_yaml: str = Form(...),
    payload_file: Optional[UploadFile] = File(default=None),
    ident=Depends(require_scope("submit")),
) -> dict:
    try:
        data = yaml.safe_load(manifest_yaml)
        m = parse_manifest(data)
    except Exception as e:
        raise HTTPException(400, f"invalid manifest: {e}")

    check_namespace_allowed(m.namespace)
    m.status = "pending"
    m.reviewer = None
    storage.write_manifest(m)
    if payload_file is not None:
        target = storage.payload_dir(m.namespace, m.name)
        target.mkdir(parents=True, exist_ok=True)
        content = await payload_file.read()
        (target / (payload_file.filename or "SKILL.md")).write_bytes(content)
    storage.rebuild_index()
    storage.append_audit(
        action="submit",
        target=f"{m.namespace}/{m.name}",
        actor_role=ident.role,
        before=None,
        after="pending",
        extra={"version": m.version, "actor": ident.actor},
    )
    return manifest_to_dict(m)


@router.post("/entries/{namespace}/{name}/approve")
def approve(namespace: str, name: str, request: Request, ident=Depends(require_admin)) -> dict:
    try:
        return storage.set_status(namespace, name, "approved", reviewer=ident.actor, actor_role=ident.role)
    except FileNotFoundError:
        raise HTTPException(404, f"{namespace}/{name} not found")


@router.post("/entries/{namespace}/{name}/reject")
def reject(namespace: str, name: str, request: Request, ident=Depends(require_admin)) -> dict:
    try:
        return storage.set_status(namespace, name, "rejected", reviewer=ident.actor, actor_role=ident.role)
    except FileNotFoundError:
        raise HTTPException(404, f"{namespace}/{name} not found")


@router.get("/audit")
def get_audit(request: Request, ident=Depends(require_admin), limit: int = 200) -> list[dict]:
    return storage.read_audit(limit=limit)


# ---------- connectors ----------


@router.post("/connectors")
def create_connector(
    request: Request,
    name: str = Form(...),
    scopes: str = Form(default=",".join(connectors.DEFAULT_SCOPES)),
    ident=Depends(require_admin),
) -> dict:
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    try:
        conn, token = connectors.register(name=name, scopes=scope_list, created_by=ident.actor)
    except ValueError as e:
        raise HTTPException(400, str(e))
    storage.append_audit(
        action="connector:register",
        target=conn.id,
        actor_role=ident.role,
        before=None,
        after="active",
        extra={"name": conn.name, "scopes": conn.scopes, "by": ident.actor},
    )
    out = conn.public()
    out["token"] = token  # ONLY returned at creation
    return out


@router.get("/connectors")
def list_connectors(request: Request, ident=Depends(require_admin)) -> list[dict]:
    return [c.public() for c in connectors.list_connectors()]


@router.post("/connectors/{connector_id}/revoke")
def revoke_connector(connector_id: str, request: Request, ident=Depends(require_admin)) -> dict:
    c = connectors.revoke(connector_id)
    if c is None:
        raise HTTPException(404, f"connector {connector_id} not found")
    storage.append_audit(
        action="connector:revoke",
        target=c.id,
        actor_role=ident.role,
        before="active",
        after="revoked",
        extra={"name": c.name, "by": ident.actor},
    )
    return c.public()


@router.get("/connectors/me")
def connector_me(request: Request) -> dict:
    ident = identity(request)
    if ident.kind != "connector":
        raise HTTPException(401, "this endpoint requires a connector bearer token")
    return {
        "connector_id": ident.connector_id,
        "name": ident.actor.removeprefix("connector:"),
        "scopes": ident.scopes,
    }
