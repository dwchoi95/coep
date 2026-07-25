"""RQ5 reporter: per-rating-band effectiveness and per-provider agreement.

Reads the unified per-problem summaries and emits (a) a difficulty table
ordered by Codeforces rating band, (b) the same table as a LaTeX fragment
for the paper, and (c) a per-provider comparison for every LLM approach.

Repair rates carry Wilson 95% intervals, so small-N cells (cf_10C has 3
submissions) are visibly uninformative rather than silently misleading.

Usage: python3 -m src.experiments.rq5_report [--ver v2] [--tex paper/rq5.tex]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Codeforces rating bands (inclusive lower bound) -> official title.
BANDS = [(0, "Newbie"), (1200, "Pupil"), (1400, "Specialist"),
         (1600, "Expert"), (1900, "Candidate Master"), (2100, "Master")]

# A band cell with fewer submissions than this is reported but excluded
# from the difficulty trend, because its interval spans most of [0, 1].
MIN_TREND_N = 10


def band_of(rating: int) -> str:
    title = BANDS[0][1]
    for lo, name in BANDS:
        if rating >= lo:
            title = name
    return title


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def load(ver: str) -> pd.DataFrame:
    rows = []
    for d in sorted((ROOT / "results" / ver).iterdir()):
        summ = d / "summary.csv"
        prob = ROOT / "data" / d.name / "problem.json"
        if not summ.exists() or not prob.exists():
            continue
        meta = json.loads(prob.read_text())
        rating = meta.get("rating")
        for _, r in pd.read_csv(summ).iterrows():
            rows.append({
                "pid": d.name,
                "corpus": "Codeforces" if meta.get("source") == "codeforces"
                          else "Refactory",
                "rating": rating,
                "band": band_of(rating) if rating else "CS1",
                "approach": r["Approach"],
                "model": r["Model"],
                "n": int(r["N"]),
                "rr": float(r["RR"]),
                "rps": float(r["RPS"]),
                "att": float(r["ATT_all"]),
                "usd": float(r["$API"]),
            })
    return pd.DataFrame(rows)


def difficulty_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (band, approach): N-weighted RR/RPS with Wilson bounds."""
    cf = df[df.corpus == "Codeforces"]
    out = []
    for (band, rating, approach, model), g in cf.groupby(
            ["band", "rating", "approach", "model"], dropna=False):
        n = int(g.n.sum())
        k = int(round((g.n * g.rr).sum()))
        rep = (g.n * g.rr).sum()
        rps = (g.n * g.rr * g.rps).sum() / rep if rep else 0.0
        lo, hi = wilson(k, n)
        out.append({"band": band, "rating": rating, "approach": approach,
                    "model": model, "n": n, "rr": k / n if n else 0.0,
                    "rr_lo": lo, "rr_hi": hi, "rps": rps,
                    "in_trend": n >= MIN_TREND_N})
    return pd.DataFrame(out).sort_values(["rating", "approach", "model"])


def provider_table(df: pd.DataFrame) -> pd.DataFrame:
    """Per-approach micro-averages for each model, over the whole corpus."""
    llm = df[df.model != "none"]
    out = []
    for (approach, model), g in llm.groupby(["approach", "model"]):
        n = int(g.n.sum())
        rep = (g.n * g.rr).sum()
        out.append({
            "approach": approach, "model": model, "problems": len(g), "n": n,
            "rr": rep / n if n else 0.0,
            "rps": (g.n * g.rr * g.rps).sum() / rep if rep else 0.0,
            "usd_per_sub": g.usd.sum() / n if n else 0.0,
        })
    return pd.DataFrame(out).sort_values(["approach", "model"])


def to_tex(diff: pd.DataFrame) -> str:
    """LaTeX fragment: rating bands x approaches, RR [Wilson] and RPS."""
    approaches = list(dict.fromkeys(diff.approach))
    lines = [r"\begin{tabular}{@{}llr" + "cc" * len(approaches) + r"@{}}",
             r"\toprule"]
    head = ["Band", "Rating", "N"]
    for a in approaches:
        head += [f"{a} RR (\\%)", "RPS"]
    lines.append(" & ".join(head) + r" \\", )
    lines.append(r"\midrule")
    for (band, rating), g in diff.groupby(["band", "rating"], sort=True):
        n = int(g.n.max())
        cells = [band, str(int(rating)), f"{n:,}"]
        for a in approaches:
            row = g[g.approach == a]
            if row.empty:
                cells += ["--", "--"]
                continue
            r = row.iloc[0]
            mark = "" if r.in_trend else r"$^{\dagger}$"
            cells += [f"{100*r.rr:.1f}{mark}", f"{r.rps:.3f}"]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", default="v2")
    ap.add_argument("--tex", default="", help="write the LaTeX fragment here")
    args = ap.parse_args(argv)

    df = load(args.ver)
    if df.empty:
        print("no results yet")
        return 1

    diff = difficulty_table(df)
    print("=== RQ5a: effectiveness by Codeforces rating band ===")
    for _, r in diff.iterrows():
        flag = "" if r.in_trend else f"  (N<{MIN_TREND_N}, excluded from trend)"
        model = "" if r.model == "none" else f" [{r.model}]"
        print(f"{r.band:16s} {int(r.rating):5d} {r.approach:9s}{model:18s} "
              f"N={r.n:4d} RR={100*r.rr:6.2f}% "
              f"[{100*r.rr_lo:.1f}, {100*r.rr_hi:.1f}] "
              f"RPS={r.rps:.3f}{flag}")

    prov = provider_table(df)
    print("\n=== RQ5b: provider agreement (whole corpus, micro-averaged) ===")
    for _, r in prov.iterrows():
        print(f"{r.approach:10s} {r.model:16s} problems={r.problems:2d} "
              f"N={r.n:5d} RR={100*r.rr:6.2f}% RPS={r.rps:.3f} "
              f"${r.usd_per_sub:.4f}/sub")

    for approach, g in prov.groupby("approach"):
        if len(g) == 2:
            a, b = g.iloc[0], g.iloc[1]
            print(f"  {approach}: RR gap {100*abs(a.rr-b.rr):.2f}pp, "
                  f"RPS gap {abs(a.rps-b.rps):.3f}, "
                  f"cost ratio {max(a.usd_per_sub, b.usd_per_sub)/max(1e-9, min(a.usd_per_sub, b.usd_per_sub)):.2f}x")

    if args.tex:
        Path(args.tex).write_text(to_tex(diff) + "\n")
        print(f"\nLaTeX fragment -> {args.tex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
