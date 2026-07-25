"""Six-method comparison over the sampled smoke set: one table per Refactory
assignment plus an overall table.

Every arm is restricted to the *same* sampled submissions, so the columns are
paired. The one exception is Refactory itself: its results on its own corpus
are quoted from the published paper as per-problem aggregates, so it cannot be
subset and its row is the full-set number, marked with a dagger.

Usage: python3 -m src.experiments.sample_report [--ver sample] [--base v2]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PIDS = [f"refactory_q{i}" for i in range(1, 6)]
COEP = ["CoEP_L", "CoEP_LF", "CoEP_L+SL"]
MODELS = ["gpt-5.4-mini", "claude-sonnet-5"]


def _events(path: Path, ids: set[str]) -> pd.DataFrame | None:
    if not path.exists():
        return None
    d = pd.read_csv(path)
    d = d[d.Buggy.astype(str).isin(ids)]
    return d if len(d) else None


def _stats(d: pd.DataFrame, build_usd: float = 0.0,
           w: dict[str, float] | None = None) -> dict:
    """Sample statistics, reweighted to the corpus when weights are given.

    The set is stratified and deliberately over-samples the strata that decide
    the outcome, so a raw sample mean is not a corpus estimate: q2's miss
    stratum is 13 of 60 sampled but 38 of 417 in the corpus. Each submission
    carries its stratum's (cell size / sampled) weight, which undoes that.
    """
    n = len(d)
    if not n:
        return {"N": 0, "RR": 0.0, "RPS": float("nan"), "ATT": float("nan"),
                "BUILD": build_usd, "API": 0.0}
    wt = (d.Buggy.astype(str).map(lambda b: (w or {}).get(b, 1.0))
          if w else pd.Series(1.0, index=d.index))
    fixed = d.Fixed.astype(bool)
    tw = wt.sum()
    rep_w = wt[fixed].sum()
    return {"N": n, "RR": rep_w / tw,
            "RPS": (wt[fixed] * d.RPS[fixed]).sum() / rep_w if rep_w else float("nan"),
            "ATT": (wt * d.ATT_all).sum() / tw,
            # Build and deployment spend stay in separate columns: the whole
            # argument is that one is paid once and the other scales with N.
            "BUILD": build_usd, "API": d["$API"].sum()}


def weight_of(meta: dict, pid: str) -> dict[str, float]:
    """Per-submission corpus weight: its stratum's size divided by how many of
    that stratum were sampled."""
    m = meta.get(pid, {})
    weights, cell = m.get("weights", {}), m.get("member_cell", {})
    return {b: weights.get(c, 1.0) for b, c in cell.items()}


def rows_for(pid: str, ids: set[str], ver: str, base: str,
             w: dict[str, float] | None = None) -> list[dict]:
    out: list[dict] = []
    # Refactory: published per-problem aggregate, not subsettable.
    summ = pd.read_csv(ROOT / "results" / base / pid / "summary.csv")
    r = summ[summ.Approach == "Refactory"]
    if len(r):
        r = r.iloc[0]
        out.append({"method": "Refactory†", "model": "--", "N": int(r.N),
                    "RR": float(r.RR), "RPS": float(r.RPS),
                    "ATT": float(r.ATT_all), "BUILD": 0.0,
                    "API": float(r["$API"])})
    for arm, label in (("pydex", "PyDex"), ("pydex_pc", "PyDex_PC")):
        d = _events(ROOT / "results" / base / pid / f"{arm}.csv", ids)
        if d is not None:
            out.append({"method": label, "model": "sonnet", **_stats(d, w=w)})
    for arm in COEP:
        f = ROOT / "results" / ver / pid / (arm.lower().replace("+", "_") + ".csv")
        d0 = _events(f, ids)
        if d0 is None:
            continue
        for model in MODELS:
            d = d0[d0.Model == model]
            if not len(d):
                continue
            s = pd.read_csv(ROOT / "results" / ver / pid / "summary.csv")
            row = s[(s.Approach == arm) & (s.Model == model)]
            build = float(row.iloc[0]["$Build"]) if len(row) else 0.0
            out.append({"method": arm,
                        "model": "mini" if "mini" in model else "sonnet",
                        **_stats(d, build, w=w)})
    return out


def render(title: str, rows: list[dict]) -> str:
    head = (f"### {title}\n\n"
            "| method | model | N | RR | RPS | ATT (s) | $Build | $API | "
            "$Total |\n|---|---|---:|---:|---:|---:|---:|---:|---:|")
    lines = [head]
    for r in rows:
        rps = "--" if r["RPS"] != r["RPS"] else f"{r['RPS']:.3f}"
        lines.append(f"| {r['method']} | {r['model']} | {r['N']:,} | "
                     f"{100*r['RR']:.2f}% | {rps} | {r['ATT']:.2f} | "
                     f"${r['BUILD']:.4f} | ${r['API']:.4f} | "
                     f"${r['BUILD']+r['API']:.4f} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", default="sample")
    ap.add_argument("--base", default="v2")
    ap.add_argument("--subset", default="data/smoke_set.json")
    args = ap.parse_args(argv)

    doc = json.loads(Path(args.subset).read_text())
    manifest, meta = doc["problems"], doc["_meta"]["per_problem"]
    per_problem: dict[str, list[dict]] = {}
    for pid in PIDS:
        ids = set(map(str, manifest.get(pid, [])))
        rows = rows_for(pid, ids, args.ver, args.base, weight_of(meta, pid))
        if rows:
            per_problem[pid] = rows
            print(render(f"{pid} (sampled n={len(ids)})", rows), "\n")

    # Overall: each assignment enters weighted by its corpus pool, not by how
    # many of it were sampled, so the five contribute in their real proportions.
    keys, agg = [], {}
    for pid, rows in per_problem.items():
        pool = meta.get(pid, {}).get("pool", 0) or 1
        for r in rows:
            k = (r["method"], r["model"])
            if k not in agg:
                agg[k] = {"N": 0, "W": 0.0, "rep": 0.0, "rps_w": 0.0,
                          "att_w": 0.0, "BUILD": 0.0, "API": 0.0}
                keys.append(k)
            a = agg[k]
            # Refactory's row is a full-set aggregate; weight it by its own N.
            w = r["N"] if r["method"].startswith("Refactory") else pool
            rep = w * r["RR"]
            a["N"] += r["N"]; a["W"] += w; a["rep"] += rep
            a["rps_w"] += rep * (0 if r["RPS"] != r["RPS"] else r["RPS"])
            a["att_w"] += w * r["ATT"]
            a["BUILD"] += r["BUILD"]; a["API"] += r["API"]
    overall = [{"method": m, "model": mo, "N": a["N"], "RR": a["rep"] / a["W"],
                "RPS": a["rps_w"] / a["rep"] if a["rep"] else float("nan"),
                "ATT": a["att_w"] / a["W"],
                "BUILD": a["BUILD"], "API": a["API"]}
               for (m, mo), a in ((k, agg[k]) for k in keys)]
    print(render("Overall (five assignments, N-weighted)", overall))
    print("\n† Refactory is quoted from its published per-problem results over "
          "the full buggy set; it cannot be restricted to the sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
