#!/bin/zsh
# Wait for the OpenAI API to recover, then run the CoEP gpt-side smoke test:
# build a tool with gpt-5.4-mini and run the three-variant single pass over a
# small slice, so the gpt path is verified end to end before the campaign.
set -u
cd "$(dirname "$0")/.."
LOG=/tmp/gpt_smoke.log

{
  echo "=== waiting for OpenAI ($(date)) ==="
  for i in {1..240}; do            # up to ~4h at 60s
    if python3 - <<'PY'
import sys
from src.experiments._common import load_env
load_env()
from src.utils import llm
try:
    llm.complete("say OK", model="gpt-mini", max_tokens=16, temperature=None)
except Exception as e:
    print(f"still down: {type(e).__name__}")
    sys.exit(1)
sys.exit(0)
PY
    then
      echo "=== OpenAI back after $i probe(s) ($(date)) ==="
      break
    fi
    sleep 60
  done

  echo "--- build refactory_q1 gpt-mini ---"
  python3 run.py build --problem refactory_q1 --model gpt-mini
  echo "--- compare refactory_q1 gpt-mini (60) ---"
  python3 run.py compare --problem refactory_q1 --model gpt-mini --limit 60 --ver smoke
  echo "--- build cf_11B gpt-mini (sparse pool, fallback path) ---"
  python3 run.py build --problem cf_11B --model gpt-mini
  echo "--- compare cf_11B gpt-mini (25) ---"
  python3 run.py compare --problem cf_11B --model gpt-mini --limit 25 --ver smoke
  echo "=== GPT SMOKE DONE ==="
} > "$LOG" 2>&1
