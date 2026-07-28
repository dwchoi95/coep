"""`run.py resummarize` — rebuild summary.csv rows from the event logs.

The event log is the record; summary.csv is a view of it. A pass that writes
one arm can still upsert another arm's row, and if it does so from an empty
row list it silently zeroes a completed measurement -- which is how the
framework-only ablation wiped every CoEP_LF summary row while leaving
coep_lf.csv intact. Rebuilding the view from the record costs nothing and makes
that class of loss recoverable rather than a re-run.

Only arms whose event file exists are touched; anything else is left alone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.synthesis import load_fixer
from src.experiments._common import tool_path
from src.experiments.results_io import (build_overall, read_events,
                                        summarize_events, upsert_summary)

ROOT = Path(__file__).resolve().parents[2]

# event file -> (approach label, does this arm have a build behind it)
ARMS = {"refactory": ("Refactory", False), "pydex": ("PyDex", False),
        "pydex_pc": ("PyDex_PC", False), "coep_l": ("CoEP_L", True),
        "coep_lf": ("CoEP_LF", True), "coep_l_sl": ("CoEP_L+SL", True),
        "coep_l_fw": ("CoEP_L_fw", True)}
# Refactory's CS1 rows are its *published* per-assignment figures and PyDex's
# carry token counts the collector priced; recomputing either from our event
# logs would silently replace an external number with our own. They are
# rebuilt only when named.
DEFAULT = ("coep_l", "coep_lf", "coep_l_sl", "coep_l_fw")
# Refactory's five CS1 rows are its published per-assignment results. Naming
# `--only refactory` must not silently recompute those from our own run, so they
# are refused even when the arm is named; its Codeforces rows are ours and are
# rebuilt normally.
PUBLISHED = {("refactory", p) for p in
             ("refactory_q1", "refactory_q2", "refactory_q3",
              "refactory_q4", "refactory_q5")}


def _build_cost(pid: str, model: str, tools_root: str) -> tuple[float, float]:
    f = tool_path(pid, model, tools_root).parent / "cost.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    return float(d.get("build_seconds") or 0.0), float(d.get("usd") or 0.0)


def _authored(pid: str, model: str, tools_root: str) -> list[str]:
    """The builder-authored rule names, read back off the frozen tool.

    Without this the rebuilt summary carries an empty Rules_build and every
    rule-produced repair is then attributed to the always-on generic library --
    which silently inverts the repair-source split the paper reports.
    """
    f = tool_path(pid, model, tools_root)
    if not f.exists():
        return []
    return [r.name for r in load_fixer(f) if not r.name.startswith("generic_")]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py resummarize")
    ap.add_argument("--ver", default="v2")
    ap.add_argument("--tools-root", default="tools")
    ap.add_argument("--only", nargs="*", default=list(DEFAULT),
                    help="event file stems to rebuild; the baseline arms are "
                         "excluded by default and must be named explicitly")
    args = ap.parse_args(argv)

    base = ROOT / "results" / args.ver
    fixed = 0
    for pdir in sorted(p for p in base.iterdir() if p.is_dir()):
        for stem, (approach, has_build) in ARMS.items():
            if args.only and stem not in args.only:
                continue
            if not (pdir / f"{stem}.csv").exists():
                continue
            if (stem, pdir.name) in PUBLISHED:
                print(f"  {pdir.name:<14}{approach:<11}skipped (published figures)")
                continue
            rows = read_events(args.ver, pdir.name, stem)
            for model in sorted({str(r["Model"]) for r in rows}):
                mine = [r for r in rows if str(r["Model"]) == model]
                att_build, usd = ((0.0, 0.0) if not has_build else
                                  _build_cost(pdir.name, model, args.tools_root))
                # the learned artifact prices its own induction on top
                rec = summarize_events(
                    approach, model, mine, att_build=att_build, build_usd=usd,
                    rules_build=(_authored(pdir.name, model, args.tools_root)
                                 if has_build else ()))
                upsert_summary(args.ver, pdir.name, rec)
                fixed += 1
                print(f"  {pdir.name:<14}{approach:<11}{model:<17}"
                      f"N={rec['N']:>4} RR={100*rec['RR']:.2f}% RPS={rec['RPS']}")
    print(f"rebuilt {fixed} summary rows -> {build_overall(args.ver)}")
    return 0
