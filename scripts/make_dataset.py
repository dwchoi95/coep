#!/usr/bin/env python3
"""Generate mutation-based buggy programs and the build/eval split.

For each problem: keep the 10 crafted bugs, add mutants generated from the
three reference solutions (seeded, filtered to programs that compile and fail
at least one test), then split into 5 build examples (2 crafted + 3 mutants)
and up to 20 evaluation instances. Deterministic under SEED.
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.mutation import generate_mutants  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
SEED = 7
MUTANTS_PER_PROBLEM = 15


def main():
    rng = random.Random(SEED)
    splits = {}
    for pdir in sorted(PROBLEMS.iterdir()):
        if not pdir.is_dir():
            continue
        p = json.loads((pdir / "problem.json").read_text())
        entry, tests = p["entry"], p["tests"]
        crafted = sorted((pdir / "buggy").glob("crafted_*.py"))
        existing = {f.read_text().strip() for f in crafted}

        # remove any stale mutants from earlier runs
        for f in (pdir / "buggy").glob("mutant_*.py"):
            f.unlink()

        refs = sorted((pdir / "refs").glob("*.py"))
        mutants = []
        per_ref = MUTANTS_PER_PROBLEM // len(refs) + 2
        for ref in refs:
            src = ref.read_text()
            for m in generate_mutants(src, per_ref * 4, rng):
                if len([x for x in mutants if x["ref"] == ref.name]) >= per_ref:
                    break
                if m["source"].strip() in existing:
                    continue
                r = run_tests(m["source"], entry, tests, timeout=4.0)
                if not r.compiled or r.all_pass or r.timeout:
                    continue
                existing.add(m["source"].strip())
                mutants.append({"ref": ref.name, "faults": m["faults"], "source": m["source"]})
        rng.shuffle(mutants)
        mutants = mutants[:MUTANTS_PER_PROBLEM]
        mutant_names = []
        for i, m in enumerate(mutants, 1):
            name = f"mutant_{i:02d}.py"
            (pdir / "buggy" / name).write_text(m["source"] + "\n")
            mutant_names.append(name)

        crafted_names = [f.name for f in crafted]
        rng2 = random.Random(SEED + hash(p["id"]) % 1000)
        build = (rng2.sample(crafted_names, 2) + rng2.sample(mutant_names, 3))
        rest = [n for n in crafted_names + mutant_names if n not in build]
        rng2.shuffle(rest)
        eval_set = sorted(rest[:20])
        splits[p["id"]] = {"build": sorted(build), "eval": eval_set}
        print(f"{p['id']}: {len(crafted_names)} crafted + {len(mutant_names)} mutants "
              f"-> build {len(build)}, eval {len(eval_set)}")

    (ROOT / "benchmark" / "splits.json").write_text(json.dumps(splits, indent=2))
    print("wrote benchmark/splits.json")


if __name__ == "__main__":
    main()
