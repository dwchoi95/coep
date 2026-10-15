"""`run.py repair` — repair one submission with a built tool, then fallback.

Local rule search first (zero LLM cost); on abstention, escalate to the LLM
fallback with a strategy-matched reference. Prints the outcome, the rule
provenance, RPS, and the cost of any escalation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.core.fallback import fallback_repair
from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.core.synthesis import load_fixer
from src.experiments._common import (load_env, load_pool, load_problem, tool_path)
from src.utils.metrics import rps


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py repair")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--file", required=True, help="path to a buggy .py submission")
    ap.add_argument("--no-fallback", action="store_true")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = Path(args.file).read_text()
    rules = load_fixer(tool_path(args.problem, args.model))
    correct = load_pool(args.problem, "correct", args.data_root)
    index = ReferenceIndex(correct)

    budget = SearchBudget()
    res = local_repair(buggy, prob, rules, index, budget)
    if res.repaired:
        via = (f"rules {list(res.rules)}" if res.source == "rules"
               else "reference-guided transplant")
        print(f"LOCAL repair ({via})  RPS={rps(buggy, res.patch):.3f}  "
              f"({res.seconds:.2f}s)")
        return 0

    print("tool abstained")
    if args.no_fallback:
        return 0
    fb = fallback_repair(buggy, prob, correct, model=args.model)
    if fb.repaired:
        print(f"FALLBACK repair  RPS={rps(buggy, fb.patch):.3f}  "
              f"cost=${fb.usd:.4f} (in={fb.in_tokens} out={fb.out_tokens})")
    else:
        print(f"FALLBACK failed  cost=${fb.usd:.4f}")
    return 0
