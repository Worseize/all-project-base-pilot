#!/usr/bin/env bash
# Install the per-project backup unit and script (root).
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -m 0755 -o root -g root "$SCRIPT_DIR/project-backup.sh" /usr/local/sbin/proj-backup
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj-backup@.service" /etc/systemd/system/
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj-backup@.timer" /etc/systemd/system/
systemctl daemon-reload
echo "installed: proj-backup@.service/timer"
