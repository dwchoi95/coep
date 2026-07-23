#!/usr/bin/env python3
"""Import the PyDex (OOPSLA'24) benchmark into the unified `data/<pid>/` schema.

Source: https://github.com/microsoft/prose-benchmarks/tree/main/PyDex — 286 real
student programs across 15 introductory Python tasks from a university course in
India, released by the PyDex authors as (buggy, correct) pairs. Programs read
stdin and print stdout, so imported problems use `mode: "stdio"`.

Unlike Refactory, this corpus contains **syntax errors as well as semantic
ones**, which is why a `syntax_error` flag is recorded per program.

Each source file holds one problem:
    {problem_ID, statement, reference_solution,
     IO_example: [{IO_number, input, output}],
     submission: [{syntax_incorrect, semantics_correct}]}

Layout produced:
    data/pydex_<pid>/problem.json      description, tests, mode
    data/pydex_<pid>/buggy/<n>.py      the student's incorrect submission
    data/pydex_<pid>/fixed/<n>.py      its ground-truth correct version
    data/pydex_<pid>/reference.py      instructor reference solution

Usage:  python data/_import/pydex.py --src <dir with *_pair.json> [--out data]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


_HARNESS_ERROR = re.compile(r"OUCH!!|generated an Exception|Traceback \(most recent", re.I)


def _clean(code: str) -> str:
    return re.sub(r"\r\n?", "\n", code or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path,
                    help="directory containing PyDex *_pair.json files")
    ap.add_argument("--out", default="data", type=Path)
    args = ap.parse_args()

    files = sorted(args.src.glob("*_pair.json"))
    if not files:
        print(f"no *_pair.json under {args.src}")
        return 1

    total_bugs = total_syntax = 0
    for f in files:
        d = json.loads(f.read_text())
        pid = f"pydex_{d['problem_ID']}"
        tests, dropped = [], 0
        for io in d.get("IO_example", []):
            expected = _norm_io(io["output"])
            if _HARNESS_ERROR.search(expected):
                dropped += 1   # PyDex captured its own runner's exception text
                continue
            tests.append({"stdin": _norm_io(io["input"]), "expected": expected})
        if not tests:
            print(f"  !! {pid}: no IO examples, skipped")
            continue

        pdir = args.out / pid
        (pdir / "buggy").mkdir(parents=True, exist_ok=True)
        (pdir / "fixed").mkdir(parents=True, exist_ok=True)
        (pdir / "reference.py").write_text(_clean(d.get("reference_solution", "")))

        n_syntax = 0
        for i, sub in enumerate(d.get("submission", []), start=1):
            buggy = _clean(sub.get("syntax_incorrect", ""))
            fixed = _clean(sub.get("semantics_correct", ""))
            name = f"{i:03d}.py"
            (pdir / "buggy" / name).write_text(buggy)
            (pdir / "fixed" / name).write_text(fixed)
            if not _parses(buggy):
                n_syntax += 1

        n_bug = len(d.get("submission", []))
        (pdir / "problem.json").write_text(json.dumps({
            "pid": pid, "source": "pydex", "mode": "stdio",
            "description": _statement(d.get("statement", "")),
            "tests": tests,
        }, indent=1))
        total_bugs += n_bug
        total_syntax += n_syntax
        print(f"  {pid}: buggy={n_bug} (syntax-error {n_syntax}) tests={len(tests)}"
              + (f" [{dropped} contaminated tests dropped]" if dropped else ""))

    print(f"imported {len(files)} problems, {total_bugs} buggy programs "
          f"({total_syntax} with syntax errors, {total_syntax/max(1,total_bugs):.0%})")
    return 0


def _parses(src: str) -> bool:
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


def _norm_io(text) -> str:
    """IO fields may be lists of lines or a single string."""
    if isinstance(text, list):
        text = "\n".join(str(x) for x in text)
    text = _clean(str(text))
    return text if text.endswith("\n") or not text else text + "\n"


def _statement(html: str) -> str:
    """Strip the light HTML markup the statements carry."""
    text = re.sub(r"<br\s*/?>", "\n", html or "")
    text = re.sub(r"</?[bi]>", "", text)
    return re.sub(r"<[^>]+>", "", text).strip()


if __name__ == "__main__":
    raise SystemExit(main())
