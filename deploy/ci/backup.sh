#!/usr/bin/env bash
# Project backup fixture: create, verify, count entries.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA="$(mktemp -d)"
DIR="$(mktemp -d)"
chmod 0755 "$DIR"
printf 'one\n' > "$DATA/a.txt"
printf 'two\n' > "$DATA/b.txt"
BACKUP_DATA_DIR="$DATA" BACKUP_DIR="$DIR" BACKUP_KEEP=2 \
  bash "$ROOT/deploy/project-backup.sh" fixture >/dev/null
archive="$(find "$DIR" -name '*.tar.gz' | head -n 1)"
[ -n "$archive" ] && [ -s "$archive" ] && [ -f "$archive.sha256" ] || {
  echo "backup missing" >&2
  exit 1
}
[ "$(stat -c %a "$DIR")" = "700" ] || { echo "backup dir mode" >&2; exit 1; }
[ "$(stat -c %U:%G "$DIR")" = "root:root" ] || { echo "backup dir owner" >&2; exit 1; }
[ "$(stat -c %a "$archive")" = "600" ] || { echo "backup file mode" >&2; exit 1; }
BACKUP_DATA_DIR="$DATA" BACKUP_DIR="$DIR" \
  bash "$ROOT/deploy/project-backup.sh" fixture --verify >/dev/null
count="$(tar -tzf "$archive" | grep -v '^\./$' | wc -l)"
[ "$count" -ge 2 ] || { echo "restore count $count" >&2; exit 1; }
printf 'extra\n' > "$DATA/c.txt"
if BACKUP_DATA_DIR="$DATA" BACKUP_DIR="$DIR" \
  bash "$ROOT/deploy/project-backup.sh" fixture --verify >/dev/null 2>&1; then
  echo "count mismatch not detected" >&2
  exit 1
fi
rm -rf "$DATA" "$DIR"
echo "ok: backup created, mode 0700, verified, count=$count"
