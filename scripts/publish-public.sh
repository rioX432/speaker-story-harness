#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-rioX432/speaker-story-harness}"
if [[ "$TARGET" != rioX432/* ]]; then
  echo "For safety, this script only creates a repository under rioX432. Received: $TARGET" >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo 'GitHub CLI (gh) is required in your local authenticated environment.' >&2
  exit 1
fi
gh auth status >/dev/null
cd "$(dirname "$0")/.."
if gh repo view "$TARGET" >/dev/null 2>&1; then
  echo "Repository $TARGET already exists; refusing to overwrite." >&2
  exit 1
fi
if [[ ! -d .git ]]; then
  git init -b main
  git add .
  git commit -m "feat: bootstrap story-first presentation harness"
else
  if [[ -n "$(git status --porcelain)" ]]; then
    echo 'Please commit or clean the working tree before publishing.' >&2
    exit 1
  fi
fi
echo "Creating public repository $TARGET."
gh repo create "$TARGET" --public --source . --remote origin --push
