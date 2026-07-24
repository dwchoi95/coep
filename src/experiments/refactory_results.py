"""Collect the Refactory tool's CSVs into the unified results/v2 layout.

Writes ``results/v2/baselines/refactory/<pid>/{events.jsonl, summary.json}``
with the same field names as ``run.py compare``'s CoEP output, so every
approach is tabulated from one directory tree:

* events.jsonl — one line per buggy submission: file, status (their Status
  column; ``not_exported`` for programs the adapter could not hand them),
  repaired, rps, t_cpu (their Total Time; their pipeline is pure CPU).
* summary.json — RR over the full shared denominator (unexported = failure,
  the tool cannot attempt them) plus RR_adapted over what it could attempt;
  mean RPS over repairs; ATT_cpu/ATT_all; zeros for the LLM columns.

Usage: python3 -m src.experiments.refactory_results cf_125A [cf_110A ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def collect(pid: str, out_root: str = "results/v2") -> dict:
    csv = ROOT / "baselines" / "refactory" / "data_cf" / pid / "refactory_online.csv"
    df = pd.read_csv(csv)
    exported = set(df["File Name"])
    all_buggy = sorted(p.name for p in (ROOT / "data" / pid / "buggy").glob("*.py"))

    out = ROOT / out_root / "baselines" / "refactory" / pid
    out.mkdir(parents=True, exist_ok=True)

    n = len(all_buggy)
    repaired = 0
    rps_sum = 0.0
    t_sum = 0.0
    with (out / "events.jsonl").open("w") as ev:
        rows = {r["File Name"]: r for _, r in df.iterrows()}
        for name in all_buggy:
            if name not in rows:
                ev.write(json.dumps({"file": name, "status": "not_exported",
                                     "repaired": False}) + "\n")
                continue
            r = rows[name]
            ok = str(r["Status"]).startswith("success")
            e = {"file": name, "status": r["Status"], "repaired": ok,
                 "t_cpu": round(float(r["Total Time"]), 3)}
            t_sum += float(r["Total Time"])
            if ok:
                repaired += 1
                rps = float(r["RPS"]) if pd.notna(r["RPS"]) else None
                if rps is not None:
                    rps_sum += rps
                    e["rps"] = round(rps, 3)
            ev.write(json.dumps(e) + "\n")

    n_att = len(exported)
    summary = {
        "pid": pid, "approach": "Refactory",
        "n_programs": n, "n_attempted": n_att,
        "arms": {"Refactory": {
            "n": n, "repaired": repaired,
            "RR": round(100 * repaired / max(1, n), 2),
            "RR_adapted": round(100 * repaired / max(1, n_att), 2),
            "RPS": round(rps_sum / max(1, repaired), 3),
            "ATT_cpu": round(t_sum / max(1, n_att), 3),
            "ATT_api": 0.0,
            "ATT_all": round(t_sum / max(1, n_att), 3),
            "InT": 0.0, "OuT": 0.0, "USD": 0.0,
        }},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pids", nargs="+")
    args = ap.parse_args(argv)
    for pid in args.pids:
        s = collect(pid)
        a = s["arms"]["Refactory"]
        print(f"[{pid}] RR={a['RR']}% (adapted {a['RR_adapted']}%) "
              f"RPS={a['RPS']} ATT={a['ATT_cpu']}s -> "
              f"results/v2/baselines/refactory/{pid}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
