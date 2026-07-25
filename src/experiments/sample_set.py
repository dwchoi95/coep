"""Build a stratified smoke-test set, so methodology changes can be re-tested
without paying for a full pass over all 2,970 buggy submissions.

Sampling is stratified on the axes that decide whether a change is an
improvement, not on raw counts:

  * **baseline agreement** — whether Refactory and PyDex repaired the same
    submission. The bulk of the corpus sits in the both-repaired cell, so that
    cell is sampled down; the cells where a baseline fails are small and are
    taken whole, because they carry the difficulty signal.
  * **local patch size** — which tercile of \\textsc{CoEP}'s own RPS
    distribution the submission falls in, when a local-only pass exists. An
    RPS gate must fire on the tail and must *not* fire on the body, so a set
    that omits either cannot detect a regression.

Per-submission Refactory results exist only for the Codeforces problems (its
own corpus is quoted from the published paper), so there the agreement axis
degrades to PyDex alone. Selection is seeded and written to a manifest, so a
re-test after a methodology change runs on exactly the same submissions.

Usage:
    python3 -m src.experiments.sample_set [--n 60] [--seed 0]
                                          [--out data/smoke_set.json]
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Cells at or below this size carry too little signal to sample: take them whole.
TAKE_ALL_BELOW = 6
# Every non-empty stratum contributes at least this many, so no cell vanishes.
MIN_PER_CELL = 2


def _arm(path: Path, name: str) -> pd.DataFrame | None:
    if not path.exists():
        return None
    d = pd.read_csv(path)[["Buggy", "Fixed", "RPS"]]
    return d.rename(columns={"Fixed": f"{name}_ok", "RPS": f"{name}_rps"})


def strata(pid: str, ver: str, local_ver: str) -> pd.DataFrame:
    """One row per candidate submission, tagged with its stratum key."""
    res = ROOT / "results"
    pydex = _arm(res / ver / pid / "pydex.csv", "P")
    if pydex is None:
        return pd.DataFrame()
    df = pydex
    refac = _arm(res / ver / pid / "refactory.csv", "R")
    if refac is not None:
        df = df.merge(refac, on="Buggy", how="inner")
    local = _arm(res / local_ver / pid / "coep_l.csv", "L")
    if local is not None:
        df = df.merge(local, on="Buggy", how="inner")

    def agree(r) -> str:
        p = "P+" if r.P_ok else "P-"
        return f"{'R+' if r.R_ok else 'R-'}{p}" if "R_ok" in df.columns else p

    df["cell"] = df.apply(agree, axis=1)
    if "L_ok" in df.columns:
        ok = df[df.L_ok.astype(bool)]
        lo, hi = (ok.L_rps.quantile([1 / 3, 2 / 3]) if len(ok) >= 3
                  else (float("inf"), float("inf")))

        def bucket(r) -> str:
            if not r.L_ok:
                return "miss"            # the submissions the fallback exists for
            return "body" if r.L_rps <= lo else ("mid" if r.L_rps <= hi else "tail")

        df["cell"] = df.cell + "/" + df.apply(bucket, axis=1)
    return df


def pick(df: pd.DataFrame, n: int, rng: random.Random):
    """Square-root allocation across strata, small cells taken whole.

    Proportional allocation would spend the budget on the both-repaired cell
    and leave the interesting ones too thin to read: on cf_110A it gives the
    375-strong easy cell 50 slots and the 64 submissions Refactory cannot
    repair only 9. Allocating by ``sqrt(size)`` buys precision where the cells
    are small while still tracking size, and the returned per-cell weight
    (cell size / sampled) reweights the sample back to a corpus-level estimate.
    """
    groups = {k: list(g.Buggy.astype(str)) for k, g in df.groupby("cell")}
    chosen: dict[str, list[str]] = {}
    budget = n
    big = {}
    for k, ids in groups.items():
        if len(ids) <= TAKE_ALL_BELOW:          # take whole, from the same budget
            chosen[k] = list(ids)
            budget -= len(ids)
        else:
            big[k] = ids
    total = sum(len(v) ** 0.5 for v in big.values())
    for k, ids in big.items():
        share = (max(MIN_PER_CELL, round(budget * len(ids) ** 0.5 / total))
                 if total else 0)
        chosen[k] = rng.sample(ids, min(len(ids), share))
    weights = {k: len(groups[k]) / len(v) for k, v in chosen.items() if v}
    return sorted({i for ids in chosen.values() for i in ids}), chosen, weights


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60, help="target per problem")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ver", default="v2", help="where baseline results live")
    ap.add_argument("--local-ver", default="missprobe",
                    help="where the local-only CoEP pass lives")
    ap.add_argument("--out", default="data/smoke_set.json")
    args = ap.parse_args(argv)

    rng = random.Random(args.seed)
    out: dict[str, list[str]] = {}
    meta: dict[str, dict] = {}
    for d in sorted((ROOT / "results" / args.ver).iterdir()):
        if not d.is_dir():
            continue
        df = strata(d.name, args.ver, args.local_ver)
        if df.empty:
            print(f"{d.name:14s} no per-submission baselines, skipped")
            continue
        ids, per_cell, weights = pick(df, args.n, rng)
        out[d.name] = ids
        meta[d.name] = {"pool": len(df), "picked": len(ids),
                        "cells": {k: f"{len(v)}/{int((df.cell == k).sum())}"
                                  for k, v in sorted(per_cell.items())},
                        # corpus weight per sampled submission, by stratum
                        "weights": {k: round(w, 3)
                                    for k, w in sorted(weights.items())},
                        "member_cell": {i: k for k, v in per_cell.items()
                                        for i in v}}
        print(f"{d.name:14s} pool={len(df):5d} -> {len(ids):3d}  "
              + "  ".join(f"{k}:{v}" for k, v in meta[d.name]["cells"].items()))

    payload = {"_meta": {"seed": args.seed, "n_target": args.n,
                         "total": sum(len(v) for v in out.values()),
                         "per_problem": meta},
               "problems": out}
    Path(args.out).write_text(json.dumps(payload, indent=1))
    print(f"\n{payload['_meta']['total']} submissions -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
