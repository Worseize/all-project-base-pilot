#!/usr/bin/env bash
# Six data/snapshot/rollback scenarios on fixtures.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAILED=0
fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

# 1-2: tracked data is rejected; ignored data is accepted.
TMP="$(mktemp -d)"
git -C "$TMP" init -q
git -C "$TMP" config user.email ci@example.invalid
git -C "$TMP" config user.name ci
mkdir -p "$TMP/data"
printf 'state\n' > "$TMP/data/state.json"
git -C "$TMP" add data/state.json
if bash "$ROOT/deploy/data-guard.sh" "$TMP" >/dev/null 2>&1; then
  fail "tracked data accepted"
else
  ok "tracked data rejected"
fi
rm -rf "$TMP"
TMP="$(mktemp -d)"
git -C "$TMP" init -q
git -C "$TMP" config user.email ci@example.invalid
git -C "$TMP" config user.name ci
printf 'data/\n.env*\n*.log\n' > "$TMP/.gitignore"
mkdir -p "$TMP/data"
printf 'state\n' > "$TMP/data/state.json"
if bash "$ROOT/deploy/data-guard.sh" "$TMP" >/dev/null 2>&1; then
  ok "ignored data accepted"
else
  fail "ignored data rejected"
fi
rm -rf "$TMP"

# 3-5: snapshot create, verify, corrupt.
SD="$(mktemp -d)"
DATA="$(mktemp -d)"
printf 'value\n' > "$DATA/state.json"
if SNAPSHOT_DATA_DIR="$DATA" SNAPSHOT_DIR="$SD" bash "$ROOT/deploy/snapshot.sh" ci >/dev/null; then
  ok "snapshot created"
else
  fail "snapshot create failed"
fi
if SNAPSHOT_DATA_DIR="$DATA" SNAPSHOT_DIR="$SD" bash "$ROOT/deploy/snapshot.sh" ci --verify >/dev/null 2>&1; then
  ok "snapshot verified"
else
  fail "snapshot verify failed"
fi
latest="$(find "$SD" -name '*.tar.gz' | head -n 1)"
printf 'corrupt\n' >> "$latest"
if SNAPSHOT_DATA_DIR="$DATA" SNAPSHOT_DIR="$SD" bash "$ROOT/deploy/snapshot.sh" ci --verify >/dev/null 2>&1; then
  fail "corrupt snapshot accepted"
else
  ok "corrupt snapshot rejected"
fi
rm -rf "$SD" "$DATA"

# 6: code rollback to saved sha.
A="proj-a"
REPO="/srv/$A/repo.git"
BASE="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/main)"
REVIEW="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/review)"
install -d -m 0750 /var/lib/proj-base/deploy
printf '%s\n' "$BASE" > "/var/lib/proj-base/deploy/$A.sha"
git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/main "$REVIEW"
if bash "$ROOT/deploy/rollback.sh" "$A" >/dev/null 2>&1 &&
  [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/main)" = "$BASE" ]; then
  ok "code rollback to saved sha"
else
  fail "code rollback failed"
fi

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
