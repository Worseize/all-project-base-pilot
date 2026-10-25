#!/usr/bin/env bash
# Idempotent onboarding for one isolated project.
# Usage: sudo [AGENT_PUBKEY="ssh-ed25519 ... agent"] deploy/bootstrap-project.sh proj-a
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
if ! [[ "$PROJECT" =~ ^[a-z][a-z0-9-]{2,19}$ ]]; then
  echo "invalid project id: $PROJECT" >&2
  exit 2
fi
if [[ "$PROJECT" == *--* || "$PROJECT" == *- ]]; then
  echo "invalid project id (double/trailing dash): $PROJECT" >&2
  exit 2
fi
case " root app caddy watchdog admin system debian ubuntu nobody daemon bin sys mail www git ssh " in
  *" $PROJECT "*) echo "reserved project id: $PROJECT" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/srv/$PROJECT"
REPO="$PROJECT_ROOT/repo.git"
WORK="$PROJECT_ROOT/current"
HOOKS="/etc/git-hooks/$PROJECT"
SECRETS="/etc/$PROJECT"
AUTH="$PROJECT_ROOT/.ssh/authorized_keys"
PROJECTS_FILE="${PROJECTS_FILE:-$SOURCE_REPO/projects.json}"
ALLOWED_FILE="$HOOKS/allowed-paths"
PROTECTED_FILE="$HOOKS/protected-paths"
SOURCE_REPO="${SOURCE_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
SOURCE_REF="${SOURCE_REF:-HEAD}"
GIT_SHELL="$(command -v git-shell || true)"
[ -n "$GIT_SHELL" ] || GIT_SHELL="/usr/bin/git-shell"
USER_EXISTED=0
if id -u "$PROJECT" >/dev/null 2>&1; then
  USER_EXISTED=1
  if [ ! -f "$PROJECT_ROOT/CANARY" ] || [ "$(cat "$PROJECT_ROOT/CANARY")" != "$PROJECT" ]; then
    echo "user $PROJECT already exists and is not this project" >&2
    exit 1
  fi
fi

install -d -m 0711 -o root -g root /srv
if [ "$USER_EXISTED" -eq 0 ]; then
  useradd --system --home-dir "$PROJECT_ROOT" --shell "$GIT_SHELL" --create-home "$PROJECT"
fi
usermod --shell "$GIT_SHELL" "$PROJECT"
install -d -m 0750 -o "$PROJECT" -g "$PROJECT" "/var/lib/$PROJECT"
install -d -m 0750 -o "$PROJECT" -g "$PROJECT" "$PROJECT_ROOT"
install -d -m 0700 -o "$PROJECT" -g "$PROJECT" "$PROJECT_ROOT/.ssh"

if [ ! -f "$PROJECT_ROOT/CANARY" ]; then
  printf '%s\n' "$PROJECT" > "$PROJECT_ROOT/CANARY"
fi
chown "$PROJECT:$PROJECT" "$PROJECT_ROOT/CANARY"
chmod 0640 "$PROJECT_ROOT/CANARY"

if [ ! -d "$REPO" ]; then
  git init --bare "$REPO"
fi
chown -R "$PROJECT:$PROJECT" "$REPO"
git -c safe.directory="$REPO" --git-dir="$REPO" config core.hooksPath "$HOOKS"
git -c safe.directory="$REPO" --git-dir="$REPO" config receive.denyDeletes true
git -c safe.directory="$REPO" --git-dir="$REPO" config receive.denyNonFastForwards true
git -c safe.directory="$REPO" --git-dir="$REPO" symbolic-ref HEAD refs/heads/main

if ! git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse --verify --quiet refs/heads/main >/dev/null; then
  if [ "$(git -c safe.directory="$SOURCE_REPO" -C "$SOURCE_REPO" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
    echo "SOURCE_REPO is shallow; fetch full history or set SOURCE_REPO" >&2
    exit 1
  fi
  if ! git -c safe.directory="$SOURCE_REPO" -C "$SOURCE_REPO" rev-parse --verify --quiet "$SOURCE_REF" >/dev/null; then
    echo "source repo/ref not found: $SOURCE_REPO $SOURCE_REF" >&2
    exit 1
  fi
  git -c safe.directory="$REPO" -c safe.directory="$SOURCE_REPO" --git-dir="$REPO" fetch "$SOURCE_REPO" "$SOURCE_REF:refs/heads/main"
  if ! git -c safe.directory="$REPO" --git-dir="$REPO" rev-parse --verify --quiet refs/heads/main >/dev/null; then
    echo "main was not seeded from $SOURCE_REPO ($SOURCE_REF)" >&2
    exit 1
  fi
  chown -R "$PROJECT:$PROJECT" "$REPO"
  echo "seeded main from $SOURCE_REPO ($SOURCE_REF)"
fi
git -c safe.directory="$REPO" --git-dir="$REPO" symbolic-ref HEAD refs/heads/main

install -d -m 0755 -o root -g root "$HOOKS"
install -m 0755 -o root -g root "$SCRIPT_DIR/git/pre-receive" "$HOOKS/pre-receive"
install -m 0755 -o root -g root "$SCRIPT_DIR/git/post-receive" "$HOOKS/post-receive"
allowed="${ALLOWED_PATHS:-*}"
if [ -f "$PROJECTS_FILE" ]; then
  allowed="$(python3 - "$PROJECTS_FILE" "$PROJECT" 2>/dev/null <<'PY' || true
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    item = json.load(handle).get("projects", {}).get(sys.argv[2], {})
for path in item.get("allowed_paths", []):
    print(path)
PY
)"
  [ -n "$allowed" ] || allowed="${ALLOWED_PATHS:-*}"
fi
printf '%s\n' "$allowed" > "$ALLOWED_FILE"
chown root:root "$ALLOWED_FILE"
chmod 0644 "$ALLOWED_FILE"

if git -c safe.directory="$REPO" --git-dir="$REPO" cat-file -e refs/heads/main:test.sh 2>/dev/null; then
  : > "$PROTECTED_FILE"
else
  cat > "$PROTECTED_FILE" <<'EOF'
verify.py
project.json
go.mod
go.sum
tests/
cmd/
deploy/
.github/
.gitlab-ci.yml
azure-pipelines.yml
EOF
fi
chown root:root "$PROTECTED_FILE"
chmod 0644 "$PROTECTED_FILE"

install -d -m 0755 -o root -g root /var/log/git
chown root:root /var/log/git
chmod 0755 /var/log/git
LOG="/var/log/git/$PROJECT.log"
if [ ! -f "$LOG" ]; then
  install -m 0660 -o root -g "$PROJECT" /dev/null "$LOG"
else
  chown root:"$PROJECT" "$LOG"
  chmod 0660 "$LOG"
fi
if command -v runuser >/dev/null 2>&1 && ! runuser -u "$PROJECT" -- test -w "$LOG"; then
  echo "$PROJECT cannot write $LOG" >&2
  exit 1
fi

if ! command -v runuser >/dev/null 2>&1; then
  echo "runuser is required" >&2
  exit 1
fi
if [ ! -d "$WORK/.git" ]; then
  if [ -e "$WORK" ]; then
    echo "working directory exists but is not a git checkout: $WORK" >&2
    exit 1
  fi
  runuser -u "$PROJECT" -- git clone "$REPO" "$WORK"
fi
chown -R "$PROJECT:$PROJECT" "$WORK"
runuser -u "$PROJECT" -- git -C "$WORK" fetch origin main
runuser -u "$PROJECT" -- git -C "$WORK" checkout -B main FETCH_HEAD
runuser -u "$PROJECT" -- git -C "$WORK" reset --hard FETCH_HEAD
chown -R "$PROJECT:$PROJECT" "$WORK"

install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj@.service" /etc/systemd/system/proj@.service

install -d -m 0750 -o root -g "$PROJECT" "$SECRETS"
if [ ! -f "$SECRETS/app.env" ]; then
  install -m 0640 -o root -g "$PROJECT" /dev/null "$SECRETS/app.env"
fi

if [ -n "${AGENT_PUBKEY:-}" ]; then
  if [ ! -f "$AUTH" ]; then
    install -m 0600 -o "$PROJECT" -g "$PROJECT" /dev/null "$AUTH"
  fi
  if ! grep -qF "$AGENT_PUBKEY" "$AUTH"; then
    printf 'command="git-receive-pack '\''%s'\''",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding %s\n' \
      "$REPO" "$AGENT_PUBKEY" >> "$AUTH"
  fi
  chown "$PROJECT:$PROJECT" "$AUTH"
  chmod 0600 "$AUTH"
else
  echo "AGENT_PUBKEY not set; add the agent key later" >&2
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
  systemctl daemon-reload || true
  systemctl enable "proj@$PROJECT.service" || true
fi

printf 'ready: project=%s user=%s repo=%s hooks=%s\n' \
  "$PROJECT" "$PROJECT" "$REPO" "$HOOKS"
echo "next: review push is allowed; main is seeded from $SOURCE_REPO" >&2
