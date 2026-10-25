#!/usr/bin/env bash
# Snapshot project data outside git: tar + sha256; verify by extraction.
# Usage: snapshot.sh <id> [--verify]
set -euo pipefail
if [ "$#" -lt 1 ]; then
  echo "usage: $0 <id> [--verify]" >&2
  exit 2
fi
ID="$1"
VERIFY=0
[ "${2:-}" = "--verify" ] && VERIFY=1
DATA_DIR="${SNAPSHOT_DATA_DIR:-/var/lib/$ID}"
BACKUP_DIR="${SNAPSHOT_DIR:-/var/backups/$ID}"
RETENTION="${SNAPSHOT_RETENTION_DAYS:-7}"

if [ ! -d "$DATA_DIR" ]; then
  echo "data dir missing: $DATA_DIR" >&2
  exit 1
fi

if [ "$VERIFY" -eq 1 ]; then
  latest="$(find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.gz' -type f 2>/dev/null | sort | tail -n 1)"
  [ -n "$latest" ] || { echo "no snapshot in $BACKUP_DIR" >&2; exit 1; }
  sha_file="$latest.sha256"
  [ -f "$sha_file" ] || { echo "sha256 missing for $latest" >&2; exit 1; }
  (cd "$BACKUP_DIR" && sha256sum -c "$(basename "$sha_file")") >/dev/null || {
    echo "snapshot checksum mismatch: $latest" >&2
    exit 1
  }
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  tar -xzf "$latest" -C "$tmp" || {
    echo "snapshot extract failed: $latest" >&2
    exit 1
  }
  echo "verified: $latest"
  exit 0
fi

install -d -m 0750 "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive="$BACKUP_DIR/$stamp.tar.gz"
tar -czf "$archive" \
  --exclude='*.env' --exclude='.env*' --exclude='*.log' \
  -C "$DATA_DIR" . || {
    echo "snapshot failed" >&2
    exit 1
  }
(cd "$BACKUP_DIR" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.gz' -mtime +"$RETENTION" -delete 2>/dev/null || true
echo "snapshot: $archive"
