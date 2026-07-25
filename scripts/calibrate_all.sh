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

# `wait -n` is not portable across zsh builds, and falling back to a bare
# `wait` reaps every job while the counter only drops by one, which silently
# serializes the rest of the run. Throttle on the live job count instead.
for pid in $PIDS; do
  while (( $(jobs -r | wc -l) >= JOBS )); do sleep 5; done
  PYTHONUNBUFFERED=1 python3 run.py calibrate --problem "$pid" \
      --model claude-sonnet gpt-mini > "/tmp/calib_${pid}.log" 2>&1 &
done
wait
echo "=== CALIBRATION DONE ==="
cat /tmp/calib_*.log
