#!/usr/bin/env bash
# Install the auto-merge script and timer (root).
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

install -m 0755 -o root -g root "$SCRIPT_DIR/auto-merge.sh" /usr/local/sbin/proj-auto-merge
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj-auto-merge.service" /etc/systemd/system/proj-auto-merge.service
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj-auto-merge.timer" /etc/systemd/system/proj-auto-merge.timer
install -d -m 0755 -o root -g root /etc/proj-base
if [ -f "$ROOT/projects.json" ] && [ ! -f /etc/proj-base/projects.json ]; then
  install -m 0640 -o root -g root "$ROOT/projects.json" /etc/proj-base/projects.json
fi
systemctl daemon-reload
systemctl enable --now proj-auto-merge.timer
echo "auto-merge installed; registry: /etc/proj-base/projects.json"
