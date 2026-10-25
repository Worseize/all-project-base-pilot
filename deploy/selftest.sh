#!/usr/bin/env bash
# Node dependency self-test. Red means: install python3-venv.
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
  echo "selftest: python3 missing" >&2
  exit 1
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
if ! python3 -m venv "$tmp/venv" >/dev/null 2>&1; then
  echo "selftest: нет python3-venv — поставь пакет python3-venv" >&2
  exit 1
fi
echo "selftest: python3-venv ok"

mkdir -p "$tmp/data"
printf 'state\n' > "$tmp/data/state.json"
SNAPSHOT_DATA_DIR="$tmp/data" SNAPSHOT_DIR="$tmp/snap" \
  bash "$(dirname "${BASH_SOURCE[0]}")/snapshot.sh" selftest >/dev/null
if ! SNAPSHOT_DATA_DIR="$tmp/data" SNAPSHOT_DIR="$tmp/snap" \
  bash "$(dirname "${BASH_SOURCE[0]}")/snapshot.sh" selftest --verify >/dev/null; then
  echo "selftest: snapshot verify failed" >&2
  exit 1
fi
echo "selftest: snapshot verify ok"
bash "$(dirname "${BASH_SOURCE[0]}")/check-backups.sh" 26
