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
HOOKS="/etc/git-hooks/$PROJECT"
SECRETS="/etc/$PROJECT"
AUTH="$PROJECT_ROOT/.ssh/authorized_keys"
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
  if ! git -c safe.directory="$SOURCE_REPO" -C "$SOURCE_REPO" rev-parse --verify --quiet "$SOURCE_REF" >/dev/null; then
    echo "source repo/ref not found: $SOURCE_REPO $SOURCE_REF" >&2
    exit 1
  fi
  git -c safe.directory="$REPO" -c safe.directory="$SOURCE_REPO" --git-dir="$REPO" fetch "$SOURCE_REPO" "$SOURCE_REF:refs/heads/main"
  chown -R "$PROJECT:$PROJECT" "$REPO"
  echo "seeded main from $SOURCE_REPO ($SOURCE_REF)"
fi

install -d -m 0755 -o root -g root "$HOOKS"
install -m 0755 -o root -g root "$SCRIPT_DIR/git/pre-receive" "$HOOKS/pre-receive"

install -d -m 0770 -o root -g "$PROJECT" /var/log/git
LOG="/var/log/git/$PROJECT.log"
if [ ! -f "$LOG" ]; then
  install -m 0660 -o root -g "$PROJECT" /dev/null "$LOG"
else
  chown root:"$PROJECT" "$LOG"
  chmod 0660 "$LOG"
fi
chown root:"$PROJECT" /var/log/git
chmod 0770 /var/log/git

install -m 0644 -o root -g root "$SCRIPT_DIR/systemd/proj@.service" /etc/systemd/system/proj@.service
sed "s/%i/$PROJECT/g" "$SCRIPT_DIR/logrotate/proj" > "/etc/logrotate.d/proj-$PROJECT"
chmod 0644 "/etc/logrotate.d/proj-$PROJECT"

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
