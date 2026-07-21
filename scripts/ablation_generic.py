#!/usr/bin/env python3
"""Ablation: generic-only local repair (no synthesized problem-specific rules,
no LLM). For every evaluation instance, search mutation-inversion candidates
(1 then 2 edits) validated against the visible tests under the same RPS cap
used by COEP repairers. Isolates the contribution of builder-written
problem-specific rules. Writes runs/ablation_generic/results.json."""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.evaluate import rps  # noqa: E402
from coep.repairlib import candidates_generic, first_passing  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
OUT = ROOT / "runs" / "ablation_generic"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    results = []
    for pid, split in sorted(splits.items()):
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        fixed = 0
        for bug in split["eval"]:
            src = (PROBLEMS / pid / "buggy" / bug).read_text()
            t0 = time.monotonic()
            patch = first_passing(candidates_generic(src, max_edits=2, budget=2000),
                                  p["entry"], p["tests"], src,
                                  max_rps=0.35, max_checks=2000)
            rec = {"pid": pid, "bug": bug, "seconds": round(time.monotonic() - t0, 2)}
            if patch is None:
                rec["repaired"] = False
            else:
                v = run_tests(patch, p["entry"], p["tests"])
                rec["repaired"] = bool(v.all_pass)
                rec["rps"] = round(rps(src, patch), 4)
            fixed += rec["repaired"]
            results.append(rec)
        print(f"{pid}: {fixed}/{len(split['eval'])}")
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    n = len(results)
    f = sum(r["repaired"] for r in results)
    print(f"TOTAL generic-only: {f}/{n} = {f/n:.3f}")


if __name__ == "__main__":
    main()
