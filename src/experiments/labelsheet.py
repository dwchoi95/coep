"""`run.py labelsheet` — build results/label_study/sheet.csv for the label-accuracy study.

The paper claims legibility for the names the builder gives its rules, not
correctness: nothing in the campaign checks that ``flip_min_to_max_extremum``
is the misconception a tutor would have written down. This writes the sheet a
human needs to check exactly that, one row per builder-written rule.

Each row carries what a rater must see to judge the name without opening the
tool: the rule's own source, including the comment block the builder wrote
above it, and one repair the rule actually produced, preferring a repair where
no other rule fired so the edit is attributable to this rule alone.

``n_repairs`` is on every row because rule-level and repair-level accuracy are
different quantities. 66 of the 195 authored rules never fire, and the paper
reports a share of *repairs* that carry a name, so an unweighted rule-level
rate would answer a question the paper does not ask. Keeping the count lets
both be computed from one sheet.

Rows are shuffled under a fixed seed. Rating a tool's rules in authored order
lets each judgement lean on the last, and the assignments differ enough that
grouping would leak context between rows.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import random
from pathlib import Path

import pandas as pd

from src.core.synthesis import load_fixer
from src.experiments._common import tool_path

ROOT = Path(__file__).resolve().parents[2]
SEED = 0
FIELDS = ["rule_id", "problem", "model", "rule_name", "rule_code", "n_repairs",
          "example_buggy", "example_patch", "label"]
# accurate       -- names the misconception a tutor would recognize
# describes_edit -- states the edit correctly but is not a misconception
# wrong          -- does not describe what the rule does
LABELS = ("accurate", "describes_edit", "wrong")


def unwrap(fn):
    """The function a rule actually applies, behind any safety wrapper.

    Three of the generated tools wrap every rule in a decorator that swallows
    exceptions, so ``inspect.getsource`` on ``rule.apply`` returns the wrapper
    and every rule in that tool looks identical. Follow ``__wrapped__`` when
    functools.wraps was used, and otherwise the closure cell holding the
    wrapped function.
    """
    seen = set()
    while id(fn) not in seen:
        seen.add(id(fn))
        inner = getattr(fn, "__wrapped__", None)
        if inner is None:
            cells = [c.cell_contents for c in (fn.__closure__ or ())
                     if inspect.isfunction(getattr(c, "cell_contents", None))]
            inner = cells[0] if len(cells) == 1 else None
        if inner is None:
            return fn
        fn = inner
    return fn


def rule_source(fixer: Path, rule) -> str:
    """The rule's function, prefixed by the comment block above it.

    ``inspect.getsource`` returns the ``def`` alone, but the generated fixers
    put the builder's explanation of the misconception in a banner comment
    above each function, which is the part a rater most wants to read.
    """
    try:
        body, lineno = inspect.getsourcelines(unwrap(rule.apply))
    except (OSError, TypeError):
        return ""
    lines = fixer.read_text().splitlines()
    i = lineno - 1                        # getsourcelines is 1-based
    while i > 0 and not lines[i - 1].strip():
        i -= 1                            # blank lines between banner and def
    j = i
    while j > 0 and lines[j - 1].lstrip().startswith("#"):
        j -= 1
    head = [ln for ln in lines[j:i] if ln.strip()]
    return ("\n".join(head) + "\n" if head else "") + "".join(body)


def firings(pid: str, results: Path) -> dict[tuple[str, str], list[dict]]:
    """(model, rule name) -> the repair rows that rule contributed to."""
    f = results / pid / "coep_l.csv"
    if not f.exists():
        return {}
    df = pd.read_csv(f, keep_default_na=False)
    out: dict[tuple[str, str], list[dict]] = {}
    for _i, r in df.iterrows():
        if str(r["Fixed"]).lower() != "true":
            continue
        names = json.loads(r["Rules_L"] or "[]")
        for n in names:
            out.setdefault((r["Model"], n), []).append(
                {"buggy": r["Buggy"], "patch": r["Patch"], "alone": len(names) == 1})
    return out


def example(hits: list[dict], pid: str, data_root: Path) -> tuple[str, str]:
    """One repair for the rater, preferring one this rule made by itself."""
    if not hits:
        return "", ""
    hit = next((h for h in hits if h["alone"]), hits[0])
    src = data_root / pid / "buggy" / f"{hit['buggy']}.py"
    return (src.read_text() if src.exists() else ""), hit["patch"]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py labelsheet")
    ap.add_argument("--out", default="results/label_study/sheet.csv")
    ap.add_argument("--tools-root", default="tools")
    ap.add_argument("--data-root", default="benchmark")
    ap.add_argument("--results-root", default="results")
    ap.add_argument("--fired-only", action="store_true",
                    help="drop rules that never produced a repair")
    args = ap.parse_args(argv)

    tools, data = ROOT / args.tools_root, ROOT / args.data_root
    results = ROOT / args.results_root
    rows = []
    for pid in sorted(p.name for p in tools.iterdir() if p.is_dir()):
        fired = firings(pid, results)
        for model in sorted(p.name for p in (tools / pid).iterdir() if p.is_dir()):
            fixer = tool_path(pid, model, args.tools_root)
            if not fixer.exists():
                continue
            for rule in load_fixer(fixer):
                if rule.name.startswith("generic_"):
                    continue          # shared library, not written by a builder
                hits = fired.get((model, rule.name), [])
                if args.fired_only and not hits:
                    continue
                buggy, patch = example(hits, pid, data)
                rows.append({"rule_id": f"{pid}/{model}/{rule.name}",
                             "problem": pid, "model": model,
                             "rule_name": rule.name,
                             "rule_code": rule_source(fixer, rule),
                             "n_repairs": len(hits),
                             "example_buggy": buggy, "example_patch": patch,
                             "label": ""})

    random.Random(SEED).shuffle(rows)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    fires = sum(1 for r in rows if r["n_repairs"])
    print(f"  wrote {args.out}: {len(rows)} rules, {fires} of them fire, "
          f"{sum(r['n_repairs'] for r in rows)} rule-repairs covered")
    print(f"  label column takes one of: {', '.join(LABELS)}")
    return 0
