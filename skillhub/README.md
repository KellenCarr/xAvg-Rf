# SkillHub — Enterprise Agent Skill & Tool Registry (Prototype)

A centralized place where companies can publish, govern, and pull **skills** and
**tools** for AI agent harnesses (Claude Code, Cowork, etc.). Think
*Artifactory/JFrog for agent skills*: one catalog, two entry kinds, a stubbed
approval workflow, and a CLI that drops skills into real Claude Code project
layouts.

> **This is a prototype.** Auth, signatures, and approval pipelines are
> intentionally faked. See [What's faked](#whats-faked-vs-real) below.

## Quickstart

```bash
# from skillhub/
pip install -e .
make seed          # populate registry/ from seed/
make run           # uvicorn on :8765
```

Then:

- Browse the catalog: <http://localhost:8765/>
- Become admin: <http://localhost:8765/?role=admin> (or `skillhub login --role admin`)
- Submit a manifest: <http://localhost:8765/submit>
- Approve pending entries: <http://localhost:8765/admin?role=admin>

CLI demo (in another terminal):

```bash
skillhub login --role user
skillhub search reviewer
skillhub info acme/code-reviewer
skillhub add acme/code-reviewer --project ./sample-project --yes
skillhub add platform/filesystem-mcp --project ./sample-project --yes
ls sample-project/.claude/skills/code-reviewer/   # SKILL.md
cat sample-project/.mcp.json                       # mcpServers.filesystem
```

End-to-end check: `bash scripts/verify.sh` (runs against the running server).

## What's in the registry

| Entry | Kind | Status | Notes |
|---|---|---|---|
| `acme/code-reviewer` | skill | approved | reads files, runs git |
| `acme/jira-helper` | skill | approved | network + env perms (high-risk badge) |
| `platform/filesystem-mcp` | mcp_server | approved | the MCP filesystem server |
| `platform/github-mcp` | mcp_server | approved | the MCP GitHub server |
| `community/readme-writer` | skill | **pending** | drives the admin approval demo |

## Architecture

- **Backend**: FastAPI. Single process serves both `/api/*` JSON and `/` HTML.
- **Frontend**: Server-rendered Jinja2 + HTMX. No build step.
- **CLI**: Typer (`skillhub`).
- **Storage**: filesystem-backed under `registry/<namespace>/<name>/`. The
  generated `index.json` is the search/list backing store. Append-only
  `audit.log.jsonl` for governance events.

```
registry/
├── index.json                 # GENERATED, do not hand-edit
├── audit.log.jsonl            # append-only governance events
├── .allowlist.yaml            # allowed namespaces
└── <namespace>/<name>/
    ├── manifest.yaml          # the unit
    └── payload/               # SKILL.md + assets (skills only)
```

## Manifest schema

Shared fields:

```yaml
apiVersion: skillhub/v0
kind: skill | mcp_server
namespace: <str>
name: <str>
version: <semver>
description: <str>
author: <email>
status: pending | approved | rejected
reviewer: <email|null>
permissions: ["read_files", "run_shell:git", "network:host", "read_env:VAR", ...]
visibility: private | public
signature: "UNSIGNED-PROTOTYPE"
```

Skill-specific:

```yaml
skill:
  entrypoint: payload/SKILL.md
  install_path: .claude/skills/{name}/
```

MCP-specific:

```yaml
mcp_server:
  command: "npx"
  args: ["-y", "@modelcontextprotocol/server-filesystem", "${WORKSPACE}"]
  env: { WORKSPACE: "./" }
  mcp_json_key: "filesystem"
```

## CLI reference

```text
skillhub login --role user|admin [--registry-url URL]
skillhub whoami
skillhub search [QUERY] [--kind skill|mcp_server] [--namespace NS] [--status STATUS]
skillhub info <namespace>/<name>
skillhub add  <namespace>/<name> --project PATH [--yes] [--allow-unapproved]
skillhub submit <manifest.yaml> [--payload <file>]
skillhub approve <namespace>/<name>     # admin
skillhub reject  <namespace>/<name>     # admin
skillhub audit [--limit 50]             # admin
```

`add` is the load-bearing command. For `kind=skill` it downloads `payload/`
and untars into `<project>/.claude/skills/<name>/`. For `kind=mcp_server` it
merges into `<project>/.mcp.json` under `mcpServers[mcp_json_key]`. It
**refuses entries with `status != approved`** unless `--allow-unapproved`.

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | health |
| GET | `/api/whoami` | echo role |
| GET | `/api/entries` | list/search; `?q&kind&status&namespace&visibility` |
| GET | `/api/entries/{ns}/{name}` | full manifest |
| GET | `/api/entries/{ns}/{name}/payload` | tar.gz of `payload/` |
| POST | `/api/entries` | submit (force `pending`) |
| POST | `/api/entries/{ns}/{name}/approve` | admin |
| POST | `/api/entries/{ns}/{name}/reject` | admin |
| GET | `/api/audit` | tail audit log (admin) |

## Governance demo features

- **Namespaces**: `acme` (private), `platform` (private/shared), `community` (public).
- **Allowlist**: `registry/.allowlist.yaml`; submissions outside it 400.
- **Roles**: `user` default, `admin` via `?role=admin`, `X-Role` header, or cookie set by `/login`.
- **Audit log**: every state change appends to `registry/audit.log.jsonl`.
- **Permissions**: declared in the manifest; UI flags high-risk
  (`write_files`, `run_shell:*`, `network:*`); CLI prompts before install.

## What's faked vs real

**Real**:

- Manifest schema & validation (Pydantic discriminated union).
- Filesystem registry, regenerated index, append-only audit log.
- CLI install behavior matches Claude Code conventions:
  `.claude/skills/<name>/SKILL.md` for skills, `.mcp.json` `mcpServers` shape
  for MCP entries.
- End-to-end submit → approve → install loop.
- Search/filter on name, description, kind, status, namespace, visibility.

**Faked** (do not deploy as-is):

- **Auth**: `?role=admin`, `X-Role` header, or a cookie. Trivially bypassable.
- **Signatures**: the `signature` field is the literal string `UNSIGNED-PROTOTYPE`. No crypto.
- **Permission enforcement**: declared and *displayed*, not enforced at runtime.
- **Approval pipeline**: a button. No reviewer pools, required approvers, or SLAs.
- **Versioning**: only the latest version is stored. No history, no semver resolution.
- **Search**: substring match on name + description.
- **Visibility**: `private`/`public` is a label, not access-controlled.
- **Multi-tenant**: one tenant. "Organization" = namespace prefix.
- **MCP server health**: we never start or test the MCP servers we configure.

## Where to take this next

- Real auth (OIDC/SAML) + per-namespace ACLs.
- Detached-signature verification on submit (cosign / sigstore).
- Pluggable storage (filesystem → git → object store → Postgres) by swapping
  `skillhub/storage.py`.
- Manifest linter as CI on submission PRs (when migrating from in-app
  submission to a GitOps flow).
- Pre-publish skill testing harness (run skill against a fixture transcript).

## Layout

```
skillhub/
├── skillhub/                  # python package
│   ├── manifest.py            # Pydantic models
│   ├── storage.py             # FS registry + index + audit
│   ├── governance.py          # role, allowlist, perms
│   ├── api/
│   │   ├── main.py            # FastAPI app
│   │   ├── routes_registry.py # /api/*
│   │   └── routes_web.py      # / (Jinja+HTMX)
│   ├── templates/             # Jinja2
│   ├── static/style.css       # ~80 lines
│   └── cli/main.py            # Typer
├── registry/                  # the catalog (git-tracked, IS the database)
├── seed/                      # source manifests for `make seed`
├── sample-project/            # fake Claude Code project to install into
└── scripts/verify.sh          # end-to-end smoke test
```
