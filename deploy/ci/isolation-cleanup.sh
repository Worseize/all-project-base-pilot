#!/usr/bin/env bash
# Remove test projects created by deploy/ci/isolation.sh.
set -u

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root" >&2
  exit 1
fi

PROJECTS=("$@")
if [ "${#PROJECTS[@]}" -eq 0 ]; then
  PROJECTS=(proj-a proj-b)
fi

for PROJECT in "${PROJECTS[@]}"; do
  if id -u "$PROJECT" >/dev/null 2>&1; then
    userdel -r "$PROJECT" >/dev/null 2>&1 || userdel "$PROJECT" >/dev/null 2>&1 || true
  fi
  if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    systemctl disable "proj@$PROJECT.service" >/dev/null 2>&1 || true
  fi
  rm -rf "/srv/$PROJECT" "/etc/git-hooks/$PROJECT" "/etc/$PROJECT" "/var/lib/$PROJECT"
  rm -f "/etc/caddy/conf.d/$PROJECT.caddy" "/var/log/git/$PROJECT.log" "/etc/logrotate.d/proj-$PROJECT"
  rm -rf "/etc/systemd/system/proj@$PROJECT.service.d"
done

echo "isolation cleanup: done"
