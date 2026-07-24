"""`run.py build` — synthesize tools/<p_id>/<model>/{fixer.py, cost.json}.

Stage 1 (local, no LLM cost) selects the build samples and references; Stage 2
calls the builder model. The same selection feeds every model.
"""
from __future__ import annotations

import argparse

from src.core.cluster import cluster
from src.core.repair import SearchBudget
from src.core.synthesis import build, select_samples
from src.experiments._common import load_env, load_pool, load_problem


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py build")
    ap.add_argument("--problem", required=True, help="problem id, e.g. refactory_q1")
    ap.add_argument("--model", default=["claude-haiku", "gpt-nano"], nargs="+",
                    help="builder model(s)")
    ap.add_argument("--n-samples", type=int, default=6)
    ap.add_argument("--n-refs", type=int, default=2)
    ap.add_argument("--r-max", type=int, default=3)
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    correct = load_pool(args.problem, "correct", args.data_root)

    samples = select_samples(buggy, correct, n_samples=args.n_samples)
    refs = [correct[c.medoid] for c in cluster(correct)[0][:args.n_refs]]
    print(f"{args.problem}: {len(buggy)} buggy, {len(correct)} correct → "
          f"{len(samples)} samples, {len(refs)} refs")

    budget = SearchBudget(max_candidates=400, max_seconds=10, max_combo=2,
                          candidate_timeout=3)
    for model in args.model:
        res = build(prob, refs, samples, model=model, r_max=args.r_max, budget=budget)
        print(f"  [{model}] rules={res.rules} coverage={res.coverage:.0%} "
              f"rounds={res.rounds} cost=${res.usd:.4f} → {res.path}")
    return 0
