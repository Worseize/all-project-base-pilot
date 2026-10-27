#!/usr/bin/env bash
# Manifest scenarios on a fixture project built from the skeleton.
# The gate must read run/test/health from project.conf, not hardcoded names.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
A="proj-m"
REPO="/srv/$A/repo.git"
WORK="/srv/$A/current"
FAILED=0
OUT="$(mktemp)"

fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

git_r() { git -c safe.directory="$REPO" --git-dir="$REPO" "$@"; }

write_entry() {
  local name="$1"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$WORK/$name"
  chown "$A:$A" "$WORK/$name"
  chmod 0755 "$WORK/$name"
}

write_sleeper() {
  local name="$1"
  printf '#!/usr/bin/env python3\nimport time\ntime.sleep(300)\n' > "$WORK/$name"
  chown "$A:$A" "$WORK/$name"
  chmod 0755 "$WORK/$name"
}

stage_manifest() {
  printf '%b\n' "$1" > "$WORK/project.conf"
  chown "$A:$A" "$WORK/project.conf"
  local paths=(project.conf)
  shift
  [ "$#" -eq 0 ] || paths+=("$@")
  runuser -u "$A" -- git -C "$WORK" add -A -- "${paths[@]}"
  runuser -u "$A" -- git -C "$WORK" commit -qm "manifest fixture" || true
}

push_review() {
  runuser -u "$A" -- git -C "$WORK" push -q origin HEAD:review
}

accept_manifest() {
  stage_manifest "$@"
  push_review || return 1
  local sha
  sha="$(runuser -u "$A" -- git -C "$WORK" rev-parse HEAD)"
  git_r update-ref refs/heads/main "$sha"
}

reject_manifest() {
  local needle="$1" out
  shift
  stage_manifest "$@"
  if out="$(push_review 2>&1)"; then
    fail "push accepted, expected rejection: $needle"
    return 1
  fi
  if printf '%s\n' "$out" | grep -q "$needle"; then
    return 0
  fi
  printf '%s\n' "$out" >&2
  fail "rejection without '$needle'"
  return 1
}

deploy() {
  bash "$ROOT/deploy/deploy-project.sh" "$A" >"$OUT" 2>&1
}

expect_deploy_ok() {
  local name="$1"
  if deploy; then ok "$name"; else cat "$OUT" >&2; fail "$name"; fi
}

if [ ! -d "$REPO" ]; then
  if ! bash "$ROOT/deploy/init-project.sh" "$A" >/dev/null 2>&1; then
    echo "FAIL: fixture project $A" >&2
    exit 1
  fi
fi
if [ ! -d "$WORK/.git" ]; then
  runuser -u "$A" -- git clone "$REPO" "$WORK" >/dev/null || {
    echo "FAIL: clone $A" >&2
    exit 1
  }
fi
runuser -u "$A" -- git -C "$WORK" config user.email "$A@agents.invalid"
runuser -u "$A" -- git -C "$WORK" config user.name "$A"

BASE_MAIN="$(git_r rev-parse refs/heads/main)"
BASE_REVIEW="$(git_r rev-parse refs/heads/review 2>/dev/null || git_r rev-parse refs/heads/main)"
runuser -u "$A" -- git -C "$WORK" fetch -q origin main
runuser -u "$A" -- git -C "$WORK" checkout -q -B main origin/main

write_entry check.sh
write_sleeper run
accept_manifest "test=test.sh\nhealth=health\n" check.sh run ||
  fail "custom test file push"
expect_deploy_ok "default run accepted"

rm -f "$WORK/run"
write_sleeper app
accept_manifest "run=app\ntest=check.sh\nhealth=health\n" app check.sh run &&
  expect_deploy_ok "run=app accepted from project.conf" &&
  grep -q "^ExecStart=$WORK/app$" /etc/systemd/system/"proj@$A.service.d"/manifest.conf &&
  ok "unit starts run=app" ||
  { cat "$OUT" >&2; fail "gate or unit ignored run=app from project.conf"; }

write_sleeper run
accept_manifest "run=run\ntest=test.sh\nhealth=health\n" run app ||
  fail "restore default run"

reject_manifest "missing mode missing, expected 100755" \
  "run=missing\ntest=test.sh\nhealth=health\n" && ok "missing run rejected by gate"

reject_manifest "invalid project.conf" "run=run\nunknown=1\n" &&
  ok "unknown key rejected by gate"

accept_manifest "run=run\nbuild=false\n" || fail "build=false push"
if deploy; then fail "build failure accepted"; else ok "build failure rejected"; fi

accept_manifest "run=run\nmigrate=false\n" || fail "migrate=false push"
if deploy; then fail "migrate failure accepted"; else ok "migrate failure rejected"; fi

rm -f "$WORK/built.txt"
accept_manifest "run=run\nbuild=printf built > built.txt\n" || fail "build push"
if deploy && [ -f "$WORK/built.txt" ]; then
  ok "build ran"
else
  cat "$OUT" >&2
  fail "build did not run"
fi

venv_tmp="$(mktemp -d)"
if python3 -m venv "$venv_tmp/venv" >/dev/null 2>&1; then
  rm -rf "$venv_tmp"
  accept_manifest "run=run\ndeps=python3 -m venv .venv\n" || fail "deps push"
  if deploy; then ok "python deps"; else cat "$OUT" >&2; fail "python deps"; fi
else
  rm -rf "$venv_tmp"
  fail "нет python3-venv: поставь python3-venv"
fi

accept_manifest "run=run\nsite=static\ndomains=example.test\n" || fail "site push"
if deploy && grep -q "example.test" /etc/caddy/conf.d/"$A".caddy 2>/dev/null; then
  ok "site generated"
else
  cat "$OUT" >&2
  fail "site not generated"
fi

accept_manifest "run=run\n" || fail "timezone default push"
if deploy && ! grep -q '^Environment=TZ=' /etc/systemd/system/"proj@$A.service.d"/manifest.conf 2>/dev/null; then
  ok "timezone default inherits host"
else
  cat "$OUT" >&2
  fail "timezone default wrote TZ"
fi

accept_manifest "run=run\ntimezone=Europe/Moscow\n" || fail "timezone push"
if deploy && grep -q "TZ=Europe/Moscow" /etc/systemd/system/"proj@$A.service.d"/manifest.conf 2>/dev/null; then
  ok "timezone applied"
else
  cat "$OUT" >&2
  fail "timezone not applied"
fi

chmod 0644 "$WORK/health"
reject_manifest "health mode 100644, expected 100755" "run=run\n" health &&
  ok "non-executable health rejected by gate"
write_entry health
accept_manifest "run=run\n" health || fail "restore health mode"

git_r update-ref refs/heads/main "$BASE_MAIN"
git_r update-ref refs/heads/review "$BASE_REVIEW"
rm -f "$OUT"
if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
