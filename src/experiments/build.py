"""`run.py build` — synthesize tools/<p_id>/<model>/{fixer.py, cost.json}.

Stage 1 (local, no LLM cost) selects the build samples; Stage 2
calls the builder model. The same selection feeds every model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.core.repair import SearchBudget
from src.core.synthesis import build, select_sample_pairs
from src.experiments._common import load_env, load_pool, load_problem


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py build")
    ap.add_argument("--problem", required=True, help="problem id, e.g. refactory_q1")
    ap.add_argument("--model", default=["claude-sonnet-5", "gpt-5.4-mini"], nargs="+",
                    help="builder model(s)")
    ap.add_argument("--r-max", type=int, default=3)
    ap.add_argument("--data-root", default="benchmark")
    ap.add_argument("--tools-root", default="tools",
                    help="where to write <p_id>/<model>/; use a separate root to "
                         "compare configurations without clobbering the campaign")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    correct = load_pool(args.problem, "correct", args.data_root)

    pairs = select_sample_pairs(buggy, correct)
    samples = [b for b, _f, _n in pairs]
    fixes = [f for _b, f, _n in pairs]
    print(f"{args.problem}: {len(buggy)} buggy, {len(correct)} correct → "
          f"{len(samples)} (buggy→fixed) pairs, one per cluster")

    budget = SearchBudget()
    for model in args.model:
        res = build(prob, samples, model=model, r_max=args.r_max,
                    budget=budget, sample_fixes=fixes,
                    out_path=Path(args.tools_root) / args.problem / model / "fixer.py")
        print(f"  [{model}] rules={res.rules} coverage={res.coverage:.0%} "
              f"rounds={res.rounds} cost=${res.usd:.4f} → {res.path}")
    return 0
