#!/usr/bin/env bash
# Canary checks for one or two project users. Run as root on the Linux host.
# Usage: sudo deploy/selftest-isolation.sh proj-a [proj-b]
set -u

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 <project-a> [project-b]" >&2
  exit 2
fi

A="$1"
B="${2:-}"
if [ -n "$B" ] && [ "$A" = "$B" ]; then
  echo "project-a and project-b must differ" >&2
  exit 2
fi
FAILED=0
fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

REGISTRY="${REGISTRY:-projects.json}"
if [ ! -f "$REGISTRY" ]; then
  echo "registry not found: $REGISTRY" >&2
  exit 2
fi
python3 - "$REGISTRY" "$A" "$B" <<'PY'
import json
import sys
registry, first, second = sys.argv[1:4]
with open(registry, encoding="utf-8") as handle:
    projects = json.load(handle).get("projects", {})
for name in filter(None, (first, second)):
    if name not in projects:
        raise SystemExit(f"project not in registry: {name}")
PY

if ! command -v runuser >/dev/null 2>&1; then
  echo "runuser not found; cannot test as another user" >&2
  exit 2
fi

if [ ! -f "/srv/$A/CANARY" ]; then
  fail "missing /srv/$A/CANARY"
elif runuser -u "$A" -- test -r "/srv/$A/CANARY" 2>/dev/null; then
  ok "$A can read own CANARY"
else
  fail "$A cannot read own CANARY"
fi

if [ -n "$B" ]; then
  if [ ! -f "/srv/$B/CANARY" ]; then
    fail "missing /srv/$B/CANARY"
  elif runuser -u "$A" -- test -r "/srv/$B/CANARY" 2>/dev/null; then
    fail "$A can read $B CANARY"
  else
    ok "$A cannot read $B CANARY"
  fi
fi

if runuser -u "$A" -- sudo -n true 2>/dev/null; then
  fail "$A has passwordless sudo"
else
  ok "$A has no sudo"
fi

if command -v ss >/dev/null 2>&1 && command -v pgrep >/dev/null 2>&1; then
  for pid in $(pgrep -u "$A" 2>/dev/null || true); do
    if ss -ltnp 2>/dev/null | grep -q "pid=$pid,"; then
      fail "$A listens on a socket (pid $pid)"
    fi
  done
  ok "$A has no listening socket"
else
  ok "ss/pgrep not installed; port check skipped"
fi

if [ "$(stat -c '%U:%G %a' "/etc/git-hooks/$A" 2>/dev/null)" = "root:root 755" ]; then
  ok "hooks directory root:root 755"
else
  fail "hooks directory is not root:root 755"
fi

LOG="/var/log/git/$A.log"
if [ -f "$LOG" ] && [ "$(stat -c '%U:%G %a' "$LOG" 2>/dev/null)" = "root:$A 660" ]; then
  ok "acceptance log root:$A 660"
else
  fail "acceptance log missing or wrong mode (root:$A 660)"
fi

if getent passwd "$A" | grep -q 'nologin$\|git-shell$'; then
  ok "$A has no interactive shell"
else
  fail "$A still has an interactive shell"
fi

REPO="/srv/$A/repo.git"
if [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" config core.hooksPath 2>/dev/null)" = "/etc/git-hooks/$A" ]; then
  ok "core.hooksPath is outside repo"
else
  fail "core.hooksPath is not /etc/git-hooks/$A"
fi
if [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" config receive.denyDeletes 2>/dev/null)" = "true" ] &&
   [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" config receive.denyNonFastForwards 2>/dev/null)" = "true" ]; then
  ok "delete and force push denied"
else
  fail "receive.denyDeletes/denyNonFastForwards not true"
fi
if git -c safe.directory="$REPO" --git-dir="$REPO" show-ref --verify --quiet refs/heads/main; then
  ok "main is seeded"
else
  fail "main is missing; bootstrap must seed it"
fi

if [ -f /etc/systemd/system/proj@.service ]; then
  ok "systemd template installed"
else
  fail "systemd template missing"
fi

if [ "$FAILED" -ne 0 ]; then
  echo "ISOLATION: RED" >&2
  exit 1
fi
echo "ISOLATION: GREEN"
