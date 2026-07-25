#!/bin/zsh
# Build the per-assignment tools for the campaign, skipping any that already
# exist, so the script is safe to re-run after an interruption or an outage.
#
#   ./scripts/build_tools.sh <model> [logfile]
set -u
cd "$(dirname "$0")/.."
MODEL="${1:?usage: build_tools.sh <model> [logfile]}"
LOG="${2:-/tmp/build_${MODEL}.log}"

PIDS=(refactory_q1 refactory_q2 refactory_q3 refactory_q4 refactory_q5 \
      cf_1011B cf_10C cf_110A cf_11B cf_125A cf_131A)

{
  echo "=== build $MODEL ($(date)) ==="
  for pid in $PIDS; do
    if [[ -f "tools/$pid/$MODEL/fixer.py" ]]; then
      echo "--- skip $pid (tools/$pid/$MODEL/fixer.py exists)"
    else
      echo "--- build $pid $MODEL ---"
      PYTHONUNBUFFERED=1 python3 run.py build --problem "$pid" --model "$MODEL"
    fi
  done
  echo "=== build $MODEL DONE ($(date)) ==="
} >> "$LOG" 2>&1
