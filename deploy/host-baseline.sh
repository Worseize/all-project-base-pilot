#!/usr/bin/env bash
# Host baseline for an admin node: firewall, fail2ban, sysctl, journald,
# logrotate and timezone. Idempotent; run as root on Linux with systemd.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi
if [ ! -d /run/systemd/system ]; then
  echo "systemd is not running" >&2
  exit 1
fi
SSH_PORT="${SSH_PORT:-22}"
TIMEZONE="${TIMEZONE:-UTC}"

for cmd in ufw fail2ban-client timedatectl sysctl systemctl; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "required command missing: $cmd" >&2
    exit 1
  }
done

ufw default deny incoming
ufw default allow outgoing
ufw limit "$SSH_PORT/tcp"
ufw allow 80,443/tcp
ufw --force enable

install -d -m 0755 -o root -g root /etc/fail2ban/jail.d
cat > /etc/fail2ban/jail.d/sshd.local <<EOF
[sshd]
enabled = true
backend = file
logpath = /var/log/auth.log
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
fail2ban-client reload

cat > /etc/sysctl.d/90-template-hardening.conf <<'EOF'
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.tcp_syncookies = 1
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
EOF
sysctl --system >/dev/null

install -d -m 0755 -o root -g root /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/90-template.conf <<'EOF'
[Journal]
Storage=persistent
SystemMaxUse=200M
RuntimeMaxUse=50M
MaxRetentionSec=1month
EOF
systemctl restart systemd-journald

cat > /etc/logrotate.d/proj-logs <<'EOF'
/var/log/git/*.log {
    size 100k
    rotate 5
    missingok
    notifempty
    copytruncate
}
EOF

current_timezone="$(timedatectl show -p Timezone --value)"
if [ "$current_timezone" != "$TIMEZONE" ]; then
  timedatectl set-timezone "$TIMEZONE"
fi

echo "host baseline: ready (ssh=$SSH_PORT tz=$TIMEZONE)"
