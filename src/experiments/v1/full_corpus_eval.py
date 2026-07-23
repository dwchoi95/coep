#!/usr/bin/env python3
"""Evaluate zero-marginal-cost arms on the FULL imported corpus (every
compiled-and-failing submission except the 5 build samples per assignment),
not just the 40-per-assignment evaluation subsample.

Arms: the frozen CoEP repairers (repairer.py) and, optionally, the
generic-only search. Writes runs/full_corpus/<arm>/<pid>.json and prints
per-assignment and pooled rates with Wilson CIs.

  python3 scripts/full_corpus_eval.py coep
  python3 scripts/full_corpus_eval.py generic
"""
import json
import pathlib
import sys
import time

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep.evaluate import rps  # noqa: E402
from coep.repairlib import candidates_generic, first_passing  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
MAX_RPS = 0.35


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (100 * (c - h), 100 * (c + h))


def eval_coep(pid, bugs):
    import subprocess
    results = []
    for b in bugs:
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        buggy = (PROBLEMS / pid / "buggy" / b).read_text()
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_repairer_one.py"), pid, b],
                capture_output=True, text=True, timeout=60,
                env={**__import__("os").environ, "COEP_REPAIRER": "repairer.py"})
            out = json.loads(proc.stdout.strip().splitlines()[-1])
            patched = out.get("patched")
        except Exception:
            patched = None
        ok = False
        if patched:
            v = run_tests(patched, p["entry"], p["tests"])
            ok = v.all_pass and rps(buggy, patched) <= MAX_RPS
        results.append({"bug": b, "repaired": bool(ok)})
    return results


def eval_generic(pid, bugs):
    p = json.loads((PROBLEMS / pid / "problem.json").read_text())
    results = []
    for b in bugs:
        src = (PROBLEMS / pid / "buggy" / b).read_text()
        t0 = time.time()
        cand = first_passing(candidates_generic(src, max_edits=2, budget=4000),
                             p["entry"], p["tests"], src, max_rps=MAX_RPS,
                             max_checks=800)
        results.append({"bug": b, "repaired": bool(cand),
                        "seconds": round(time.time() - t0, 2)})
    return results


def main():
    arm = sys.argv[1]
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    outdir = ROOT / "runs" / "full_corpus" / arm
    outdir.mkdir(parents=True, exist_ok=True)
    tot_ok = tot_n = 0
    for pid, split in sorted(splits.items()):
        build = set(split["build"])
        bugs = sorted(f.name for f in (PROBLEMS / pid / "buggy").glob("*.py")
                      if f.name not in build)
        res = (eval_coep if arm == "coep" else eval_generic)(pid, bugs)
        (outdir / f"{pid}.json").write_text(json.dumps(res, indent=2))
        ok = sum(r["repaired"] for r in res)
        lo, hi = wilson(ok, len(res))
        print(f"{pid}: {ok}/{len(res)} = {ok/len(res)*100:.1f}% [{lo:.1f}, {hi:.1f}]",
              flush=True)
        tot_ok += ok
        tot_n += len(res)
    lo, hi = wilson(tot_ok, tot_n)
    print(f"TOTAL {arm}: {tot_ok}/{tot_n} = {tot_ok/tot_n*100:.1f}% [{lo:.1f}, {hi:.1f}]")


if __name__ == "__main__":
    main()
