"""Enter Refactory's published numbers (its own corpus) into the unified
summary CSVs, per protocol: on refactory_q1..q5 we do not re-run the tool —
RR/RPS (and per-problem time, once supplied) come verbatim from the paper's
strongest configuration.

RR/RPS below are the figures confirmed from the paper; ATT_cpu is left 0.0
until the per-problem time values are supplied (fill PUBLISHED and re-run).

Usage: python3 -m src.experiments.refactory_published
"""
from __future__ import annotations

from src.experiments.results_io import build_overall, upsert_summary

# pid: (N_wrong, RR, RPS, ATT_cpu_seconds)
PUBLISHED = {
    "refactory_q1": (575, 0.9896, 0.39, 0.0),
    "refactory_q2": (435, 0.7816, 0.56, 0.0),
    "refactory_q3": (308, 0.9740, 0.34, 0.0),
    "refactory_q4": (357, 0.8824, 0.31, 0.0),
    "refactory_q5": (108, 0.8796, 0.32, 0.0),
}


def main(argv=None) -> int:
    for pid, (n, rr, rps, att) in PUBLISHED.items():
        upsert_summary("v2", pid, {
            "Approach": "Refactory", "Model": "none", "N": n,
            "RR": rr, "RPS": rps,
            "ATT_all": att, "ATT_cpu": att, "ATT_api": 0.0,
            "ATT_build": 0.0, "InT": 0, "OuT": 0,
            "$API": 0.0, "$Build": 0.0,
            "Rules_build": "[]", "Rules_add": "[]", "Rules_used": "{}",
        })
        print(f"[{pid}] Refactory published: RR={rr} RPS={rps}")
    build_overall("v2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
