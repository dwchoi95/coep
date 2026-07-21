#!/usr/bin/env python3
"""Generate PyDex-style per-instance repair prompts (few-shot + execution
feedback; Joshi et al., AAAI 2024) for every evaluation instance.

Few-shot pairs are REAL (buggy, fixed) pairs by the same student, taken from
the 5 build-split submissions of each assignment — i.e. exactly the same
information budget the CoEP builder receives. Execution feedback is the
buggy program's failing tests under the shared harness.

Requires the original Refactory dataset at /workspace/refactory (to look up
each build-split student's own later correct submission).
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.prompts import pydex_repair_prompt  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
OUT = ROOT / "runs" / "pydex"
REFDATA = pathlib.Path("/workspace/refactory/data")


def fewshot_pairs(pid: str, split: dict, tests, entry) -> list[tuple[str, str]]:
    """Real (buggy, fixed-by-the-same-student) pairs. Primary source: the 5
    build-split submissions. If a build student's own fix does not pass the
    parsed suite, pad (deterministically) with same-student pairs drawn from
    submissions in NEITHER the build nor the eval split."""
    import random
    qname = pid.replace("refactory_q", "question_")
    qdir = REFDATA / qname / "code"
    wrong_sorted = sorted((qdir / "wrong").glob("*.py"))

    def pair_of(idx: int):
        wfile = wrong_sorted[idx - 1]
        cfile = qdir / "correct" / wfile.name.replace("wrong_", "correct_")
        if not cfile.exists():
            return None
        fix = cfile.read_text()
        if not run_tests(fix, entry, tests).all_pass:
            return None
        return (wfile.read_text(), fix)

    used = set(split["build"]) | set(split["eval"])
    pairs = []
    for ours in split["build"]:
        pr = pair_of(int(re.match(r"real_(\d+)\.py", ours).group(1)))
        if pr:
            pairs.append(pr)
    spare = [i for i in range(1, len(wrong_sorted) + 1)
             if f"real_{i:03d}.py" not in used]
    random.Random(7).shuffle(spare)
    for idx in spare:
        if len(pairs) >= 5:
            break
        pr = pair_of(idx)
        if pr:
            pairs.append(pr)
    return pairs


def main():
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    (OUT / "prompts").mkdir(parents=True, exist_ok=True)
    (OUT / "responses").mkdir(parents=True, exist_ok=True)
    manifest = []
    for pid, split in sorted(splits.items()):
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        pairs = fewshot_pairs(pid, split, p["tests"], p["entry"])
        print(f"{pid}: {len(pairs)} few-shot (buggy, fixed) pairs")
        for name in split["eval"]:
            src = (PROBLEMS / pid / "buggy" / name).read_text()
            failures = run_tests(src, p["entry"], p["tests"]).failures
            key = f"{pid}__{name[:-3]}"
            (OUT / "prompts" / f"{key}.md").write_text(
                pydex_repair_prompt(p, src, pairs, failures))
            manifest.append({"key": key, "pid": pid, "bug": name})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    # batches of 10 for the response-collection agents
    keys = [m["key"] for m in manifest]
    for b in range(0, len(keys), 10):
        (OUT / f"batch_{b // 10:02d}.txt").write_text("\n".join(keys[b:b + 10]) + "\n")
    print(f"wrote {len(manifest)} prompts and {(len(keys) + 9) // 10} batches to {OUT}")


if __name__ == "__main__":
    main()
