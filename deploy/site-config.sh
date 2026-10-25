#!/usr/bin/env bash
# Generate the node-owned Caddy block from project.conf (root).
# Usage: site-config.sh <project> <workdir>
set -euo pipefail
PROJECT="${1:?project}"
WORK="${2:?workdir}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_PY="$SCRIPT_DIR/manifest.py"
CONF="$WORK/project.conf"
DIR="/etc/caddy/conf.d"
FILE="$DIR/$PROJECT.caddy"
mkdir -p "$DIR"

get() { python3 "$MANIFEST_PY" get "$CONF" "$1" 2>/dev/null || true; }
site="$(get site)"
[ -n "$site" ] || site="none"
if [ "$site" = "none" ]; then
  rm -f "$FILE"
  exit 0
fi
domains="$(get domains)"
redirects="$(get redirects)"
port="$(get port)"
{
  IFS=',' read -ra names <<< "${domains:-$PROJECT}"
  for name in "${names[@]}"; do
    name="$(printf '%s' "$name" | tr -d ' ')"
    [ -n "$name" ] || continue
    printf '%s {\n' "$name"
    if [ "$site" = "static" ]; then
      printf '  root * %s\n  file_server\n' "$WORK"
    else
      printf '  reverse_proxy 127.0.0.1:%s\n' "${port:-8080}"
    fi
    if [ -n "$redirects" ]; then
      IFS=',' read -ra rules <<< "$redirects"
      for rule in "${rules[@]}"; do
        from="${rule%%>*}"
        to="${rule#*>}"
        [ "$from" != "$to" ] && printf '  redir %s %s permanent\n' "$from" "$to"
      done
    fi
    printf '}\n'
  done
} > "$FILE"
chmod 0644 "$FILE"
