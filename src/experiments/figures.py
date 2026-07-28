"""`run.py figures` — regenerate the paper's figures from results/.

Three figures, each carrying one claim the tables cannot:

  fig_cost    where the arms sit in the turnaround/spend plane, and where
              amortization overtakes per-submission inference
  fig_source  which mechanism repaired what, assignment by assignment
  fig_gate    every escalation-threshold setting against the baselines, so the
              reader can see that the choice does not move the conclusion

Writes paper/figures/*.pdf.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.experiments.tables import (BANDS, CHEAP, FRONTIER, IDS, ORDER,
                                    PAPER, ROOT, _cell, _meta, _summary)

OUT = PAPER / "figures"
# colour-blind safe, and legible in grayscale by ordering lightness
C = {"authored": "#1f4e79", "generic": "#5b9bd5", "reference": "#a6c8e8",
     "noop": "#d9d9d9", "llm": "#e8a33d", "none": "#f2f2f2"}


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "font.family": "serif",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.dpi": 200, "savefig.bbox": "tight",
                         "savefig.pad_inches": 0.02})
    return plt


def _tot(ver, approach, model):
    n = 0
    att = usd = 0.0
    for pid in ORDER:
        c = _cell(_summary(ver, pid), approach, model)
        if c is None:
            continue
        nn = int(c["N"])
        n += nn
        att += float(c["ATT_all"]) * nn
        usd += float(c["$API"]) + float(c["$Build"])
    return att / max(n, 1), usd, n


def fig_cost(ver: str) -> Path:
    plt = _mpl()
    fig, ax2 = plt.subplots(figsize=(3.35, 2.15))

    # --- break-even: cumulative dollars against submissions per assignment
    n_probs = len(ORDER)
    _a, coep_usd, n_tot = _tot(ver, "CoEP_LF", FRONTIER)
    build = sum(float(_cell(_summary(ver, p), "CoEP_L", FRONTIER)["$Build"])
                for p in ORDER) / n_probs
    tail = 0.0
    for p in ORDER:
        c = _cell(_summary(ver, p), "CoEP_LF", FRONTIER)
        tail += float(c["$API"])
    tail_per_sub = tail / max(n_tot, 1)
    per_sub = {}
    for label, approach, col, ls in (("PyDex", "PyDex", "#c0392b", "-"),
                                     (r"PyDex$_{PC}$", "PyDex_PC", "#e07b6a", "--")):
        u = sum(float(_cell(_summary(ver, p), approach, FRONTIER)["$API"])
                for p in ORDER)
        per_sub[label] = (u / max(n_tot, 1), col, ls)

    import numpy as np
    x = np.linspace(0, 700, 400)
    for label, (slope, col, ls) in per_sub.items():
        ax2.plot(x, slope * x, ls, color=col, lw=1.3, label=label)
    ax2.plot(x, build + tail_per_sub * x, "-", color="#1f4e79", lw=1.6,
             label=r"CoEP$_{LF}$")
    for k, (label, (slope, col, _ls)) in enumerate(per_sub.items()):
        if slope <= tail_per_sub:
            continue
        xstar = build / (slope - tail_per_sub)
        if xstar >= x[-1]:
            continue
        ax2.plot([xstar], [build + tail_per_sub * xstar], "o", ms=4,
                 color=col, zorder=4)
        ax2.annotate(f"$N^*$ = {xstar:.0f}", (xstar, build + tail_per_sub * xstar),
                     textcoords="offset points", xytext=(8, 6 - 12 * k),
                     fontsize=6, color=col)
    sizes = [int(_cell(_summary(ver, p), "CoEP_L", FRONTIER)["N"]) for p in ORDER]
    ax2.plot(sizes, [0.024] * len(sizes), "|", color="#333333", ms=6, mew=0.9,
             zorder=5, clip_on=False)
    ax2.annotate("assignment sizes", (350, 0.028), fontsize=5.5,
                 color="#333333", ha="center")
    ax2.set_xlabel("submissions per assignment")
    ax2.set_ylabel("cumulative USD for one assignment (log)")
    ax2.set_xlim(0, 700)
    # log y, because the two structures differ by two orders of magnitude and a
    # linear axis renders CoEP as the x axis and hides where the lines cross
    ax2.set_yscale("log")
    ax2.set_ylim(0.02, 200)
    ax2.grid(alpha=0.25, linewidth=0.4)
    ax2.legend(fontsize=6.5, frameon=False, loc="lower right")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_cost.pdf"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_source(ver: str) -> Path:
    plt = _mpl()
    import numpy as np
    fig, ax = plt.subplots(figsize=(3.35, 2.3))
    keys = ["authored", "generic", "reference", "noop", "llm", "none"]
    names = {"authored": "authored rules", "generic": "generic rules",
             "reference": "transplant", "noop": "already passing",
             "llm": "LLM fallback", "none": "unrepaired"}
    mat = {k: [] for k in keys}
    labels = []
    for pid in ORDER:
        labels.append(IDS[pid])
        authored = set(json.loads(_cell(_summary(ver, pid), "CoEP_L",
                                        FRONTIER)["Rules_build"]))
        lf = pd.read_csv(ROOT / "results" / ver / pid / "coep_lf.csv",
                         keep_default_na=False)
        lf = lf[lf["Model"] == FRONTIER]
        cnt = {k: 0 for k in keys}
        for _i, r in lf.iterrows():
            if not r["Fixed"]:
                cnt["none"] += 1
            elif r["Source"] == "rules":
                nm = json.loads(r["Rules_L"])
                cnt["authored" if any(n in authored for n in nm) else "generic"] += 1
            elif r["Source"] in ("reference", "noop", "llm"):
                cnt[r["Source"]] += 1
        tot = max(sum(cnt.values()), 1)
        for k in keys:
            mat[k].append(100 * cnt[k] / tot)
    x = np.arange(len(ORDER))
    bottom = np.zeros(len(ORDER))
    for k in keys:
        v = np.array(mat[k])
        ax.bar(x, v, bottom=bottom, color=C[k], label=names[k], width=0.74,
               edgecolor="white", linewidth=0.3)
        bottom += v
    ax.axvline(4.5, color="#555555", lw=0.7, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("share of submissions (\\%)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=5.6, frameon=False, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), handlelength=1.1, columnspacing=0.9)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_source.pdf"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_gate(ver: str, sweep: Path | None) -> Path:
    """Every threshold setting against the baselines it is compared to."""
    plt = _mpl()
    fig, ax = plt.subplots(figsize=(3.35, 2.4))
    if sweep and sweep.exists():
        pts = json.loads(sweep.read_text())
        xs = [p["usd"] for p in pts]
        ys = [p["rps"] for p in pts]
        ax.scatter(xs, ys, s=13, color="#2e86c1", alpha=0.75, zorder=3,
                   label=f"threshold settings ({len(pts)})", edgecolor="none")
    # The shipped point is the canonical CoEP_LF run, not the sweep's
    # reconstruction of it, so the paper never carries two numbers for one
    # configuration. The sweep's own points share one cached fallback.
    rep = rps = 0
    usd = 0.0
    for pid in ORDER:
        c = _cell(_summary(ver, pid), "CoEP_LF", FRONTIER)
        if c is None:
            continue
        k = round(float(c["RR"]) * int(c["N"]))
        rep += k
        rps += float(c["RPS"]) * k
        usd += float(c["$API"]) + float(c["$Build"])
    ax.scatter([usd], [rps / max(rep, 1)], s=62, marker="*", color="#1f4e79",
               zorder=6, label=r"shipped: $\mathrm{RPS}>1$")
    for approach, model, label, col, mk in (
            ("PyDex", FRONTIER, "PyDex", "#c0392b", "s"),
            ("PyDex_PC", FRONTIER, r"PyDex$_{PC}$", "#e07b6a", "D"),
            ("PyDex", CHEAP, "PyDex (mini)", "#7b3f9e", "s"),
            ("CoEP_L", FRONTIER, r"CoEP$_L$", "#1e8449", "^"),
            ("Refactory", "none", "Refactory", "#444444", "o")):
        _a, usd, n = _tot(ver, approach, model)
        c = None
        rep = rps = 0
        for pid in ORDER:
            cc = _cell(_summary(ver, pid), approach, model)
            if cc is None:
                continue
            k = round(float(cc["RR"]) * int(cc["N"]))
            rep += k
            rps += float(cc["RPS"]) * k
        ax.scatter([max(usd, 0.05)], [rps / max(rep, 1)], s=46, marker=mk,
                   color=col, zorder=4, label=label, edgecolor="white",
                   linewidth=0.4)
    ax.set_xscale("log")
    ax.set_xlabel("total API spend for the benchmark (USD, log)")
    ax.set_ylabel("mean RPS")
    ax.grid(alpha=0.25, linewidth=0.4)
    ax.legend(fontsize=6, frameon=False, loc="upper left", handletextpad=0.3)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_gate.pdf"
    fig.savefig(p)
    plt.close(fig)
    return p


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py figures")
    ap.add_argument("--ver", default="v2")
    ap.add_argument("--sweep", default="", help="JSON of threshold-sweep points")
    args = ap.parse_args(argv)
    print(" ", fig_cost(args.ver))
    print(" ", fig_source(args.ver))
    print(" ", fig_gate(args.ver, Path(args.sweep) if args.sweep else None))
    return 0
