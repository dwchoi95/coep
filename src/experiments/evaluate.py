"""`run.py evaluate` — run a built tool over every buggy program and report.

Local-only by default (RR / mean RPS / ATT / rule-firing profile). With
`--fallback` the abstentions escalate to the LLM (adds InT/OuT/Cost); with
`--learn` each successful fallback is absorbed into a new rule (self-learning),
and coverage-vs-fallbacks is printed so the tool's improvement is visible.
"""
from __future__ import annotations

import argparse
import time

from src.core.fallback import absorb, fallback_repair
from src.core.repair import ProvenanceLog, SearchBudget, repair
from src.core.synthesis import load_fixer
from src.experiments._common import (load_env, load_pool, load_problem, tool_path)
from src.utils.metrics import rps


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py evaluate")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-haiku")
    ap.add_argument("--limit", type=int, default=0, help="0 = all buggy programs")
    ap.add_argument("--fallback", action="store_true", help="escalate abstentions")
    ap.add_argument("--learn", action="store_true", help="absorb fallback fixes")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args(argv)
    if args.fallback or args.learn:
        load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    if args.limit:
        buggy = buggy[:args.limit]
    correct = load_pool(args.problem, "correct", args.data_root)
    fpath = tool_path(args.problem, args.model)

    budget = SearchBudget(max_candidates=400, max_seconds=10, max_combo=2,
                          candidate_timeout=3)
    prov = ProvenanceLog()
    n = local = fb_fixed = absorbed = 0
    rps_sum = seconds = usd = 0.0
    in_tok = out_tok = 0

    for i, src in enumerate(buggy):
        n += 1
        rules = load_fixer(fpath)          # reload: picks up newly-learned rules
        t = time.time()
        res = repair(src, prob, rules, budget)
        if res.repaired:
            local += 1
            prov.record(f"{args.problem}:{i}", res)
            rps_sum += rps(src, res.patch)
            seconds += time.time() - t
            continue
        if not (args.fallback or args.learn):
            seconds += time.time() - t
            continue
        fb = fallback_repair(src, prob, correct, model=args.model)
        seconds += time.time() - t
        in_tok += fb.in_tokens; out_tok += fb.out_tokens; usd += fb.usd
        if fb.repaired:
            fb_fixed += 1
            rps_sum += rps(src, fb.patch)
            if args.learn:
                ab = absorb(fpath, src, fb.patch, prob, model=args.model, budget=budget)
                usd += ab.usd; in_tok += ab.in_tokens; out_tok += ab.out_tokens
                absorbed += int(ab.absorbed)

    repaired = local + fb_fixed
    print(f"=== {args.problem} [{args.model}] on {n} buggy ===")
    print(f"RR = {repaired}/{n} = {repaired/n:.1%}  (local {local}, fallback {fb_fixed})")
    if repaired:
        print(f"mean RPS = {rps_sum/repaired:.3f}   ATT = {seconds/n:.3f}s")
    if args.fallback or args.learn:
        print(f"escalation cost: in={in_tok} out={out_tok} ${usd:.4f}"
              + (f"   rules learned: {absorbed}" if args.learn else ""))
    print("rule-firing profile:")
    for name, cnt in prov.profile():
        print(f"  {cnt:5d}  {name}")
    return 0
