# BRAFAR and MENTORED on the CoEP benchmark

Setup and dataset rebuild: see the docstring of `prepare.py`. Then
`sh run_brafar.sh`, `sh run_mentored.sh`, and
`python3 run.py collect-afg brafar` / `collect-afg mentored` from the repo root.

What the adapter patches change, and nothing else:

- **BRAFAR** (`brafar.patch`): the per-test budget, hard-coded at 0.01 s, reads
  `BRAFAR_TC_TIMEOUT` (default 0.01; C1-C6 run at 2 s, our oracle's budget, since
  0.01 s times out correct Codeforces programs); one submission that crashes the
  searcher or the repairer is reported unrepaired instead of aborting the run.
- **MENTORED** (`mentored.patch`): stdin programs get a real text stream shared by
  `input()`, `sys.stdin` and `sys.stdin.buffer` (the original `input()` returned
  each line with its newline), output is compared whitespace-normalized, and
  `exit()` ends the program normally.

Both tools search and validate with their own harness; `collect-afg` counts a
repair only if the program also passes our oracle, and re-measures RPS on the
student's original program. R1-R5 use each tool's authors' shipped run.
