#!/bin/sh
# Release dev's HEAD to main: the same tree minus what only the work on dev
# needs (dev branch only).
#
#   ANON_PATTERNS="name,account,..." ./release.sh "commit message"
#
# Builds the tree in a temporary worktree of main, refuses to commit if any of
# ANON_PATTERNS (kept out of the repo) occurs in it, and commits it on main.
# Pushing is left to you: git push origin main
set -e
cd "$(dirname "$0")"
msg=${1:?usage: ./release.sh "commit message"}

# dev-only: the history of the work, the paper (its own branch via
# `git subtree split --prefix=paper -b paper`), the paper's number checks, and
# this script
EXCLUDE="archive paper release.sh src/experiments/tables.py src/experiments/numbers.py src/experiments/splice.py"

wt=$(mktemp -d)/main
git worktree add -q "$wt" main
trap 'git worktree remove --force "$wt"' EXIT
git -C "$wt" rm -q -r --ignore-unmatch .
git archive HEAD | tar -x -C "$wt"
for p in $EXCLUDE; do rm -rf "${wt:?}/$p"; done

if [ -n "$ANON_PATTERNS" ]; then
    leaks=$(cd "$wt" && grep -rIl -i -E "$(echo "$ANON_PATTERNS" | tr ',' '|')" . | grep -v '^./.git' || true)
    if [ -n "$leaks" ]; then
        echo "refusing to release; identifying strings in:"; echo "$leaks"; exit 1
    fi
fi

git -C "$wt" add -A
git -C "$wt" commit -q -m "$msg"
git -C "$wt" log --oneline -1
