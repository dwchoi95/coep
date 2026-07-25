#!/bin/zsh
# Run the CoEP campaign: one pass per (problem, model) recording all three
# variants. Cells already present in summary.csv are skipped, so the script is
# safe to re-run after an interruption.
#
#   ./scripts/run_coep.sh <model> [logfile] [extra args...]
#
# Extra args are forwarded to `run.py compare` (e.g. --subset data/smoke_set.json).
set -u
cd "$(dirname "$0")/.."
MODEL="${1:?usage: run_coep.sh <model> [logfile] [extra args...]}"
LOG="${2:-/tmp/coep_${MODEL}.log}"
shift 2 2>/dev/null || shift 1

PIDS=(refactory_q1 refactory_q2 refactory_q3 refactory_q4 refactory_q5 \
      cf_1011B cf_10C cf_110A cf_11B cf_125A cf_131A)

{
  echo "=== CoEP campaign $MODEL ($(date)) ==="
  for pid in $PIDS; do
    if [[ ! -f "tools/$pid/$MODEL/fixer.py" ]]; then
      echo "--- SKIP $pid: no tool built for $MODEL"
      continue
    fi
    if python3 - "$pid" "$MODEL" <<'PY'
import sys, pathlib, pandas as pd
from src.experiments.compare import MODEL_LABEL
pid, model = sys.argv[1], sys.argv[2]
p = pathlib.Path(f"results/v2/{pid}/summary.csv")
if not p.exists():
    sys.exit(1)
s = pd.read_csv(p)
label = MODEL_LABEL.get(model, model)
hit = s[(s.Approach == "CoEP_LF") & (s.Model == label) & (s.N > 5)]
sys.exit(0 if len(hit) else 1)
PY
    then
      echo "--- skip $pid $MODEL (already recorded)"
    else
      echo "--- coep $pid $MODEL ---"
      PYTHONUNBUFFERED=1 python3 run.py compare --problem "$pid" --model "$MODEL" "$@"
    fi
  done
  echo "=== CoEP campaign $MODEL DONE ($(date)) ==="
} >> "$LOG" 2>&1
