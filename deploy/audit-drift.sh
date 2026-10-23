#!/usr/bin/env bash
# Orphans in either direction: registry without directory, directory without registry.
# Usage: deploy/audit-drift.sh [projects.json]
set -euo pipefail

REGISTRY="${1:-projects.json}"
if [ ! -f "$REGISTRY" ]; then
  echo "registry not found: $REGISTRY" >&2
  exit 2
fi
if [ "$(id -u)" -ne 0 ]; then
  echo "run as root (reads /srv)" >&2
  exit 1
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
declare -A REG=()
for id in "${IDS[@]}"; do REG["$id"]=1; done

FAILED=0
for id in "${IDS[@]}"; do
  if [ ! -d "/srv/$id" ]; then
    echo "orphan-registry: /srv/$id missing" >&2
    FAILED=1
  fi
done

while IFS= read -r dir; do
  id="$(basename "$dir")"
  if [ -z "${REG[$id]:-}" ]; then
    echo "orphan-dir: /srv/$id not in registry" >&2
    FAILED=1
  fi
done < <(find /srv -mindepth 1 -maxdepth 1 -type d 2>/dev/null)

if [ "$FAILED" -ne 0 ]; then
  echo "DRIFT: found" >&2
  exit 1
fi
echo "DRIFT: clean"
