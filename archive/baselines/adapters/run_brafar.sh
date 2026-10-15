#!/bin/sh
# Run BRAFAR on all 11 assignments in parallel. CS1 keeps the tool's own
# 0.01 s per-test budget; Codeforces gets our oracle's 2 s (see fault_locator.py).
cd "$(dirname "$0")/../brafar"
for q in 1 2 3 4 5; do
  .venv/bin/python run.py -d data -q question_$q -s 100 > logs/question_$q.log 2>&1 &
done
for p in cf_110A cf_131A cf_1011B cf_125A cf_11B cf_10C; do
  BRAFAR_TC_TIMEOUT=2 .venv/bin/python run.py -d data_cf -q $p -s 100 > logs/$p.log 2>&1 &
done
wait
echo ALL DONE
