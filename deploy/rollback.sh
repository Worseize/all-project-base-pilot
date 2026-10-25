#!/usr/bin/env bash
# Roll back code to the sha saved before the last deploy.
# Usage: rollback.sh <id>
set -euo pipefail
ID="${1:?project id}"
REPO="/srv/$ID/repo.git"
STATE="/var/lib/proj-base/deploy/$ID.sha"
[ -f "$STATE" ] || { echo "no previous sha: $STATE" >&2; exit 1; }
sha="$(cat "$STATE")"
git -c safe.directory="$REPO" --git-dir="$REPO" cat-file -e "$sha^{commit}" || {
  echo "previous sha missing: $sha" >&2
  exit 1
}
git -c safe.directory="$REPO" --git-dir="$REPO" update-ref refs/heads/main "$sha"
bash "$(dirname "${BASH_SOURCE[0]}")/deploy-project.sh" "$ID"
echo "rolled back: $ID -> $sha"
