#!/bin/sh
# Run MENTORED (with correct programs, 30 generations, one trial) on the CoEP
# benchmark. problem_1..5 = R1..R5 (the tool's own datasets, 1 s per test);
# problem_6..11 = C1..C6 (built from our data, 2 s per test = our oracle).
cd "$(dirname "$0")/../mentored"
for i in 1 2 3 4 5; do
  .venv/bin/python run.py -d data_coep/problem_$i -c -g 30 -e 1 -t 1 > logs/problem_$i.log 2>&1 &
done
for i in 6 7 8 9 10 11; do
  .venv/bin/python run.py -d data_coep/problem_$i -c -g 30 -e 1 -t 2 > logs/problem_$i.log 2>&1 &
done
wait
echo ALL DONE
