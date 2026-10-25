#!/usr/bin/env bash
# Create a project repository from the minimal skeleton (root).
# Usage: sudo deploy/init-project.sh <project>
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if [ "$#" -ne 1 ]; then
  echo "usage: $0 <project>" >&2
  exit 2
fi
PROJECT="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKELETON="${SKELETON:-$SCRIPT_DIR/../skeleton/project}"
[ -d "$SKELETON" ] || { echo "skeleton not found: $SKELETON" >&2; exit 1; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp -a "$SKELETON/." "$tmp/"
chmod +x "$tmp/run" "$tmp/test.sh" "$tmp/health"
git -C "$tmp" init -q
git -C "$tmp" config user.email "skeleton@agents.invalid"
git -C "$tmp" config user.name "skeleton"
git -C "$tmp" add -A
git -C "$tmp" commit -qm "project skeleton"

SOURCE_REPO="$tmp" SOURCE_REF=HEAD \
  ALLOWED_PATHS="*" \
  bash "$SCRIPT_DIR/bootstrap-project.sh" "$PROJECT"
