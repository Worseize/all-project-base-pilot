#!/usr/bin/env bash
# Daily project-data backup owned by the node (root).
# Usage: project-backup.sh <id> [--verify]
set -euo pipefail
ID="${1:?project id}"
MODE="${2:-}"
DATA="${BACKUP_DATA_DIR:-/var/lib/$ID}"
DIR="${BACKUP_DIR:-/var/backups/$ID}"
KEEP="${BACKUP_KEEP:-14}"

[ -d "$DATA" ] || { echo "data dir missing: $DATA" >&2; exit 1; }

if [ "$MODE" = "--verify" ]; then
  latest="$(find "$DIR" -maxdepth 1 -name '*.tar.gz' -type f 2>/dev/null | sort | tail -n 1)"
  [ -n "$latest" ] || { echo "no backup in $DIR" >&2; exit 1; }
  [ -f "$latest.sha256" ] || { echo "sha256 missing" >&2; exit 1; }
  (cd "$DIR" && sha256sum -c "$(basename "$latest.sha256")") >/dev/null || {
    echo "checksum mismatch" >&2
    exit 1
  }
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  tar -xzf "$latest" -C "$tmp"
  source_count="$(find "$DATA" -mindepth 1 | wc -l)"
  archive_count="$(tar -tzf "$latest" | awk '!/^\.\/$/' | wc -l)"
  if [ "$source_count" -ne "$archive_count" ]; then
    echo "restore count mismatch: $source_count != $archive_count" >&2
    exit 1
  fi
  echo "verified: $latest entries=$archive_count"
  exit 0
fi

install -d -m 0700 -o root -g root "$DIR"
chown root:root "$DIR"
chmod 0700 "$DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$DIR/$stamp.tar.gz"
tar -czf "$archive" -C "$DATA" . || { echo "backup failed" >&2; exit 1; }
chmod 0600 "$archive"
(cd "$DIR" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
chmod 0600 "$archive.sha256"
tar -tzf "$archive" >/dev/null || { echo "backup unreadable" >&2; exit 1; }
tar -tzf "$archive" | grep -q '^\./' || { echo "backup has no project dir" >&2; exit 1; }
ls -1t "$DIR"/*.tar.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while IFS= read -r old; do
  rm -f "$old" "$old.sha256"
done
echo "backup: $archive"
