"""`run.py calibrate` — derive a built tool's escalation threshold.

`build` calibrates automatically; this runs the same step against tools that
already exist, so an already-built corpus does not have to be rebuilt (and
paid for again) to acquire a threshold. No LLM calls: it only runs the tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.core.calibrate import calibrate, write_into_cost
from src.core.synthesis import load_fixer
from src.experiments._common import load_pool, load_problem, tool_path


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py calibrate")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default=["claude-sonnet", "gpt-mini"], nargs="+")
    ap.add_argument("--data-root", default="data")
    args = ap.parse_args(argv)

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    stems = [f.stem for f in
             sorted((Path(args.data_root) / args.problem / "buggy").glob("*.py"))]
    correct = load_pool(args.problem, "correct", args.data_root)

    for model in args.model:
        path = tool_path(args.problem, model)
        if not path.exists():
            print(f"  [{model}] no tool at {path}, skipped")
            continue
        rec = calibrate(prob, load_fixer(path), buggy, correct, stems=stems)
        write_into_cost(path, rec)
        tau = rec.get("rps_tau")
        if tau is None:
            print(f"{args.problem} [{model}] gate off: only "
                  f"{rec['calibration_n']} test-passing patches")
        else:
            print(f"{args.problem} [{model}] tau={tau} "
                  f"(median {rec['rps_median']} + {rec['rps_tau_k']}*MAD "
                  f"{rec['rps_mad']}), fires on "
                  f"{100*rec['rps_gate_rate']:.1f}% of {rec['calibration_n']}")
    return 0
