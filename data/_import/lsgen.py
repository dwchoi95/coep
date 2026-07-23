#!/usr/bin/env python3
"""Import the LSGen (AAAI-26) test split into the unified `data/<pid>/` schema.

Source: https://github.com/PandaAB/LSGen — 110 problems, 1,668 (Wrong-Answer →
Accepted) pairs by the same student, drawn from CodeNet (AIZU/AtCoder). Programs
read stdin and print stdout, so imported problems use `mode: "stdio"`.

Layout produced:

    data/<pid>/problem.json     description, tests, mode
    data/<pid>/buggy/<sid>.py   the Wrong-Answer submission
    data/<pid>/fixed/<sid>.py   the SAME student's later accepted submission

`fixed/` is the ground-truth pair. Reference selection happens at split time, so
no evaluation program's fix is ever handed to a builder.

Usage:  python data/_import/lsgen.py [--lsgen baselines/LSGen] [--out data]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_descriptions(lsgen: Path) -> dict[str, dict]:
    path = lsgen / "dataset/repairDataset/Program_Question_Data/English_Program_Question_StringVersion.json"
    return {r["Pid"]: r for r in json.loads(path.read_text()) if r.get("Pid")}


def load_tests(case_dir: Path) -> list[dict]:
    """Pair input.N.txt with output.N.txt; N ordering is numeric, not lexical."""
    if not case_dir.is_dir():
        return []
    tests = []
    for inp in case_dir.glob("input.*.txt"):
        idx = inp.name[len("input."):-len(".txt")]
        out = case_dir / f"output.{idx}.txt"
        if not out.exists():
            continue
        try:
            tests.append({"_i": int(idx), "stdin": inp.read_text(),
                          "expected": out.read_text()})
        except (ValueError, UnicodeDecodeError):
            continue
    tests.sort(key=lambda t: t["_i"])
    return [{"stdin": t["stdin"], "expected": t["expected"]} for t in tests]


def describe(rec: dict) -> str:
    """Readable statement: task text, then constraints and I/O format."""
    parts = [f"# {rec.get('title', '').strip()}"]
    body = (rec.get("ProblemText") or rec.get("content") or "").strip()
    if body:
        parts.append(body)
    for label, key in (("Constraints", "constraint"), ("Input", "input"),
                       ("Output", "output")):
        val = (rec.get(key) or "").strip()
        if val:
            parts.append(f"## {label}\n{val}")
    samples = rec.get("samples")
    if samples and samples != "[]":
        parts.append(f"## Examples\n{samples}")
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lsgen", default="baselines/LSGen", type=Path)
    ap.add_argument("--out", default="data", type=Path)
    args = ap.parse_args()

    root = args.lsgen / "dataset/repairDataset"
    pairs = json.loads((root / "RepairData-PythonLevel/Dataset/test.json").read_text())
    descriptions = load_descriptions(args.lsgen)

    by_problem: dict[str, list[dict]] = {}
    for r in pairs:
        by_problem.setdefault(r["problem_id"], []).append(r)

    written = skipped_no_tests = 0
    stats = []
    for pid, records in sorted(by_problem.items()):
        tests = load_tests(root / "merged_test_cases" / pid)
        if not tests:
            skipped_no_tests += 1
            continue
        pdir = args.out / pid
        (pdir / "buggy").mkdir(parents=True, exist_ok=True)
        (pdir / "fixed").mkdir(parents=True, exist_ok=True)
        for rec in records:
            sid = rec["submission1_id"]
            (pdir / "buggy" / f"{sid}.py").write_text(_clean(rec["code1"]))
            (pdir / "fixed" / f"{sid}.py").write_text(_clean(rec["code2"]))
        desc = describe(descriptions.get(pid, {"title": pid}))
        (pdir / "problem.json").write_text(json.dumps({
            "pid": pid, "source": "lsgen", "mode": "stdio",
            "description": desc, "tests": tests,
        }, indent=1))
        written += 1
        stats.append((pid, len(records), len(tests)))

    print(f"imported {written} problems ({skipped_no_tests} skipped: no test cases)")
    print(f"  buggy programs: {sum(s[1] for s in stats)}")
    print(f"  tests/problem  : min {min(s[2] for s in stats)}, "
          f"median {sorted(s[2] for s in stats)[len(stats)//2]}, "
          f"max {max(s[2] for s in stats)}")
    print(f"  buggy/problem  : min {min(s[1] for s in stats)}, "
          f"max {max(s[1] for s in stats)}")
    return 0


def _clean(code: str) -> str:
    """Normalize line endings; leave everything else byte-identical."""
    return re.sub(r"\r\n?", "\n", code or "")


if __name__ == "__main__":
    raise SystemExit(main())
