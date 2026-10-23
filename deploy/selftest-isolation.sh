#!/usr/bin/env bash
# Canary checks between two project users. Run as root on the Linux host.
# Usage: sudo deploy/selftest-isolation.sh proj-a proj-b
set -u

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if [ "$#" -ne 2 ] || [ "$1" = "$2" ]; then
  echo "usage: $0 <project-a> <project-b>" >&2
  exit 2
fi

A="$1"
B="$2"
FAILED=0
fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

if ! command -v runuser >/dev/null 2>&1; then
  echo "runuser not found; cannot test as another user" >&2
  exit 2
fi

if [ ! -f "/srv/$B/CANARY" ]; then
  fail "missing /srv/$B/CANARY"
elif runuser -u "$A" -- test -r "/srv/$B/CANARY" 2>/dev/null; then
  fail "$A can read $B CANARY"
else
  ok "$A cannot read $B CANARY"
fi

if runuser -u "$A" -- sudo -n true 2>/dev/null; then
  fail "$A has passwordless sudo"
else
  ok "$A has no sudo"
fi

if command -v ss >/dev/null 2>&1; then
  UID_A="$(id -u "$A")"
  PORTS="$(ss -ltnp 2>/dev/null | grep "uid:$UID_A" || true)"
  if printf '%s\n' "$PORTS" | grep -Eq '0\.0\.0\.0|\[::\]|\*:'; then
    fail "$A listens on a public port"
  else
    ok "$A has no public listening port"
  fi
else
  ok "ss not installed; port check skipped"
fi

if [ "$(stat -c '%U:%G %a' "/etc/git-hooks/$A" 2>/dev/null)" = "root:root 755" ]; then
  ok "hooks directory root:root 755"
else
  fail "hooks directory is not root:root 755"
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
