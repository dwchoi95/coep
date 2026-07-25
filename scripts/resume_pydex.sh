#!/bin/zsh
# Resume the PyDex campaign: runs only the (problem, model) cells whose
# results are missing, so it is safe to re-run after any interruption.
#
#   ./scripts/resume_pydex.sh [logfile]
#
# Each cell writes results/v2/<pid>/{pydex.csv,pydex_pc.csv} and upserts two
# summary rows, so a completed cell is detected by its summary row and skipped.
set -u
cd "$(dirname "$0")/.."
LOG="${1:-/tmp/pydex_resume.log}"

PIDS=(refactory_q1 refactory_q2 refactory_q3 refactory_q4 refactory_q5 \
      cf_1011B cf_10C cf_110A cf_11B cf_125A cf_131A)
MODELS=(claude-sonnet gpt-mini)

{
  echo "=== PyDex resume $(date) ==="
  for model in $MODELS; do
    for pid in $PIDS; do
      if python3 - "$pid" "$model" <<'PY'
import sys, pandas as pd, pathlib
pid, model = sys.argv[1], sys.argv[2]
label = {"claude-sonnet": "claude-sonnet-5", "gpt-mini": "gpt-5.4-mini"}[model]
p = pathlib.Path(f"results/{'v2'}/{pid}/summary.csv")
if not p.exists():
    sys.exit(1)
s = pd.read_csv(p)
hit = s[(s.Approach == "PyDex") & (s.Model == label) & (s.N > 5)]
sys.exit(0 if len(hit) else 1)
PY
      then
        echo "--- skip $pid $model (already recorded)"
      else
        echo "--- pydex $pid $model ---"
        PYTHONUNBUFFERED=1 python3 run.py pydex --problem "$pid" --model "$model" --k 10
      fi
    done
  done
  echo "=== PyDex resume DONE; finalizing ==="
  python3 -m src.experiments.refactory_published
} >> "$LOG" 2>&1
echo "resume finished; log -> $LOG"
