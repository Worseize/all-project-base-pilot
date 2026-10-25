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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
if ! command -v runuser >/dev/null 2>&1; then
  echo "runuser is required" >&2
  exit 1
fi
if [ ! -d "$WORK/.git" ]; then
  runuser -u "$PROJECT" -- git clone "$REPO" "$WORK"
fi
chown -R "$PROJECT:$PROJECT" "$WORK"
runuser -u "$PROJECT" -- git -C "$WORK" fetch origin main
runuser -u "$PROJECT" -- git -C "$WORK" checkout -B main FETCH_HEAD
runuser -u "$PROJECT" -- git -C "$WORK" reset --hard FETCH_HEAD
chown -R "$PROJECT:$PROJECT" "$WORK"
install -d -m 0750 -o "$PROJECT" -g "$PROJECT" "/var/lib/$PROJECT"
git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/review refs/heads/main

MANIFEST_PY="$SCRIPT_DIR/manifest.py"
MANIFEST="$WORK/project.conf"
if ! python3 "$MANIFEST_PY" check "$MANIFEST"; then
  echo "invalid project.conf for $PROJECT" >&2
  exit 1
fi
mget() { python3 "$MANIFEST_PY" get "$MANIFEST" "$1"; }
RUN_PATH="$(mget run)"
BUILD="$(mget build)"
DEPS="$(mget deps)"
MIGRATE="$(mget migrate)"
TIMEZONE="$(mget timezone)"
MEMORY="$(mget memory)"
CPU="$(mget cpu)"
PORT="$(mget port)"
case "$RUN_PATH" in
  /*|*..*) echo "run must be a relative path" >&2; exit 1 ;;
esac
run_project() {
  runuser -u "$PROJECT" -- env PROJECT_DATA_DIR="/var/lib/$PROJECT" TZ="$TIMEZONE" \
    bash -c "cd '$WORK' && $1"
}
if [ -n "$DEPS" ]; then
  if ! run_project "$DEPS"; then echo "deps failed" >&2; exit 1; fi
fi
if [ -n "$BUILD" ]; then
  if ! run_project "$BUILD"; then echo "build failed" >&2; exit 1; fi
fi
if [ -n "$MIGRATE" ]; then
  if ! run_project "$MIGRATE"; then echo "migrate failed" >&2; exit 1; fi
fi
bash "$SCRIPT_DIR/site-config.sh" "$PROJECT" "$WORK"

install -d -m 0755 /etc/systemd/system/"proj@$PROJECT.service.d"
cat > /etc/systemd/system/"proj@$PROJECT.service.d"/manifest.conf <<EOF
[Service]
Environment=TZ=$TIMEZONE
Environment=PROJECT_PORT=$PORT
MemoryMax=$MEMORY
CPUQuota=$CPU
EOF
if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  systemctl daemon-reload
fi

if [ -f "$WORK/project.conf" ]; then
  if [ ! -f "$WORK/$RUN_PATH" ] || [ ! -x "$WORK/$RUN_PATH" ]; then
    echo "run file missing or not executable: $RUN_PATH" >&2
    exit 1
  fi
fi

if [ ! -x "$WORK/$RUN_PATH" ]; then
  echo "delivered; warning: $WORK/$RUN_PATH is missing or not executable" >&2
  exit 0
fi

if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  systemctl restart "proj@$PROJECT.service"
  if ! systemctl is-active --quiet "proj@$PROJECT.service"; then
    echo "service failed to start: proj@$PROJECT.service" >&2
    exit 1
  fi
  echo "delivered and restarted: proj@$PROJECT.service"
else
  echo "delivered: $WORK"
fi
