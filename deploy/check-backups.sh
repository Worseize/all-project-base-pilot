#!/usr/bin/env bash
# Check that every project has a fresh, readable backup pair.
# Usage: check-backups.sh [hours] [backup-root]
set -euo pipefail
MAX_HOURS="${1:-26}"
ROOT="${2:-/var/backups}"
SKIP_IDS="${SKIP_IDS:-app}"
bad=0
now="$(date +%s)"

for dir in "$ROOT"/*; do
  [ -d "$dir" ] || continue
  id="$(basename "$dir")"
  case " $SKIP_IDS " in *" $id "*) continue ;; esac
  latest="$(find "$dir" -maxdepth 1 -name '*.tar.gz' -type f 2>/dev/null | sort | tail -n 1)"
  if [ -z "$latest" ]; then
    echo "[FAIL] $id: нет снимка" >&2
    bad=$((bad + 1))
    continue
  fi
  if [ ! -f "$latest.sha256" ]; then
    echo "[FAIL] $id: нет sha256" >&2
    bad=$((bad + 1))
    continue
  fi
  if ! (cd "$dir" && sha256sum -c "$(basename "$latest.sha256")") >/dev/null 2>&1; then
    echo "[FAIL] $id: sha256 не совпал" >&2
    bad=$((bad + 1))
    continue
  fi
  if ! tar -tzf "$latest" >/dev/null 2>&1; then
    echo "[FAIL] $id: архив не читается" >&2
    bad=$((bad + 1))
    continue
  fi
  age=$(( (now - $(stat -c %Y "$latest")) / 3600 ))
  if [ "$age" -gt "$MAX_HOURS" ]; then
    echo "[FAIL] $id: последний снимок ${age} ч назад (порог ${MAX_HOURS} ч)" >&2
    bad=$((bad + 1))
  fi
done

if [ "$bad" -ne 0 ]; then
  echo "backups: провалено $bad" >&2
  exit 1
fi
echo "backups: OK"
