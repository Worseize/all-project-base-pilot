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
if ! [[ "$PROJECT" =~ ^[a-z][a-z0-9-]{0,30}$ ]]; then
  echo "invalid project name: $PROJECT" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/srv/$PROJECT"
REPO="$PROJECT_ROOT/repo.git"
HOOKS="/etc/git-hooks/$PROJECT"
SECRETS="/etc/$PROJECT"
AUTH="$PROJECT_ROOT/.ssh/authorized_keys"

install -d -m 0711 -o root -g root /srv
if ! id -u "$PROJECT" >/dev/null 2>&1; then
  useradd --system --home-dir "$PROJECT_ROOT" --shell /bin/bash --create-home "$PROJECT"
fi
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

install -d -m 0755 -o root -g root "$HOOKS"
install -m 0755 -o root -g root "$SCRIPT_DIR/git/pre-receive" "$HOOKS/pre-receive"

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

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  systemctl enable "proj@$PROJECT.service"
fi

printf 'ready: project=%s user=%s repo=%s hooks=%s\n' \
  "$PROJECT" "$PROJECT" "$REPO" "$HOOKS"
