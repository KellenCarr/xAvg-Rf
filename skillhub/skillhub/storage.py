from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import tarfile
import time
from pathlib import Path
from typing import Iterable, Optional

import yaml

from skillhub.manifest import (
    McpEntry,
    SkillEntry,
    manifest_to_dict,
    parse_manifest,
)


def registry_root() -> Path:
    p = os.environ.get("SKILLHUB_REGISTRY")
    if p:
        return Path(p)
    return Path(__file__).resolve().parent.parent / "registry"


def index_path() -> Path:
    return registry_root() / "index.json"


def audit_path() -> Path:
    return registry_root() / "audit.log.jsonl"


def allowlist_path() -> Path:
    return registry_root() / ".allowlist.yaml"


def entry_dir(namespace: str, name: str) -> Path:
    return registry_root() / namespace / name


def manifest_file(namespace: str, name: str) -> Path:
    return entry_dir(namespace, name) / "manifest.yaml"


def payload_dir(namespace: str, name: str) -> Path:
    return entry_dir(namespace, name) / "payload"


def load_manifest(namespace: str, name: str):
    f = manifest_file(namespace, name)
    if not f.exists():
        raise FileNotFoundError(f"{namespace}/{name}")
    data = yaml.safe_load(f.read_text())
    return parse_manifest(data)


def write_manifest(m) -> Path:
    d = entry_dir(m.namespace, m.name)
    d.mkdir(parents=True, exist_ok=True)
    f = d / "manifest.yaml"
    f.write_text(yaml.safe_dump(manifest_to_dict(m), sort_keys=False))
    return f


def iter_entries() -> Iterable:
    root = registry_root()
    if not root.exists():
        return
    for ns_dir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        for name_dir in sorted(p for p in ns_dir.iterdir() if p.is_dir()):
            mf = name_dir / "manifest.yaml"
            if mf.exists():
                try:
                    yield load_manifest(ns_dir.name, name_dir.name)
                except Exception as e:
                    print(f"warn: bad manifest {ns_dir.name}/{name_dir.name}: {e}")


def rebuild_index() -> dict:
    entries = []
    for m in iter_entries():
        d = manifest_to_dict(m)
        entries.append(
            {
                "namespace": d["namespace"],
                "name": d["name"],
                "kind": d["kind"],
                "version": d["version"],
                "status": d["status"],
                "visibility": d["visibility"],
                "description": d["description"],
                "permissions": d["permissions"],
                "author": d["author"],
                "reviewer": d.get("reviewer"),
            }
        )
    out = {"generated_at": int(time.time()), "entries": entries}
    p = index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    return out


def read_index() -> dict:
    p = index_path()
    if not p.exists():
        return rebuild_index()
    return json.loads(p.read_text())


def append_audit(action: str, target: str, actor_role: str, before: Optional[str], after: Optional[str], extra: Optional[dict] = None) -> None:
    rec = {
        "ts": int(time.time()),
        "actor_role": actor_role,
        "action": action,
        "target": target,
        "before_status": before,
        "after_status": after,
    }
    if extra:
        rec.update(extra)
    p = audit_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def read_audit(limit: int = 200) -> list[dict]:
    p = audit_path()
    if not p.exists():
        return []
    lines = p.read_text().strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]


def load_allowlist() -> list[str]:
    p = allowlist_path()
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text()) or {}
    return list(data.get("allowed_namespaces", []))


def set_status(namespace: str, name: str, new_status: str, reviewer: Optional[str], actor_role: str) -> dict:
    m = load_manifest(namespace, name)
    before = m.status
    m.status = new_status  # type: ignore[assignment]
    if new_status in ("approved", "rejected"):
        m.reviewer = reviewer
    write_manifest(m)
    rebuild_index()
    append_audit(
        action=f"status:{new_status}",
        target=f"{namespace}/{name}",
        actor_role=actor_role,
        before=before,
        after=new_status,
        extra={"reviewer": reviewer},
    )
    return manifest_to_dict(m)


def make_payload_tar(namespace: str, name: str) -> bytes:
    pdir = payload_dir(namespace, name)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if pdir.exists():
            for f in sorted(pdir.rglob("*")):
                if f.is_file():
                    tar.add(f, arcname=str(f.relative_to(pdir)))
    return buf.getvalue()


def seed_from(seed_dir: Path) -> int:
    """Copy seed/<flat>/ into registry/<ns>/<name>/. Folder names use '--' as ns/name separator."""
    n = 0
    for child in sorted(seed_dir.iterdir()):
        if not child.is_dir():
            continue
        if "--" not in child.name:
            print(f"skip {child.name}: expected '<ns>--<name>' folder name")
            continue
        ns, nm = child.name.split("--", 1)
        dest = entry_dir(ns, nm)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(child, dest)
        n += 1
    rebuild_index()
    return n


def _cli() -> None:
    p = argparse.ArgumentParser(prog="skillhub.storage")
    p.add_argument("--seed", type=Path, help="seed directory to copy from")
    p.add_argument("--rebuild", action="store_true")
    args = p.parse_args()
    if args.seed:
        n = seed_from(args.seed)
        print(f"seeded {n} entries into {registry_root()}")
    elif args.rebuild:
        out = rebuild_index()
        print(f"index: {len(out['entries'])} entries")
    else:
        p.print_help()


if __name__ == "__main__":
    _cli()
