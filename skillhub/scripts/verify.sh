#!/usr/bin/env bash
# End-to-end verification script for the SkillHub prototype.
# Assumes the API is running on http://localhost:${PORT:-8765}.
set -euo pipefail

PORT="${PORT:-8765}"
BASE="http://localhost:${PORT}"
PROJ="$(cd "$(dirname "$0")/.." && pwd)/sample-project"

ok()   { printf "  \033[32mOK\033[0m  %s\n" "$1"; }
fail() { printf "  \033[31mFAIL\033[0m %s\n" "$1"; exit 1; }

assert_eq() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$expected" == "$actual" ]]; then ok "$label (=$actual)"; else fail "$label expected=$expected actual=$actual"; fi
}

echo "== 1. health =="
out=$(curl -s "$BASE/api/health")
assert_eq '{"ok":true}' "$out" "health"

echo "== 2. entries count == 5 =="
n=$(curl -s "$BASE/api/entries" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
assert_eq "5" "$n" "entries length"

echo "== 3. entries kind=mcp_server == 2 =="
n=$(curl -s "$BASE/api/entries?kind=mcp_server" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
assert_eq "2" "$n" "mcp_server entries"

echo "== 4. entries status=pending == 1 =="
n=$(curl -s "$BASE/api/entries?status=pending" | python -c 'import json,sys; print(len(json.load(sys.stdin)))')
assert_eq "1" "$n" "pending entries"

echo "== 5. CLI install: skill =="
rm -rf "$PROJ/.claude/skills/code-reviewer"
skillhub login --role user --registry-url "$BASE" >/dev/null
skillhub add acme/code-reviewer --project "$PROJ" --yes >/dev/null
test -f "$PROJ/.claude/skills/code-reviewer/SKILL.md" || fail "skill not installed"
ok "skill installed at $PROJ/.claude/skills/code-reviewer/SKILL.md"

echo "== 6. CLI install: mcp =="
echo '{"mcpServers": {}}' > "$PROJ/.mcp.json"
skillhub add platform/filesystem-mcp --project "$PROJ" --yes >/dev/null
python - <<EOF
import json, sys
d = json.load(open("$PROJ/.mcp.json"))
assert "filesystem" in d["mcpServers"], d
assert d["mcpServers"]["filesystem"]["command"] == "npx"
EOF
ok ".mcp.json contains filesystem entry"

echo "== 7. CLI refuses pending entry =="
set +e
out=$(skillhub add community/readme-writer --project "$PROJ" --yes 2>&1)
rc=$?
set -e
[[ $rc -ne 0 ]] || fail "expected non-zero exit when installing pending entry"
echo "$out" | grep -q "status=" || fail "expected refusal message"
ok "CLI refused pending entry"

echo "== 8. admin approve flow =="
skillhub login --role admin --registry-url "$BASE" >/dev/null
skillhub approve community/readme-writer >/dev/null
got=$(curl -s "$BASE/api/entries/community/readme-writer" | python -c 'import json,sys; print(json.load(sys.stdin)["status"])')
assert_eq "approved" "$got" "post-approve status"

echo "== 9. audit log has approve entry =="
last=$(tail -1 "$(cd "$(dirname "$0")/.." && pwd)/registry/audit.log.jsonl")
echo "$last" | python -c 'import json,sys; d=json.loads(sys.stdin.read()); assert d["action"]=="status:approved" and d["target"]=="community/readme-writer", d'
ok "audit log captured approval"

echo "== 10. allowlist rejects evil namespace =="
tmp=$(mktemp /tmp/skillhub-bad.XXXX.yaml)
cat > "$tmp" <<EOF
apiVersion: skillhub/v0
kind: skill
namespace: evil
name: foo
version: 0.0.1
description: "should be rejected"
author: "x@x"
permissions: []
visibility: public
EOF
set +e
out=$(skillhub submit "$tmp" 2>&1)
rc=$?
set -e
[[ $rc -ne 0 ]] || fail "expected allowlist rejection"
echo "$out" | grep -qi allowlist || fail "expected 'allowlist' in error"
rm -f "$tmp"
ok "allowlist rejected evil namespace"

# Reset readme-writer back to pending so re-running verify is idempotent
SKILLHUB_REGISTRY="$(cd "$(dirname "$0")/.." && pwd)/registry"
export SKILLHUB_REGISTRY
SKILLHUB_REGISTRY="$SKILLHUB_REGISTRY" python - <<EOF
import os, yaml
from pathlib import Path
root = Path(os.environ["SKILLHUB_REGISTRY"])
mf = root / "community" / "readme-writer" / "manifest.yaml"
d = yaml.safe_load(mf.read_text())
d["status"] = "pending"
d["reviewer"] = None
mf.write_text(yaml.safe_dump(d, sort_keys=False))
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "skillhub.storage", "--rebuild"])
EOF

echo
echo "All checks passed."
