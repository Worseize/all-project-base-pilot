#!/usr/bin/env bash
# Full isolation acceptance on a disposable Ubuntu runner.
# Run as root: sudo --preserve-env=PATH bash deploy/ci/isolation.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
A="proj-a"
B="proj-b"
WORK="/srv/$A/work"
FAILED=0
TMP_KEY="$(mktemp -d)"

fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

cleanup() {
  rm -rf "$TMP_KEY"
  bash "$SCRIPT_DIR/isolation-cleanup.sh" "$A" "$B" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if ! command -v ssh-keygen >/dev/null 2>&1; then
  echo "ssh-keygen is required" >&2
  exit 2
fi

ssh-keygen -q -t ed25519 -N '' -f "$TMP_KEY/agent"
PUBKEY="$(cat "$TMP_KEY/agent.pub")"

for PROJECT in "$A" "$B"; do
  if ! AGENT_PUBKEY="$PUBKEY" SOURCE_REPO="$ROOT" SOURCE_REF=HEAD \
    bash "$ROOT/deploy/bootstrap-project.sh" "$PROJECT"; then
    fail "bootstrap $PROJECT"
    exit 1
  fi
done
ok "bootstrap: $A, $B"

EXPECTED_SHELL="$(command -v git-shell)"
for PROJECT in "$A" "$B"; do
  actual="$(getent passwd "$PROJECT" | awk -F: '{print $7}')"
  [ "$actual" = "$EXPECTED_SHELL" ] && ok "$PROJECT uses git-shell" ||
    fail "$PROJECT shell is $actual, not git-shell"
done

REPO="/srv/$A/repo.git"
git -c safe.directory="$REPO" --git-dir="$REPO" show-ref --verify --quiet refs/heads/main &&
  ok "main seeded" || fail "main missing"

if ! runuser -u "$A" -- git clone "$REPO" "$WORK" >/dev/null 2>&1; then
  fail "clone as $A"
  exit 1
fi
runuser -u "$A" -- git -C "$WORK" config user.email "$A@agents.invalid"
runuser -u "$A" -- git -C "$WORK" config user.name "$A"

if ! runuser -u "$A" -- bash -c "cd '$WORK' && printf 'proof\\n' > ci-proof.txt && git add ci-proof.txt && git commit -m 'ci proof'" >/dev/null 2>&1; then
  fail "normal commit"
  exit 1
fi

if ! out="$(runuser -u "$A" -- git -C "$WORK" push origin HEAD:review 2>&1)"; then
  fail "review push: $out"
else
  printf '%s\n' "$out" | grep -q "review accepted" && ok "review accepted" ||
    fail "review push without accepted marker"
fi

expect_reject() {
  local desc="$1" needle="$2" out
  shift 2
  if out="$("$@" 2>&1)"; then
    fail "$desc accepted"
  elif printf '%s\n' "$out" | grep -q "$needle"; then
    ok "$desc rejected"
  else
    fail "$desc rejected without '$needle': $out"
  fi
}

runuser -u "$A" -- git -C "$WORK" checkout -B gate >/dev/null 2>&1
runuser -u "$A" -- bash -c "cd '$WORK' && printf '\\n# weakened\\n' >> verify.py && git add verify.py && git commit -m weaken" >/dev/null 2>&1
expect_reject "verify.py change" "gate files changed" \
  runuser -u "$A" -- git -C "$WORK" push origin HEAD:review

base="$(runuser -u "$A" -- git -C "$WORK" rev-parse HEAD~2)"
runuser -u "$A" -- git -C "$WORK" checkout -B force "$base" >/dev/null 2>&1
runuser -u "$A" -- bash -c "cd '$WORK' && printf 'force\\n' >> ci-proof.txt && git add ci-proof.txt && git commit -m force" >/dev/null 2>&1
expect_reject "force push" "force push" \
  runuser -u "$A" -- git -C "$WORK" push --force origin HEAD:review

expect_reject "delete review" "deleting review" \
  runuser -u "$A" -- git -C "$WORK" push origin --delete review

if runuser -u "$A" -- test -r "/srv/$B/CANARY" 2>/dev/null; then
  fail "$A can read $B CANARY"
else
  ok "$A cannot read $B CANARY"
fi

if runuser -u "$A" -- sudo -n true 2>/dev/null; then
  fail "$A has passwordless sudo"
else
  ok "$A has no sudo"
fi

LOG="/var/log/git/$A.log"
if [ -s "$LOG" ]; then
  ok "acceptance log written"
else
  fail "acceptance log is empty"
fi
if [ -f "/etc/logrotate.d/proj-$A" ]; then
  ok "logrotate rule installed"
else
  fail "logrotate rule missing"
fi
if [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" config core.hooksPath 2>/dev/null)" = "/etc/git-hooks/$A" ]; then
  ok "core.hooksPath outside repo"
else
  fail "core.hooksPath is wrong"
fi

if [ "$FAILED" -ne 0 ]; then
  echo "ISOLATION CI: RED" >&2
  exit 1
fi
echo "ISOLATION CI: GREEN"
