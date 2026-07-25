#!/bin/zsh
# Calibrate every built tool's escalation threshold. Pure CPU (no LLM calls),
# but it runs the tool over the whole buggy pool, so problems go in parallel
# and each writes its own log.
#
#   ./scripts/calibrate_all.sh [max_parallel]
set -u
cd "$(dirname "$0")/.."
JOBS="${1:-4}"

PIDS=(refactory_q1 refactory_q2 refactory_q3 refactory_q4 refactory_q5 \
      cf_1011B cf_10C cf_110A cf_11B cf_125A cf_131A)

running=0
for pid in $PIDS; do
  PYTHONUNBUFFERED=1 python3 run.py calibrate --problem "$pid" \
      --model claude-sonnet gpt-mini > "/tmp/calib_${pid}.log" 2>&1 &
  (( running++ ))
  if (( running >= JOBS )); then
    wait -n 2>/dev/null || wait
    (( running-- ))
  fi
done
wait
echo "=== CALIBRATION DONE ==="
cat /tmp/calib_*.log
