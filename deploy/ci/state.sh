#!/usr/bin/env bash
# Normalized host-state snapshot/diff for acceptance (no inodes/sizes/dates).
# Usage: state.sh snapshot <file> | state.sh diff <before> <after>
set -euo pipefail

snapshot() {
  local out="$1"
  {
    for path in /srv /srv/app /var/lib /var/lib/watchdog; do
      if [ -e "$path" ]; then
        stat -c "path %n %a %U:%G" "$path"
      else
        echo "path $path missing"
      fi
    done
    unit="/etc/systemd/system/proj@.service"
    if [ -f "$unit" ]; then
      echo "unit proj@.service $(sha256sum "$unit" | awk '{print $1}')"
    else
      echo "unit proj@.service missing"
    fi
    if command -v systemctl >/dev/null 2>&1; then
      systemctl list-unit-files 'proj@*' 'watchdog*' --no-legend 2>/dev/null |
        awk '{print "unitfile " $1 " " $2}' | sort
    fi
    find /etc/logrotate.d -maxdepth 1 -type f -printf 'logrotate %f\n' 2>/dev/null | sort || true
    find /etc/git-hooks -mindepth 1 -maxdepth 1 -type d -printf 'hooks %f\n' 2>/dev/null | sort || true
    if command -v ufw >/dev/null 2>&1; then
      ufw status 2>/dev/null | sed -n '/^To /,$p' | sort
    fi
    if [ -f /etc/sysctl.d/90-template-hardening.conf ]; then
      while IFS='=' read -r key value; do
        key="$(printf '%s' "$key" | tr -d ' ')"
        [ -n "$key" ] || continue
        [ "${key#\#}" = "$key" ] || continue
        printf 'sysctl %s=%s\n' "$key" "$(sysctl -n "$key" 2>/dev/null || echo missing)"
      done < /etc/sysctl.d/90-template-hardening.conf
    fi
    [ -f /etc/timezone ] && echo "timezone $(cat /etc/timezone)" || echo "timezone missing"
    getent passwd 2>/dev/null | awk -F: '$1 ~ /^(zz-|proj-)/ {print "user " $1}' | sort
    getent group 2>/dev/null | awk -F: '$1 ~ /^(zz-|proj-)/ {print "group " $1}' | sort
  } > "$out"
  if [ -n "${STATE_IGNORE:-}" ]; then
    for id in $STATE_IGNORE; do
      grep -vE "(^| )${id}( |$)" "$out" > "$out.tmp" || true
      mv "$out.tmp" "$out"
    done
  fi
}

case "${1:-}" in
  snapshot)
    [ -n "${2:-}" ] || { echo "usage: state.sh snapshot <file>" >&2; exit 2; }
    snapshot "$2"
    ;;
  diff)
    [ -n "${2:-}" ] && [ -n "${3:-}" ] || { echo "usage: state.sh diff <before> <after>" >&2; exit 2; }
    if ! diff -u "$2" "$3"; then
      exit 1
    fi
    ;;
  *)
    echo "usage: state.sh snapshot <file> | diff <before> <after>" >&2
    exit 2
    ;;
esac
