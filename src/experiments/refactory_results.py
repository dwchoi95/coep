"""Collect the Refactory tool's CSVs into the agreed unified format:

    results/<ver>/<p_id>/refactory.csv   one row per buggy submission
    results/<ver>/<p_id>/summary.csv     upserted (Approach=Refactory, Model=none)

Source is ``reference`` on success (Refactory's mechanism *is* reference
reuse) and ``none`` otherwise; submissions the adapter could not export are
rows with Fixed=False (shared full denominator). Refactory has no LLM columns
(ATT_api/InT/OuT/$API/$Build = 0) and no rules.

Usage: python3 -m src.experiments.refactory_results cf_125A [cf_110A ...]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.experiments.results_io import (build_overall, event_row,
                                        summarize_events, upsert_summary,
                                        write_events)

ROOT = Path(__file__).resolve().parents[2]


def collect(pid: str, ver: str = "v2") -> dict:
    csv = ROOT / "baselines" / "refactory" / "data_cf" / pid / "refactory_online.csv"
    df = pd.read_csv(csv, keep_default_na=False)
    by_name = {r["File Name"]: r for _, r in df.iterrows()}
    all_buggy = sorted(p.name for p in (ROOT / "data" / pid / "buggy").glob("*.py"))

    rows = []
    for name in all_buggy:
        stem = name[:-3]
        r = by_name.get(name)
        if r is None:                          # adapter could not export it
            rows.append(event_row(stem, "none", "none", False))
            continue
        ok = str(r["Status"]).startswith("success")
        patch = str(r.get("Repair", "")) if ok else None
        rps = None
        if ok and str(r["RPS"]).strip() not in ("", "nan"):
            rps = float(r["RPS"])
        rows.append(event_row(stem, "none", "reference" if ok else "none", ok,
                              patch, rps, att_cpu=float(r["Total Time"])))

    write_events(ver, pid, "refactory", rows)
    summ = summarize_events("Refactory", "none", rows)
    upsert_summary(ver, pid, summ)
    return summ


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pids", nargs="+")
    ap.add_argument("--ver", default="v2")
    args = ap.parse_args(argv)
    for pid in args.pids:
        try:
            s = collect(pid, args.ver)
        except Exception as e:                     # noqa: BLE001
            print(f"[{pid}] collect FAILED: {type(e).__name__}: {e}")
            continue
        print(f"[{pid}] Refactory RR={s['RR']} RPS={s['RPS']} "
              f"ATT_cpu={s['ATT_cpu']}s -> results/{args.ver}/{pid}/")
    build_overall(args.ver)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
