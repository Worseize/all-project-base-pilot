#!/usr/bin/env bash
# Fail if project state or secrets are tracked in git.
# Usage: data-guard.sh <workdir>
set -euo pipefail
WORK="${1:?workdir}"
while IFS= read -r path; do
  case "$path" in
    data/*|*/data/*|.env|.env.*|*.log|var/lib/*)
      echo "state file tracked in git: $path" >&2
      exit 1
      ;;
  esac
done < <(git -c safe.directory="$WORK" -C "$WORK" ls-files)
for path in data/state.json data/app.db .env; do
  if ! git -c safe.directory="$WORK" -C "$WORK" check-ignore -q "$path" 2>/dev/null; then
    echo "data path not ignored: $path" >&2
    exit 1
  fi
done
