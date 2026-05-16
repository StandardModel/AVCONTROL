#!/bin/zsh
set -euo pipefail

cd /Users/roncompton/AVCONTROL

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "No origin remote configured yet."
  exit 0
fi

git add -A

if ! git diff --cached --quiet; then
  git commit -m "Auto-sync AVCONTROL $(date '+%Y-%m-%d %H:%M:%S')"
fi

branch="$(git branch --show-current)"

git pull --rebase --autostash origin "$branch"
git push origin "$branch"
