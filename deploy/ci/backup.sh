#!/usr/bin/env bash
# Project backup fixture: create, verify, count entries.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA="$(mktemp -d)"
DIR="$(mktemp -d)"
printf 'one\n' > "$DATA/a.txt"
printf 'two\n' > "$DATA/b.txt"
dd if=/dev/zero of="$DATA/big.bin" bs=1024 count=70 status=none
BACKUP_DATA_DIR="$DATA" BACKUP_DIR="$DIR" BACKUP_KEEP=2 \
  bash "$ROOT/deploy/project-backup.sh" fixture >/dev/null
archive="$(find "$DIR" -name '*.tar.gz' | head -n 1)"
[ -n "$archive" ] && [ -s "$archive" ] && [ -f "$archive.sha256" ] || {
  echo "backup missing" >&2
  exit 1
}
[ "$(stat -c %a "$DIR")" = "700" ] || { echo "backup dir mode" >&2; exit 1; }
[ "$(stat -c %a "$archive")" = "600" ] || { echo "backup file mode" >&2; exit 1; }
BACKUP_DATA_DIR="$DATA" BACKUP_DIR="$DIR" \
  bash "$ROOT/deploy/project-backup.sh" fixture --verify >/dev/null
count="$(tar -tzf "$archive" | wc -l)"
[ "$count" -ge 3 ] || { echo "restore count $count" >&2; exit 1; }
OLD="$(mktemp -d)"
mkdir -p "$OLD/fixture"
cp "$archive" "$archive.sha256" "$OLD/fixture/"
touch -d '48 hours ago' "$OLD/fixture/"*.tar.gz
if bash "$ROOT/deploy/check-backups.sh" 26 "$OLD" >/dev/null 2>&1; then
  echo "stale backup accepted" >&2
  exit 1
fi
rm -rf "$OLD" "$DATA" "$DIR"
echo "ok: backup created, verified, entries=$count, stale rejected"
