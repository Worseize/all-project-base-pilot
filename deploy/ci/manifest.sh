#!/usr/bin/env bash
# Seven manifest scenarios on a fixture project (root, Ubuntu CI).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
A="proj-a"
REPO="/srv/$A/repo.git"
WORK="/srv/$A/current"
FAILED=0
OUT="$(mktemp)"

fail() { printf 'FAIL: %s\n' "$*" >&2; FAILED=1; }
ok() { printf 'ok: %s\n' "$*"; }

git_a() { git -c safe.directory="$WORK" -C "$WORK" "$@"; }
git_r() { git -c safe.directory="$REPO" --git-dir="$REPO" "$@"; }

commit_manifest() {
  printf '%b\n' "$1" > "$WORK/project.conf"
  chown "$A:$A" "$WORK/project.conf"
  runuser -u "$A" -- git -C "$WORK" add project.conf
  runuser -u "$A" -- git -C "$WORK" commit -qm "manifest fixture" || true
  local sha
  sha="$(runuser -u "$A" -- git -C "$WORK" rev-parse HEAD)"
  git_r update-ref refs/heads/main "$sha"
}

deploy() {
  bash "$ROOT/deploy/deploy-project.sh" "$A" >"$OUT" 2>&1
}

expect_ok() {
  local name="$1"
  if deploy; then ok "$name"; else cat "$OUT" >&2; fail "$name"; fi
}

expect_fail() {
  local name="$1"
  if deploy; then fail "$name accepted"; else ok "$name rejected"; fi
}

BASE="$(git_r rev-parse refs/heads/main)"
runuser -u "$A" -- git -C "$WORK" config user.email "$A@agents.invalid"
runuser -u "$A" -- git -C "$WORK" config user.name "$A"
runuser -u "$A" -- git -C "$WORK" checkout -q -B main "$BASE" || true

commit_manifest "run=\ntest=true\nhealth=health\n"
if deploy; then fail "missing run accepted"; else ok "missing run rejected"; fi

commit_manifest "run=run\nunknown=1\n"
if deploy; then fail "unknown key accepted"; else ok "unknown key rejected"; fi

commit_manifest "run=run\nbuild=false\n"
if deploy; then fail "build failure accepted"; else ok "build failure rejected"; fi

commit_manifest "run=run\nmigrate=false\n"
if deploy; then fail "migrate failure accepted"; else ok "migrate failure rejected"; fi

commit_manifest "run=run\ndeps=python3 -m venv .venv\nbuild=true\n"
if deploy; then ok "deps/build"; else cat "$OUT" >&2; fail "deps/build"; fi

commit_manifest "run=run\nsite=static\ndomains=example.test\n"
if deploy && grep -q "example.test" /etc/caddy/conf.d/"$A".caddy 2>/dev/null; then
  ok "site generated"
else
  cat "$OUT" >&2
  fail "site not generated"
fi

commit_manifest "run=run\ntimezone=Europe/Moscow\n"
if deploy && grep -q "TZ=Europe/Moscow" /etc/systemd/system/"proj@$A.service.d"/manifest.conf 2>/dev/null; then
  ok "timezone applied"
else
  cat "$OUT" >&2
  fail "timezone not applied"
fi

git_r update-ref refs/heads/main "$BASE"
rm -f "$OUT"
if [ "$FAILED" -ne 0 ]; then
  exit 1
fi
