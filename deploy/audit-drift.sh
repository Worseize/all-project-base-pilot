#!/usr/bin/env bash
# Host health + registry drift. Root, Linux with systemd.
# Usage: deploy/audit-drift.sh [projects.json]
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root (reads /srv and host config)" >&2
  exit 1
fi
REGISTRY="${1:-projects.json}"
SSH_PORT="${SSH_PORT:-22}"
HOST_TZ="${TIMEZONE:-$(timedatectl show -p Timezone --value 2>/dev/null || echo UTC)}"
TIMEZONE="$HOST_TZ"
FAILED=0
fail() { echo "drift: $*" >&2; FAILED=1; }

command -v ufw >/dev/null 2>&1 || fail "ufw missing"
ufw status 2>/dev/null | grep -q "Status: active" || fail "ufw inactive"
ufw status 2>/dev/null | grep -q "$SSH_PORT/tcp.*LIMIT" || fail "ssh limit missing"
if [ -f /etc/fail2ban/jail.d/sshd.local ] &&
  fail2ban-client status sshd >/dev/null 2>&1; then
  :
else
  fail "fail2ban sshd jail missing/inactive"
fi
[ -f /etc/sysctl.d/90-template-hardening.conf ] || fail "sysctl hardening missing"
[ -f /etc/systemd/journald.conf.d/90-template.conf ] || fail "journald limits missing"
[ -f /etc/logrotate.d/proj-logs ] || fail "logrotate rule missing"
[ "$(timedatectl show -p Timezone --value 2>/dev/null || true)" = "$TIMEZONE" ] ||
  fail "timezone is not $TIMEZONE"

for unit in apt-daily.timer apt-daily-upgrade.timer unattended-upgrades; do
  if ! systemctl is-enabled --quiet "$unit" 2>/dev/null; then
    fail "updates disabled: $unit"
  fi
done

while IFS= read -r unit; do
  [ -n "$unit" ] || continue
  env_line="$(systemctl show "$unit" -p Environment --value 2>/dev/null || true)"
  tz="$(printf '%s\n' "$env_line" | tr ' ' '\n' | sed -n 's/^TZ=//p' | head -n 1)"
  if [ -n "$tz" ] && [ "$tz" != "$TIMEZONE" ]; then
    fail "$unit TZ=$tz, host=$TIMEZONE"
  fi
done < <(systemctl list-units 'proj@*.service' --state=running --no-legend 2>/dev/null | awk '{print $1}')

while IFS= read -r unit; do
  case "$unit" in proj-backup@*.timer) ;; *) continue ;; esac
  id="${unit#proj-backup@}"; id="${id%.timer}"
  [ -d "/srv/$id/repo.git" ] || fail "orphan backup timer: $unit"
done < <(systemctl list-unit-files 'proj-backup@*.timer' --no-legend 2>/dev/null | awk '{print $1}')

if [ -f "$REGISTRY" ]; then
  mapfile -t IDS < <(python3 - "$REGISTRY" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
for key in sorted(data.get("projects", {})):
    print(key)
PY
  )
  declare -A REG=()
  for id in "${IDS[@]}"; do REG["$id"]=1; done
  for id in "${IDS[@]}"; do
    [ -d "/srv/$id" ] || fail "orphan-registry: /srv/$id missing"
  done
  while IFS= read -r dir; do
    id="$(basename "$dir")"
    if [ ! -d "$dir/repo.git" ] && [ ! -f "$dir/CANARY" ]; then
      continue
    fi
    [ -n "${REG[$id]:-}" ] || fail "orphan-dir: /srv/$id not in registry"
  done < <(find /srv -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
else
  echo "registry not found: $REGISTRY (host checks only)" >&2
fi

if [ "$FAILED" -ne 0 ]; then
  echo "DRIFT: found" >&2
  exit 1
fi
echo "DRIFT: clean"
