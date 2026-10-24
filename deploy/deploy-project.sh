#!/usr/bin/env bash
# Deliver accepted main into the project's runtime checkout.
# Usage: sudo deploy/deploy-project.sh <project>
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
if ! [[ "$PROJECT" =~ ^[a-z][a-z0-9-]{2,19}$ ]]; then
  echo "invalid project id: $PROJECT" >&2
  exit 2
fi

REPO="/srv/$PROJECT/repo.git"
WORK="/srv/$PROJECT/current"
if [ ! -d "$REPO" ]; then
  echo "repo not found: $REPO" >&2
  exit 1
fi
if [ ! -d "$WORK/.git" ]; then
  git -c safe.directory="$REPO" clone "$REPO" "$WORK"
fi
chown -R "$PROJECT:$PROJECT" "$WORK"
git -c safe.directory="$WORK" -C "$WORK" fetch origin main
git -c safe.directory="$WORK" -C "$WORK" checkout -B main FETCH_HEAD
git -c safe.directory="$WORK" -C "$WORK" reset --hard FETCH_HEAD
chown -R "$PROJECT:$PROJECT" "$WORK"

if [ ! -x "$WORK/run" ]; then
  echo "delivered; warning: $WORK/run is missing or not executable" >&2
  exit 0
fi

if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  systemctl restart "proj@$PROJECT.service"
  echo "delivered and restarted: proj@$PROJECT.service"
else
  echo "delivered: $WORK"
fi
