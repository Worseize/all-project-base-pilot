#!/usr/bin/env bash
# Full isolation acceptance on a disposable Ubuntu runner.
# Run as root: sudo --preserve-env=PATH bash deploy/ci/isolation.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
A="proj-a"
B="proj-b"
S="proj-s"
WORK="/srv/$A/work"
FAILED=0
TMP_KEY="$(mktemp -d)"
CI_LOG_DIR="$ROOT/ci-logs"
mkdir -p "$CI_LOG_DIR"

fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

cleanup() {
  rm -rf "$TMP_KEY"
  bash "$SCRIPT_DIR/isolation-cleanup.sh" "$A" "$B" "$S" >/dev/null 2>&1 || true
}

on_exit() {
  mkdir -p "$CI_LOG_DIR"
  cp -a /var/log/git/*.log "$CI_LOG_DIR/" 2>/dev/null || true
  chmod 0644 "$CI_LOG_DIR"/*.log 2>/dev/null || true
  {
    echo "== diagnostics"
    echo "shallow=$(git -C "$ROOT" rev-parse --is-shallow-repository 2>/dev/null || echo unknown)"
    stat -c '%a %U:%G %n' /var/log/git /var/log/git/*.log 2>/dev/null || true
    getent passwd "$A" 2>/dev/null || true
    [ -d /run/systemd/system ] && echo "systemd=yes" || echo "systemd=no"
  } > "$CI_LOG_DIR/diagnostics.txt" 2>&1
  cleanup
}
trap on_exit EXIT

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

echo "== step: checks"
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
runuser -u "$A" -- bash -c "id; stat -c '%U:%G %a %n' /var/log/git /var/log/git/$A.log" 2>/dev/null || true

if ! runuser -u "$A" -- bash -c "cd '$WORK' && mkdir -p app && printf 'proof\\n' > app/ci-proof.txt && git add app/ci-proof.txt && git commit -m 'ci proof'" >/dev/null 2>&1; then
  fail "normal commit"
  exit 1
fi

echo "== step: review"
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
  fail "per-project logrotate rule duplicates host baseline"
else
  ok "no per-project logrotate duplicate"
fi
if [ "$(git -c safe.directory="$REPO" --git-dir="$REPO" config core.hooksPath 2>/dev/null)" = "/etc/git-hooks/$A" ]; then
  ok "core.hooksPath outside repo"
else
  fail "core.hooksPath is wrong"
fi
if [ -f "/etc/git-hooks/$A/post-receive" ]; then
  ok "post-receive installed"
else
  fail "post-receive missing"
fi

tmp_reg="$(mktemp)"
cat > "$tmp_reg" <<EOF
{"projects":{"$A":{"display":"A","agent":"a","domain":"","port":0,"status":"active","allowed_paths":["app/"]}}}
EOF
if bash "$ROOT/deploy/auto-merge.sh" "$tmp_reg" >/dev/null 2>&1 &&
  [ -f "/srv/$A/current/app/ci-proof.txt" ]; then
  ok "auto-merge delivered main"
else
  fail "auto-merge did not deliver main"
fi
main_after="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/main)"
bash "$ROOT/deploy/auto-merge.sh" "$tmp_reg" >/dev/null 2>&1 || true
if [ "$main_after" = "$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/main)" ]; then
  ok "auto-merge idempotent"
else
  fail "auto-merge changed main on repeat"
fi
review_sha="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/review)"
if [ "$review_sha" = "$main_after" ]; then
  ok "review aligned to main"
else
  fail "review not aligned: review=$review_sha main=$main_after"
fi
runuser -u "$A" -- git -C "$WORK" fetch -q origin
runuser -u "$A" -- git -C "$WORK" checkout -q -B work origin/review
runuser -u "$A" -- bash -c "cd '$WORK' && printf 'second\\n' > app/ci-proof2.txt && git add app/ci-proof2.txt && git commit -m second" >/dev/null 2>&1
{
  echo "local HEAD: $(git -C "$WORK" rev-parse HEAD)"
  echo "local origin/review: $(git -C "$WORK" rev-parse origin/review)"
  echo "remote main: $(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/main)"
  echo "remote review: $(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse refs/heads/review)"
  git -C "$WORK" log --oneline -6
} >"$CI_LOG_DIR/second-push-state.txt" 2>&1
if runuser -u "$A" -- git -C "$WORK" push origin HEAD:review >"$CI_LOG_DIR/second-push.log" 2>&1; then
  ok "second push after auto-merge accepted"
else
  cat "$CI_LOG_DIR/second-push.log" >&2
  fail "second push after auto-merge rejected (review not aligned)"
fi
rm -f "$tmp_reg"

echo "== step: skeleton project"
if ! bash "$ROOT/deploy/init-project.sh" "$S" >/dev/null 2>&1; then
  fail "skeleton init $S"
else
  SREPO="/srv/$S/repo.git"
  if git -c safe.directory="$SREPO" --git-dir="$SREPO" cat-file -e refs/heads/main:verify.py 2>/dev/null; then
    fail "skeleton main contains verify.py"
  else
    ok "skeleton main has no verify.py"
  fi
  SWORK="/srv/$S/work"
  if runuser -u "$S" -- git clone "$SREPO" "$SWORK" >/dev/null 2>&1; then
    runuser -u "$S" -- git -C "$SWORK" config user.email "$S@agents.invalid"
    runuser -u "$S" -- git -C "$SWORK" config user.name "$S"
    runuser -u "$S" -- bash -c "cd '$SWORK' && printf 'skeleton\\n' > note.txt && git add note.txt && git commit -m skeleton" >/dev/null 2>&1
    if runuser -u "$S" -- git -C "$SWORK" push origin HEAD:review >/dev/null 2>&1; then
      ok "skeleton review accepted via test.sh from main"
    else
      fail "skeleton review rejected"
    fi
    runuser -u "$S" -- bash -c "cd '$SWORK' && chmod -x run && git add run && git commit -m noexec" >/dev/null 2>&1
    expect_reject "non-exec run" "run mode" \
      runuser -u "$S" -- git -C "$SWORK" push origin HEAD:review
  else
    fail "skeleton clone"
  fi
fi

echo "== step: health watchdog"
HREG="$(mktemp)"
cat > "$HREG" <<EOF
{"projects":{"$A":{"display":"A","agent":"a","domain":"","port":0,"status":"active","allowed_paths":["*"]}}}
EOF
HSTATE="$CI_LOG_DIR/health-state.json"
HNOTIFY="$CI_LOG_DIR/health-notify.sh"
HNOTIFY_LOG="$CI_LOG_DIR/health-notify.log"
HLOG="$CI_LOG_DIR/health-check.log"
cat > "$HNOTIFY" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "$WATCHDOG_NOTIFY_LOG"
EOF
chmod +x "$HNOTIFY"
rm -f "$HSTATE" "$HNOTIFY_LOG" "$HLOG"

set_health() {
  printf '#!/usr/bin/env bash\necho "%s"\nexit %s\n' "$2" "$1" > "/srv/$A/current/health"
  chown "$A:$A" "/srv/$A/current/health"
  chmod 0755 "/srv/$A/current/health"
}

health_run() {
  WATCHDOG_STATE_FILE="$HSTATE" WATCHDOG_LOG="$HLOG" \
    WATCHDOG_NOTIFY_CMD="$HNOTIFY" WATCHDOG_NOTIFY_LOG="$HNOTIFY_LOG" \
    WATCHDOG_TIMEOUT="${1:-30}" WATCHDOG_REPEAT_SECONDS=3600 \
    bash "$ROOT/deploy/health-check.sh" "$HREG" >/dev/null 2>&1
}

set_health 0 ok
health_run
if [ ! -s "$HNOTIFY_LOG" ]; then
  ok "health=0 silent"
else
  fail "health=0 produced messages"
fi

set_health 1 "model down"
rm -f "$HSTATE" "$HNOTIFY_LOG"
health_run
if [ "$(grep -c . "$HNOTIFY_LOG" 2>/dev/null || true)" -eq 1 ] && grep -q "model down" "$HNOTIFY_LOG"; then
  ok "health=1 one alert with reason"
else
  fail "health=1 alert wrong"
fi
health_run
if [ "$(grep -c . "$HNOTIFY_LOG" 2>/dev/null || true)" -eq 1 ]; then
  ok "repeat suppressed"
else
  fail "repeat was not suppressed"
fi

rm -f "/srv/$A/current/health" "$HSTATE" "$HNOTIFY_LOG"
health_run
if [ "$(grep -c . "$HNOTIFY_LOG" 2>/dev/null || true)" -eq 1 ] && grep -q "health missing" "$HNOTIFY_LOG"; then
  ok "missing health is config alert"
else
  fail "missing health not reported"
fi

set_health 0 "slow"
printf '#!/usr/bin/env bash\nsleep 5\n' > "/srv/$A/current/health"
chown "$A:$A" "/srv/$A/current/health"
chmod 0755 "/srv/$A/current/health"
rm -f "$HSTATE" "$HNOTIFY_LOG"
start="$(date +%s)"
health_run 1
elapsed=$(( $(date +%s) - start ))
if [ "$elapsed" -lt 10 ] && grep -q "timeout 1s" "$HNOTIFY_LOG"; then
  ok "timeout is sick and bounded"
else
  fail "timeout not handled (${elapsed}s)"
fi

set_health 1 "down"
rm -f "$HSTATE" "$HNOTIFY_LOG"
health_run
set_health 0 "ok"
health_run
if grep -q "восстановлен" "$HNOTIFY_LOG"; then
  ok "recovery message"
else
  fail "recovery message missing"
fi
rm -f "$HREG" "/srv/$A/current/health"

echo "== step: project.conf manifest"
if ! bash "$ROOT/deploy/ci/manifest.sh"; then
  fail "manifest scenarios"
fi

echo "== step: data snapshots and rollback"
if ! bash "$ROOT/deploy/ci/data.sh"; then
  fail "data scenarios"
fi

if [ "$FAILED" -ne 0 ]; then
  echo "ISOLATION CI: RED" >&2
  exit 1
fi
echo "ISOLATION CI: GREEN"
