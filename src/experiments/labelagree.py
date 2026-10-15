"""`run.py labelagree` — aggregate the rule-name labelling study.

Reads results/rules_<n>.csv, one per rater, each the sheet `run.py labelsheet`
wrote with the ``label`` column filled in. Reports Fleiss' kappa, the majority
label, and the two accuracy rates.

Rule-level and repair-weighted rates answer different questions and both are
printed. The paper's claim is about the labels a *student* sees, so the
repair-weighted rate is the one that speaks to it: a rule that never fires
never shows a name to anyone. The rule-level rate says what the builder wrote.

Four rules are dropped: the guide used them as worked examples, so the raters
were told their answers before they started.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CATS = ("accurate", "describes_edit", "wrong")
# named as examples in results/labeling_guide.md, so not independently judged
GUIDE = ("refactory_q5/claude-sonnet-5/append_of_remove_returns_none",
         "cf_110A/claude-sonnet-5/char_compared_to_int_digit",
         "cf_1011B/claude-sonnet-5/lt_to_le",
         "cf_11B/gpt-5.4-mini/abs_input_int")


def fleiss(rows: list[list[str]]) -> float:
    """Fleiss' kappa over rows of per-rater labels, all rows the same width."""
    n, m = len(rows), len(rows[0])
    counts = [[r.count(c) for c in CATS] for r in rows]
    p_i = [(sum(x * x for x in c) - m) / (m * (m - 1)) for c in counts]
    p_j = [sum(c[j] for c in counts) / (n * m) for j in range(len(CATS))]
    p_bar, p_e = sum(p_i) / n, sum(p * p for p in p_j)
    return (p_bar - p_e) / (1 - p_e)


def rates(df: pd.DataFrame, weight: str | None) -> dict[str, float]:
    total = df[weight].sum() if weight else len(df)
    if not total:
        return {c: float("nan") for c in CATS}
    return {c: 100 * ((df[df.label == c][weight].sum() if weight
                       else (df.label == c).sum()) / total) for c in CATS}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py labelagree")
    ap.add_argument("--sheet", default="results/rules.csv")
    ap.add_argument("--raters", nargs="+",
                    default=["results/rules_1.csv", "results/rules_2.csv",
                             "results/rules_3.csv"])
    ap.add_argument("--keep-guide", action="store_true",
                    help="include the four rules the guide worked through")
    args = ap.parse_args(argv)

    base = pd.read_csv(ROOT / args.sheet, keep_default_na=False)
    labels = []
    for f in args.raters:
        d = pd.read_csv(ROOT / f, keep_default_na=False)
        if list(d.rule_id) != list(base.rule_id):
            raise SystemExit(f"{f}: rule_id order differs from {args.sheet}")
        bad = set(d.label) - set(CATS)
        if bad:
            raise SystemExit(f"{f}: labels outside the scheme: {sorted(bad)}")
        labels.append(d.label.tolist())

    per_row = [[lab[i] for lab in labels] for i in range(len(base))]
    base = base.assign(
        label=[collections.Counter(r).most_common(1)[0][0] for r in per_row],
        unanimous=[len(set(r)) == 1 for r in per_row])
    keep = base if args.keep_guide else base[~base.rule_id.isin(GUIDE)]
    rows = [r for r, k in zip(per_row, base.rule_id.isin(GUIDE))
            if args.keep_guide or not k]

    print(f"  {len(keep)} rules, {len(labels)} raters")
    print(f"  Fleiss kappa {fleiss(rows):.3f}, unanimous on "
          f"{keep.unanimous.sum()} ({100 * keep.unanimous.mean():.1f}%)")
    fired = keep[keep.n_repairs > 0]
    for label, df, w in (("rule-level      ", keep, None),
                         ("rule-level/fired", fired, None),
                         ("repair-weighted ", fired, "n_repairs")):
        r = rates(df, w)
        n = df[w].sum() if w else len(df)
        print(f"  {label} n={n:<5} " +
              "  ".join(f"{c} {r[c]:5.1f}%" for c in CATS))
    for model in sorted(keep.model.unique()):
        s = keep[keep.model == model]
        r, rw = rates(s, None), rates(s[s.n_repairs > 0], "n_repairs")
        print(f"  {model:<16} wrong {r['wrong']:5.1f}% of {len(s):>3} rules, "
              f"{rw['wrong']:4.1f}% of repairs")
    return 0
