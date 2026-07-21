#!/usr/bin/env python3
"""Validate benchmark problems.

For each problem directory under benchmark/problems/ (or those given as args):
  - problem.json parses and has id, entry, description, tests (>=12)
  - every reference solution passes ALL tests
  - every buggy program compiles, defines the entry function, and FAILS >=1 test
  - buggy programs are pairwise distinct
Exit code 0 iff everything passes. Prints a per-problem report.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"


def validate(pdir: pathlib.Path) -> list[str]:
    errors = []
    imported = pdir.name.startswith("refactory_")
    pj = pdir / "problem.json"
    if not pj.exists():
        return [f"{pdir.name}: missing problem.json"]
    p = json.loads(pj.read_text())
    for key in ("id", "entry", "description", "tests"):
        if key not in p:
            errors.append(f"{pdir.name}: problem.json missing '{key}'")
    tests = p.get("tests", [])
    if len(tests) < 12 and not imported:
        errors.append(f"{pdir.name}: only {len(tests)} tests (need >=12)")
    for i, t in enumerate(tests):
        if "args" not in t or "expected" not in t:
            errors.append(f"{pdir.name}: test {i} malformed")

    refs = sorted((pdir / "refs").glob("*.py")) if (pdir / "refs").exists() else []
    if len(refs) < 3:
        errors.append(f"{pdir.name}: only {len(refs)} reference solutions (need >=3)")
    for ref in refs:
        r = run_tests(ref.read_text(), p["entry"], tests)
        if not r.all_pass:
            detail = r.error or (r.failures[0] if r.failures else "?")
            errors.append(f"{pdir.name}/{ref.name}: FAILS tests ({r.passed}/{r.total}) {detail}")

    buggy = sorted((pdir / "buggy").glob("*.py")) if (pdir / "buggy").exists() else []
    seen = {}
    for bf in buggy:
        src = bf.read_text()
        if src.strip() in seen and not imported:
            errors.append(f"{pdir.name}/{bf.name}: duplicate of {seen[src.strip()]}")
        seen[src.strip()] = bf.name
        try:
            compile(src, bf.name, "exec")
        except SyntaxError as e:
            errors.append(f"{pdir.name}/{bf.name}: syntax error {e}")
            continue
        r = run_tests(src, p["entry"], tests)
        if not r.compiled:
            errors.append(f"{pdir.name}/{bf.name}: does not run: {r.error}")
        elif r.all_pass:
            errors.append(f"{pdir.name}/{bf.name}: passes all tests (not buggy!)")
    crafted = [] if imported else [b for b in buggy if b.name.startswith("crafted")]
    if crafted and len(crafted) < 10:
        errors.append(f"{pdir.name}: only {len(crafted)} crafted bugs (need >=10)")
    return errors


def main():
    targets = sys.argv[1:] or [d.name for d in sorted(PROBLEMS.iterdir()) if d.is_dir()]
    all_errors = []
    for name in targets:
        errs = validate(PROBLEMS / name)
        n_buggy = len(list((PROBLEMS / name / "buggy").glob("*.py"))) if (PROBLEMS / name / "buggy").exists() else 0
        status = "OK" if not errs else f"{len(errs)} ERROR(S)"
        print(f"[{status}] {name} ({n_buggy} buggy)")
        for e in errs:
            print(f"    - {e}")
        all_errors += errs
    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
