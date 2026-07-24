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
from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import ProvenanceLog, SearchBudget
from src.core.synthesis import load_fixer
from src.experiments._common import (load_env, load_pool, load_problem, tool_path)
from src.utils.metrics import rps


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py evaluate")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-sonnet")
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

    budget = SearchBudget(max_candidates=150, max_combo=2, candidate_timeout=3)
    index = ReferenceIndex(correct)        # correct pool prepared once
    prov = ProvenanceLog()
    n = noop = by_rules = by_ref = fb_fixed = absorbed = 0
    rps_sum = seconds = usd = 0.0
    in_tok = out_tok = 0

    rules = load_fixer(fpath)              # loaded once; reloaded only when learning
    for i, src in enumerate(buggy):
        n += 1
        if args.learn:
            rules = load_fixer(fpath)      # pick up rules learned this run
        t = time.time()
        res = local_repair(src, prob, rules, index, budget)
        if res.source == "noop":           # already passes: not a buggy program
            noop += 1
            continue
        if res.repaired:
            rps_sum += rps(src, res.patch)
            seconds += time.time() - t
            if res.source == "rules":
                by_rules += 1
                prov.record(f"{args.problem}:{i}",
                            type("R", (), {"rules": res.rules})())
            elif res.source == "reference":
                by_ref += 1
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

    local = by_rules + by_ref
    repaired = local + fb_fixed
    buggy_n = n - noop                      # exclude already-passing programs
    print(f"=== {args.problem} [{args.model}] on {n} programs ({buggy_n} buggy, {noop} noop) ===")
    print(f"RR = {repaired}/{buggy_n} = {repaired/max(1,buggy_n):.2%}  "
          f"(local {local} = rules {by_rules} + reference {by_ref}, fallback {fb_fixed})")
    if repaired:
        print(f"mean RPS = {rps_sum/repaired:.3f}   ATT = {seconds/max(1,buggy_n):.3f}s")
    if args.fallback or args.learn:
        print(f"escalation cost: in={in_tok} out={out_tok} ${usd:.4f}"
              + (f"   rules learned: {absorbed}" if args.learn else ""))
    print("rule-firing profile:")
    for name, cnt in prov.profile():
        print(f"  {cnt:5d}  {name}")
    return 0
