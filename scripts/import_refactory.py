#!/usr/bin/env python3
"""Import the Refactory dataset (real student submissions; Hu et al., ASE 2019)
into this repo's benchmark format, enabling the real-student-data experiment.

Usage:
    git clone https://github.com/githubhuyang/refactory  # outside this repo
    python3 scripts/import_refactory.py /path/to/refactory/data

Expected dataset layout (per the Refactory replication package):
    data/question_N/
        ans/  input_x.txt / output_x.txt   (test cases)
        code/reference/reference.py        (instructor reference)
        code/correct/*.py                  (correct student submissions)
        code/wrong/*.py                    (buggy student submissions)

For each question this script creates benchmark/problems/refactory_qN/ with
problem.json (entry function inferred from the reference; tests parsed from
ans/ via literal_eval), refs/ (reference + 2 sampled correct submissions), and
buggy/real_XXX.py (all buggy submissions). It then re-validates everything
with the standard harness and emits a build/eval split (5 build / rest eval,
seeded), after which the ordinary pipeline applies unchanged:

    python3 scripts/validate_benchmark.py refactory_q1 ...
    python3 scripts/gen_baseline_prompts.py
    python3 scripts/coep_build.py prompt refactory_q1
    ...

NOTE: written against the documented dataset layout; the dataset could not be
downloaded in the authoring environment (network policy), so run the built-in
sanity checks (--dry-run first) and expect to adjust parsing details once real
data is present. Test semantics: Refactory questions are function-based; each
input_x.txt holds a Python expression `f(args)` or bare args and output_x.txt
the expected value. We parse both with ast.literal_eval where possible and
skip tests we cannot parse (reported).
"""
import ast
import json
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.sandbox import run_tests  # noqa: E402

SEED = 7


def entry_of(reference_src: str) -> str:
    m = re.search(r"^def\s+(\w+)\s*\(", reference_src, re.M)
    if not m:
        raise ValueError("no top-level def in reference")
    return m.group(1)


def parse_tests(ansdir: pathlib.Path, entry: str) -> tuple[list[dict], int]:
    tests, skipped = [], 0
    for inp in sorted(ansdir.glob("input_*.txt")):
        out = ansdir / inp.name.replace("input", "output")
        if not out.exists():
            skipped += 1
            continue
        raw_in = inp.read_text().strip()
        raw_out = out.read_text().strip()
        try:
            call = raw_in
            m = re.match(rf"{entry}\s*\((.*)\)\s*$", raw_in, re.S)
            if m:
                call = m.group(1)
            args = ast.literal_eval(f"({call},)") if call else ()
            expected = ast.literal_eval(raw_out)
            tests.append({"args": list(args), "expected": expected})
        except (ValueError, SyntaxError):
            skipped += 1
    return tests, skipped


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dry = "--dry-run" in sys.argv
    data = pathlib.Path(sys.argv[1])
    rng = random.Random(SEED)
    splits_path = ROOT / "benchmark" / "splits.json"
    splits = json.loads(splits_path.read_text()) if splits_path.exists() else {}

    for qdir in sorted(data.glob("question_*")):
        pid = f"refactory_{qdir.name.replace('question_', 'q')}"
        ref_file = qdir / "code" / "reference" / "reference.py"
        if not ref_file.exists():
            print(f"[skip] {qdir.name}: no reference.py")
            continue
        ref_src = ref_file.read_text()
        entry = entry_of(ref_src)
        tests, skipped = parse_tests(qdir / "ans", entry)
        r = run_tests(ref_src, entry, tests)
        print(f"{pid}: entry={entry} tests={len(tests)} (skipped {skipped}) "
              f"reference passes {r.passed}/{r.total}")
        if not tests or not r.all_pass:
            print(f"[skip] {pid}: reference does not pass parsed tests — "
                  "inspect ans/ parsing for this question")
            continue
        if dry:
            continue

        pdir = ROOT / "benchmark" / "problems" / pid
        (pdir / "refs").mkdir(parents=True, exist_ok=True)
        (pdir / "buggy").mkdir(exist_ok=True)
        desc = (f"(Imported from the Refactory dataset, {qdir.name}.) Implement "
                f"the function `{entry}` so that it passes the instructor test "
                f"suite below. See Hu et al., ASE 2019 for the original "
                f"assignment handouts.")
        (pdir / "problem.json").write_text(json.dumps(
            {"id": pid, "entry": entry, "description": desc, "tests": tests}, indent=2))
        (pdir / "refs" / "ref1.py").write_text(ref_src)
        corrects = sorted((qdir / "code" / "correct").glob("*.py"))
        rng.shuffle(corrects)
        n_ref = 1
        for c in corrects:
            src = c.read_text()
            if run_tests(src, entry, tests).all_pass:
                n_ref += 1
                (pdir / "refs" / f"ref{n_ref}.py").write_text(src)
                if n_ref == 3:
                    break
        buggy_names = []
        for i, w in enumerate(sorted((qdir / "code" / "wrong").glob("*.py")), 1):
            src = w.read_text()
            res = run_tests(src, entry, tests)
            if res.compiled and not res.all_pass:
                name = f"real_{i:03d}.py"
                (pdir / "buggy" / name).write_text(src)
                buggy_names.append(name)
        rng.shuffle(buggy_names)
        splits[pid] = {"build": sorted(buggy_names[:5]),
                       "eval": sorted(buggy_names[5:])}
        print(f"  -> {n_ref} refs, {len(buggy_names)} real buggy submissions "
              f"(build 5 / eval {len(buggy_names)-5})")

    if not dry:
        splits_path.write_text(json.dumps(splits, indent=2))
        print("splits.json updated; now run scripts/validate_benchmark.py")


if __name__ == "__main__":
    main()
