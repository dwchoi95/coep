"""`run.py build` — synthesize tools/<p_id>/<model>/{fixer.py, cost.json}.

Stage 1 (local, no LLM cost) selects the build samples and references; Stage 2
calls the builder model. The same selection feeds every model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.core.calibrate import calibrate, write_into_cost
from src.core.cluster import cluster
from src.core.repair import SearchBudget
from src.core.synthesis import build, load_fixer, select_sample_pairs
from src.experiments._common import load_env, load_pool, load_problem


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py build")
    ap.add_argument("--problem", required=True, help="problem id, e.g. refactory_q1")
    ap.add_argument("--model", default=["claude-sonnet", "gpt-mini"], nargs="+",
                    help="builder model(s)")
    ap.add_argument("--n-samples", type=int, default=0,
                    help="0 = one per structural cluster, uncapped")
    ap.add_argument("--n-refs", type=int, default=2)
    ap.add_argument("--r-max", type=int, default=3)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--no-calibrate", action="store_true",
                    help="skip the build-time escalation-threshold calibration")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    stems = [f.stem for f in
             sorted((Path(args.data_root) / args.problem / "buggy").glob("*.py"))]
    correct = load_pool(args.problem, "correct", args.data_root)

    pairs = select_sample_pairs(buggy, correct, n_samples=args.n_samples)
    samples = [b for b, _f in pairs]
    fixes = [f for _b, f in pairs]
    refs = [correct[c.medoid] for c in cluster(correct)[0][:args.n_refs]]
    print(f"{args.problem}: {len(buggy)} buggy, {len(correct)} correct → "
          f"{len(samples)} (buggy→fixed) pairs, {len(refs)} refs")

    budget = SearchBudget(max_candidates=400, max_seconds=10, max_combo=2,
                          candidate_timeout=3)
    for model in args.model:
        res = build(prob, refs, samples, model=model, r_max=args.r_max,
                    budget=budget, sample_fixes=fixes)
        print(f"  [{model}] rules={res.rules} coverage={res.coverage:.0%} "
              f"rounds={res.rounds} cost=${res.usd:.4f} → {res.path}")
        if res.path and not args.no_calibrate:
            rec = calibrate(prob, load_fixer(res.path), buggy, correct,
                            stems=stems)
            write_into_cost(res.path, rec)
            tau = rec.get("rps_tau")
            print(f"  [{model}] escalation threshold "
                  + (f"tau={tau} (median {rec.get('rps_median')} + "
                     f"{rec['rps_tau_k']}*MAD {rec.get('rps_mad')}), "
                     f"fires on {100*rec['rps_gate_rate']:.1f}% of "
                     f"{rec['calibration_n']} calibration patches"
                     if tau is not None else
                     f"off ({rec['calibration_n']} test-passing patches, "
                     f"too few to calibrate)"))
    return 0
