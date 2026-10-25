#!/usr/bin/env bash
# .env.local must be rejected; .env.example must be allowed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
A="proj-a"
WORK="/srv/$A/work"
fail() { echo "FAIL: $*" >&2; exit 1; }

runuser -u "$A" -- git -C "$WORK" config user.email "$A@agents.invalid"
runuser -u "$A" -- git -C "$WORK" config user.name "$A"
runuser -u "$A" -- bash -c "cd '$WORK' && printf 'secret\n' > .env.local && git add -f .env.local && git commit -m env-local" >/dev/null
if runuser -u "$A" -- git -C "$WORK" push origin HEAD:review >/dev/null 2>&1; then
  fail ".env.local accepted"
fi
runuser -u "$A" -- git -C "$WORK" reset --hard HEAD~1 >/dev/null
runuser -u "$A" -- bash -c "cd '$WORK' && rm -f .env.local && printf 'EXAMPLE=1\n' > .env.example && git add .env.example && git commit -m env-example" >/dev/null
if ! runuser -u "$A" -- git -C "$WORK" push origin HEAD:review >/dev/null 2>&1; then
  fail ".env.example rejected"
fi
echo "ok: .env.local rejected, .env.example accepted"
