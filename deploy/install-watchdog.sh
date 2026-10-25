#!/usr/bin/env bash
# Install the single node watchdog (root). Health checks run per project.
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -m 0755 -o root -g root "$SCRIPT_DIR/health-check.sh" /usr/local/sbin/watchdog-health
install -m 0755 -o root -g root "$SCRIPT_DIR/manifest.py" /usr/local/sbin/proj-manifest
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/watchdog-health.service" /etc/systemd/system/
install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/watchdog-health.timer" /etc/systemd/system/
install -d -m 0750 -o root -g root /var/lib/watchdog
[ -d /var/log ] || install -d -m 0755 -o root -g root /var/log
systemctl daemon-reload
systemctl enable --now watchdog-health.timer
echo "installed: watchdog-health.timer"
