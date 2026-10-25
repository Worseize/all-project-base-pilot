#!/usr/bin/env bash
# One node watchdog: run project health, alert once, suppress repeats.
# Usage: watchdog-health [projects.json]
set -euo pipefail

REGISTRY="${1:-/etc/proj-base/projects.json}"
STATE_FILE="${WATCHDOG_STATE_FILE:-/var/lib/watchdog/health-state.json}"
LOG="${WATCHDOG_LOG:-/var/log/watchdog-health.log}"
TIMEOUT="${WATCHDOG_TIMEOUT:-30}"
REPEAT="${WATCHDOG_REPEAT_SECONDS:-3600}"
NOTIFY="${WATCHDOG_NOTIFY_CMD:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG" 2>/dev/null || true
}

notify() {
  local message="$1"
  log "$message"
  if [ -n "$NOTIFY" ]; then
    printf '%s\n' "$message" | bash -c "$NOTIFY \"\$1\"" -- "$message" || true
    return
  fi
  if [ -n "${WATCHDOG_TELEGRAM_TOKEN:-}" ] && [ -n "${WATCHDOG_TELEGRAM_CHAT:-}" ] &&
    command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 10 -X POST \
      "https://api.telegram.org/bot${WATCHDOG_TELEGRAM_TOKEN}/sendMessage" \
      -d "chat_id=${WATCHDOG_TELEGRAM_CHAT}" --data-urlencode "text=${message}" >/dev/null || true
    return
  fi
  logger -t watchdog-health "$message" 2>/dev/null || true
}

state_get() {
  python3 - "$STATE_FILE" "$1" <<'PY'
import json
import sys
path, key = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as handle:
        item = json.load(handle).get(key, {})
except Exception:
    item = {}
print(item.get("status", ""))
print(item.get("last_alert", 0))
print(item.get("reason", ""))
PY
}

state_set() {
  python3 - "$STATE_FILE" "$1" "$2" "$3" "$4" <<'PY'
import json
import os
import sys
path, key, status, reason, last_alert = sys.argv[1:6]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except Exception:
    data = {}
data[key] = {"status": status, "reason": reason, "last_alert": int(last_alert)}
os.makedirs(os.path.dirname(path), mode=0o750, exist_ok=True)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(data, handle, ensure_ascii=False, sort_keys=True)
os.replace(tmp, path)
PY
}

mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG")"
touch "$LOG" 2>/dev/null || true

if [ ! -f "$REGISTRY" ]; then
  notify "watchdog: registry missing: $REGISTRY"
  exit 1
fi

mapfile -t PROJECTS < <(python3 - "$REGISTRY" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    for name in json.load(handle).get("projects", {}):
        print(name)
PY
)

now="$(date +%s)"
for project in "${PROJECTS[@]}"; do
  work="/srv/$project/current"
  health="$work/health"
  prev_status="$(state_get "$project" | sed -n '1p')"
  prev_alert="$(state_get "$project" | sed -n '2p')"
  [ "$prev_alert" = "0" ] || prev_alert="${prev_alert:-0}"

  if [ ! -f "$health" ] || [ ! -x "$health" ]; then
    status="missing"
    reason="health missing or not executable: $health"
  else
    set +e
    output="$(runuser -u "$project" -- timeout "$TIMEOUT" "$health" 2>&1)"
    code=$?
    set -e
    if [ "$code" -eq 124 ]; then
      status="sick"
      reason="timeout ${TIMEOUT}s"
    elif [ "$code" -eq 0 ]; then
      status="healthy"
      reason=""
    else
      status="sick"
      reason="$(printf '%s' "$output" | head -n 1 | cut -c1-300)"
      [ -n "$reason" ] || reason="health exit $code"
    fi
  fi

  if [ "$status" = "healthy" ]; then
    if [ "$prev_status" = "sick" ] || [ "$prev_status" = "missing" ]; then
      notify "watchdog: $project восстановлен"
    fi
    state_set "$project" "$status" "" 0
    continue
  fi

  # sick or missing: one alert per REPEAT window
  if [ "$prev_status" = "$status" ] && [ $((now - prev_alert)) -lt "$REPEAT" ]; then
    log "watchdog: $project $status suppressed: $reason"
    continue
  fi
  notify "watchdog: $project $status: $reason"
  state_set "$project" "$status" "$reason" "$now"
done
