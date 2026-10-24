#!/usr/bin/env bash
# Extend a project's allowed paths (root-only).
# Usage: sudo deploy/allow-path.sh <project> <path> [path...]
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if [ "$#" -lt 2 ]; then
  echo "usage: $0 <project> <path> [path...]" >&2
  exit 2
fi
PROJECT="$1"
shift
FILE="/etc/git-hooks/$PROJECT/allowed-paths"
[ -f "$FILE" ] || { echo "allowlist missing: $FILE" >&2; exit 1; }

tmp="$(mktemp)"
cat "$FILE" > "$tmp"
for path in "$@"; do
  case "$path" in
    /*|*..*|*\\*) echo "invalid path: $path" >&2; exit 2 ;;
  esac
  printf '%s\n' "$path" >> "$tmp"
done
sort -u "$tmp" > "$FILE"
rm -f "$tmp"
chown root:root "$FILE"
chmod 0644 "$FILE"
echo "allowed paths for $PROJECT: $(tr '\n' ' ' < "$FILE")"
