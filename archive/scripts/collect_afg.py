"""`run.py collect-afg` — collect BRAFAR and MENTORED runs into the unified CSVs.

    results/<ver>/<p_id>/brafar.csv     one row per buggy submission
    results/<ver>/<p_id>/mentored.csv   one row per buggy submission
    results/<ver>/<p_id>/summary.csv    upserted (Approach=BRAFAR|MENTORED, Model=none)

Both tools search and validate with their own harness; a repair counts here only
if the returned program also passes OUR oracle (src/runner), the same judge
every other arm is scored by, and RPS is re-measured against the student's
original program in data/. Submissions a tool never reported are failures, so
the denominator is the pool as published and identical across arms.

Where each run lives (see baselines/*/run_all.sh):
  BRAFAR    baselines/brafar/data/question_N/brafar_result_100.authors.csv (R1-R5)
            baselines/brafar/data_cf/<pid>/brafar_result_100.csv       (C1-C6)
  MENTORED  baselines/mentored/data_coep/problem_K/feedbacks/mentored/ (all 11;
            problem_K -> pid in data_coep/mapping.json); for R1-R5 the authors'
            run in feedbacks/mentored_authors/ is used when present
"""
from __future__ import annotations

import argparse
import ast
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src.experiments._common import load_problem
from src.experiments.refactory_results import unwrap
from src.experiments.results_io import (build_overall, event_row,
                                        summarize_events, upsert_summary,
                                        write_events)
from src.experiments.tables import ORDER
from src.runner.testing import run_tests
from src.utils.metrics import rps as compute_rps

ROOT = Path(__file__).resolve().parents[2]
BRAFAR = ROOT / "baselines" / "brafar"
MENTORED = ROOT / "baselines" / "mentored" / "data_coep"


def _buggy(pid: str) -> dict[str, str]:
    return {p.stem: p.read_text()
            for p in sorted((ROOT / "data" / pid / "buggy").glob("*.py"))}


def _passes(src: str, problem: dict) -> bool:
    r = run_tests(src, problem)
    return r.error is None and r.total > 0 and r.passed == r.total


def _rps(buggy: str, patch: str) -> float | None:
    try:
        return compute_rps(buggy, patch)
    except Exception:                         # noqa: BLE001 - unparseable patch
        return None


# ---------------------------------------------------------------- BRAFAR
def _brafar_csv(pid: str) -> Path:
    """R1-R5: the authors' own run shipped with BRAFAR (as for Refactory, the tool
    at the configuration they report; our re-run, brafar_result_100.csv beside it,
    accepts slightly fewer because its 0.01 s per-test budget is load-sensitive).
    C1-C6: our run."""
    if pid.startswith("refactory_q"):
        return (BRAFAR / "data" / f"question_{pid.rsplit('_q', 1)[1]}"
                / "brafar_result_100.authors.csv")
    return BRAFAR / "data_cf" / pid / "brafar_result_100.csv"


def collect_brafar(pid: str, ver: str = "") -> dict:
    problem, buggy = load_problem(pid), _buggy(pid)
    df = pd.read_csv(_brafar_csv(pid), keep_default_na=False)
    by_stem = {str(r["File Name"])[:-3]: r for _, r in df.iterrows()}

    def one(stem: str) -> dict:
        r = by_stem.get(stem)
        if r is None:                         # not exported / not reported
            return event_row(stem, "none", "none", False)
        att = float(r["Total Time"] or 0.0)
        patch = str(r["Repair"]) if str(r["Status"]) == "True" else ""
        # C1-C6 run inside the stdio shim's `def main(): try: ... except _Exit`
        patch = unwrap(patch) if patch and not pid.startswith("refactory_q") else patch
        ok = bool(patch) and _passes(patch, problem)
        return event_row(stem, "none", "reference" if ok else "none", ok,
                         patch, _rps(buggy[stem], patch) if ok else None,
                         att_cpu=att)

    with ThreadPoolExecutor(max_workers=16) as ex:
        rows = list(ex.map(one, buggy))
    return _store(ver, pid, "brafar", "BRAFAR", rows)


# ---------------------------------------------------------------- MENTORED
def _mentored_dir(pid: str) -> Path:
    mapping = json.loads((MENTORED / "mapping.json").read_text())
    return MENTORED / next(k for k, v in mapping.items() if v == pid)


def _strip_prelude(patch: str, theirs: str, ours: str) -> str:
    """Drop the top-level statements MENTORED's own CS1 datasets prepend.

    Its R1-R5 programs carry Refactory's global.py (imports, a global tuple)
    above the student's code; ours do not. Those lines are not part of any
    repair, so they are removed before RPS is measured against our program.
    """
    try:
        ours_d = {ast.dump(n) for n in ast.parse(ours).body}
        extra = {ast.dump(n) for n in ast.parse(theirs).body} - ours_d
        tree = ast.parse(patch)
    except SyntaxError:
        return patch
    if not extra:
        return patch
    tree.body = [n for n in tree.body if ast.dump(n) not in extra]
    return ast.unparse(tree)


def collect_mentored(pid: str, ver: str = "") -> dict:
    problem, buggy = load_problem(pid), _buggy(pid)
    pdir = _mentored_dir(pid)
    theirs = json.loads((pdir / "dataset.json").read_text())["wrongs"]["1"]
    fb = pdir / "feedbacks" / "mentored"
    # R1-R5: the authors' own run shipped in MENTORED's data.zip, on the very
    # datasets we run (as for Refactory and BRAFAR); C1-C6 and the time: ours
    authors = pdir / "feedbacks" / "mentored_authors" / "with_correct.json"
    log = authors if authors.exists() else next(
        p for p in (fb / "with_correct_1.json", fb / "with_correct.json")
        if p.exists())
    entries = json.loads(log.read_text())
    if isinstance(entries, dict):             # tinydb layout {table: {id: doc}}
        entries = [d for t in entries.values() for d in t.values()]
    res = json.loads((fb / "results.json").read_text())
    res = [d for t in res.values() for d in t.values()]
    att = float(res[-1]["AVG Time Taken(sec)"])   # process time / |wrongs|

    cands: dict[str, list[str]] = {}
    for e in entries:
        if e.get("solution") is True:
            stem = str(e["patch_id"]).rsplit("_", 1)[0]
            cands.setdefault(stem, []).append(e["patch"])

    def one(stem: str) -> dict:
        scored = []
        for patch in dict.fromkeys(cands.get(stem, [])):
            bare = _strip_prelude(patch, theirs.get(stem, ""), buggy[stem])
            scored.append((_rps(buggy[stem], bare), patch, bare))
        scored.sort(key=lambda t: (t[0] is None, t[0] or 0.0))
        for r, patch, bare in scored:         # smallest first, as the tool picks
            if _passes(patch, problem):
                return event_row(stem, "none", "reference", True, bare, r,
                                 att_cpu=att)
        return event_row(stem, "none", "none", False, att_cpu=att)

    with ThreadPoolExecutor(max_workers=16) as ex:
        rows = list(ex.map(one, buggy))
    return _store(ver, pid, "mentored", "MENTORED", rows)


def _store(ver: str, pid: str, file: str, arm: str, rows: list[dict]) -> dict:
    write_events(ver, pid, file, rows)
    summ = summarize_events(arm, "none", rows)
    upsert_summary(ver, pid, summ)
    print(f"[{pid}] {arm}: RR={100 * summ['RR']:.2f}% RPS={summ['RPS']:.4f} "
          f"ATT={summ['ATT_cpu']:.2f}s")
    return summ


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run.py collect-afg")
    ap.add_argument("tool", choices=["brafar", "mentored"])
    ap.add_argument("pids", nargs="*", default=ORDER)
    ap.add_argument("--ver", default="")
    args = ap.parse_args(argv)
    collect = collect_brafar if args.tool == "brafar" else collect_mentored
    for pid in args.pids:
        try:
            collect(pid, args.ver)
        except Exception as e:                # noqa: BLE001 - keep going
            print(f"[{pid}] collect FAILED: {type(e).__name__}: {e}")
    build_overall(args.ver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
