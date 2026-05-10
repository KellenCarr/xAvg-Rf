from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from skillhub import storage
from skillhub.governance import NAMESPACES, check_namespace_allowed, identity
from skillhub.manifest import has_high_risk, manifest_to_dict, parse_manifest

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
TEMPLATES.env.globals["NAMESPACES"] = NAMESPACES

router = APIRouter()


def _ctx(request: Request, **kw):
    ident = identity(request)
    base = {
        "role": ident.role,
        "actor": ident.actor,
        "namespaces": NAMESPACES,
    }
    base.update(kw)
    return base


def _render(request: Request, template: str, status_code: int = 200, **ctx):
    return TEMPLATES.TemplateResponse(request, template, _ctx(request, **ctx), status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def catalog(
    request: Request,
    q: Optional[str] = None,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    namespace: Optional[str] = None,
    visibility: Optional[str] = None,
    partial: int = 0,
):
    idx = storage.read_index()
    entries = idx["entries"]
    if q:
        ql = q.lower()
        entries = [e for e in entries if ql in e["name"].lower() or ql in e["description"].lower()]
    if kind:
        entries = [e for e in entries if e["kind"] == kind]
    if status:
        entries = [e for e in entries if e["status"] == status]
    if namespace:
        entries = [e for e in entries if e["namespace"] == namespace]
    if visibility:
        entries = [e for e in entries if e["visibility"] == visibility]
    for e in entries:
        e["high_risk"] = has_high_risk(e.get("permissions", []))
    template = "_catalog_table.html" if partial else "catalog.html"
    return _render(
        request,
        template,
        entries=entries,
        filters={
            "q": q or "",
            "kind": kind or "",
            "status": status or "",
            "namespace": namespace or "",
            "visibility": visibility or "",
        },
    )


@router.get("/entries/{namespace}/{name}", response_class=HTMLResponse)
def detail(request: Request, namespace: str, name: str):
    try:
        m = storage.load_manifest(namespace, name)
    except FileNotFoundError:
        raise HTTPException(404, f"{namespace}/{name} not found")
    d = manifest_to_dict(m)
    audit_all = storage.read_audit(limit=500)
    related = [a for a in audit_all if a.get("target") == f"{namespace}/{name}"]
    install_cmd = (
        f"skillhub add {namespace}/{name} --project ./sample-project"
    )
    return _render(
        request,
        "detail.html",
        entry=d,
        high_risk=has_high_risk(d.get("permissions", [])),
        audit=list(reversed(related)),
        install_cmd=install_cmd,
    )


@router.get("/submit", response_class=HTMLResponse)
def submit_form(request: Request):
    return _render(request, "submit.html", error=None, prefill="")


@router.post("/submit", response_class=HTMLResponse)
def submit_post(request: Request, manifest_yaml: str = Form(...)):
    ident = identity(request)
    try:
        data = yaml.safe_load(manifest_yaml)
        m = parse_manifest(data)
        check_namespace_allowed(m.namespace)
    except HTTPException as he:
        return _render(request, "submit.html", status_code=400, error=he.detail, prefill=manifest_yaml)
    except Exception as e:
        return _render(request, "submit.html", status_code=400, error=str(e), prefill=manifest_yaml)
    m.status = "pending"
    m.reviewer = None
    storage.write_manifest(m)
    storage.rebuild_index()
    storage.append_audit(
        action="submit",
        target=f"{m.namespace}/{m.name}",
        actor_role=ident.role,
        before=None,
        after="pending",
        extra={"version": m.version, "via": "web"},
    )
    return RedirectResponse(url=f"/entries/{m.namespace}/{m.name}", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    ident = identity(request)
    if ident.role != "admin":
        return _render(request, "admin.html", status_code=403, denied=True, pending=[], audit=[])
    idx = storage.read_index()
    pending = [e for e in idx["entries"] if e["status"] == "pending"]
    audit = list(reversed(storage.read_audit(limit=50)))
    return _render(request, "admin.html", denied=False, pending=pending, audit=audit)


@router.post("/admin/{namespace}/{name}/{action}", response_class=HTMLResponse)
def admin_action(request: Request, namespace: str, name: str, action: str):
    ident = identity(request)
    if ident.role != "admin":
        raise HTTPException(403, "admin required (stub)")
    if action not in ("approve", "reject"):
        raise HTTPException(400, "unknown action")
    new_status = "approved" if action == "approve" else "rejected"
    storage.set_status(namespace, name, new_status, reviewer=ident.actor, actor_role=ident.role)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return _render(request, "login.html")


@router.post("/login", response_class=HTMLResponse)
def login_post(request: Request, role: str = Form(...)):
    role = "admin" if role.lower() == "admin" else "user"
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie("skillhub_role", role, httponly=False, samesite="lax")
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("skillhub_role")
    return resp
