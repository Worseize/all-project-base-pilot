#!/usr/bin/env bash
# Auto-merge review -> main only after the trusted gate passes.
# Root timer entrypoint; no content analysis, only the gate result.
set -uo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="${1:-projects.json}"
MARKERS="/var/lib/proj-base/gate"
LOG="/var/log/git/auto-merge.log"
mkdir -p "$MARKERS" /var/log/git
touch "$LOG"

log() { printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG"; }
fail() { log "reject $*"; }

if [ ! -f "$REGISTRY" ]; then
  log "registry missing: $REGISTRY"
  exit 2
fi
mapfile -t IDS < <(python3 - "$REGISTRY" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
for key in sorted(data.get("projects", {})):
    print(key)
PY
)

for PROJECT in "${IDS[@]}"; do
  REPO="/srv/$PROJECT/repo.git"
  [ -d "$REPO" ] || { fail "$PROJECT repo missing"; continue; }
  review="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse --verify --quiet refs/heads/review || true)"
  main="$(git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse --verify --quiet refs/heads/main || true)"
  [ -n "$review" ] || continue
  [ -n "$main" ] || { fail "$PROJECT main missing"; continue; }
  [ "$review" != "$main" ] || continue

  tmp="$(mktemp -d)"
  if ! git -c safe.directory="$REPO" --git-dir="$REPO" archive "$review" | tar -x -C "$tmp"; then
    fail "$PROJECT archive failed"
    rm -rf "$tmp"
    continue
  fi
  if git -c safe.directory="$REPO" --git-dir="$REPO" cat-file -e refs/heads/main:test.sh 2>/dev/null; then
    for f in run test.sh health; do
      mode="$(git -c safe.directory="$REPO" --git-dir="$REPO" ls-tree "$review" -- "$f" | awk '{print $1}')"
      if [ "$mode" != "100755" ]; then
        fail "$PROJECT $f mode ${mode:-missing}, expected 100755"
        rm -rf "$tmp"
        continue 2
      fi
    done
    git -c safe.directory="$REPO" --git-dir="$REPO" show refs/heads/main:test.sh > "$tmp/.trusted-test.sh"
    if ! (cd "$tmp" && bash .trusted-test.sh) >/dev/null 2>&1; then
      fail "$PROJECT test.sh red at $review"
      rm -rf "$tmp"
      continue
    fi
  elif git -c safe.directory="$REPO" --git-dir="$REPO" cat-file -e refs/heads/main:verify.py 2>/dev/null; then
    if ! git -c safe.directory="$REPO" --git-dir="$REPO" show refs/heads/main:verify.py > "$tmp/.trusted-verify.py"; then
      fail "$PROJECT trusted verify missing"
      rm -rf "$tmp"
      continue
    fi
    if ! (cd "$tmp" && python3 .trusted-verify.py) >/dev/null 2>&1; then
      fail "$PROJECT gate red at $review"
      rm -rf "$tmp"
      continue
    fi
  else
    fail "$PROJECT no gate in main"
    rm -rf "$tmp"
    continue
  fi
  rm -rf "$tmp"

  printf '{"commit":"%s","gate":"green","at":"%s"}\n' "$review" "$(date -Is)" > "$MARKERS/$PROJECT.json"
  log "gate green $PROJECT $review"

  install -d -m 0750 /var/lib/proj-base/deploy
  printf '%s\n' "$main" > "/var/lib/proj-base/deploy/$PROJECT.sha"

  if ! git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/main "$review" "$main"; then
    fail "$PROJECT update-ref failed"
    continue
  fi
  if bash "$SCRIPT_DIR/deploy-project.sh" "$PROJECT" >/dev/null 2>&1; then
    git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/review "$review" || true
    log "merged $PROJECT $main -> $review; review aligned"
  else
    git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/main "$main" "$review" || true
    git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/review "$main" || true
    fail "$PROJECT deploy failed; rolled back to $main; review aligned"
  fi
done
