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

from src.experiments._common import tool_path
from src.experiments.tables import (BANDS, CHEAP, FRONTIER, IDS, ORDER,
                                    PAPER, ROOT, _cell, _meta, _summary)

OUT = PAPER / "figures"
# colour-blind safe, and legible in grayscale by ordering lightness
C = {"rules": "#1f4e79", "reference": "#2e8b57", "llm": "#e8a33d",
     "none": "#c0392b"}


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
    """Cumulative dollars for one assignment against its enrollment.

    Six lines rather than three, because the paper reports every arm on both
    models and a single-model plot invites the reader to assume the other
    behaves the same. Turnaround is a table, not a second panel: it is four
    numbers per arm and a plot of it wastes the width this one needs.
    """
    plt = _mpl()
    import numpy as np
    fig, ax = plt.subplots(figsize=(3.35, 2.15))

    ARMS = [("PyDex", "PyDex", "#c0392b"),
            (r"PyDex$_{PC}$", "PyDex_PC", "#2e8b57"),
            (r"CoEP$_{LF}$", "CoEP_LF", "#1f4e79")]
    MODELS = [(FRONTIER, "-", 1.5, "claude-sonnet-5"),
              (CHEAP, ":", 1.4, "gpt-5.4-mini")]

    def totals(approach, model):
        n = usd = build = 0.0
        for pid in ORDER:
            c = _cell(_summary(ver, pid), approach, model)
            if c is None:
                continue
            n += int(c["N"])
            usd += float(c["$API"]); build += float(c["$Build"])
        return usd / max(n, 1), build / len(ORDER)

    x = np.linspace(0, 700, 400)
    for model, ls, lw, tag in MODELS:
        tail, cbuild = totals("CoEP_LF", model)
        crossings = []
        for label, approach, col in ARMS:
            slope, b = totals(approach, model)
            ax.plot(x, b + slope * x, ls, color=col, lw=lw, zorder=3)
            if approach == "CoEP_LF" or slope <= tail:
                continue
            xs = (cbuild - b) / (slope - tail)
            crossings.append(xs)
            ax.plot([xs], [cbuild + tail * xs], "o", ms=3, color=col, zorder=5)
        if crossings:
            # the two baselines cross within a submission or two of each other,
            # so one label for the pair rather than two that overprint
            xm = sum(crossings) / len(crossings)
            ax.annotate("$N^*$=" + ",".join(f"{c:.0f}" for c in sorted(crossings)),
                        (xm, cbuild + tail * xm), fontsize=6, color="#333333",
                        textcoords="offset points", xytext=(8, 4))
    sizes = [int(_cell(_summary(ver, p), "CoEP_L", FRONTIER)["N"]) for p in ORDER]
    ax.plot(sizes, [0.024] * len(sizes), "|", color="#333333", ms=6, mew=0.9,
            zorder=5, clip_on=False)
    ax.annotate("assignment sizes", (350, 0.030), fontsize=5.5, color="#333333",
                ha="center")
    ax.set_xlabel("submissions per assignment")
    ax.set_ylabel(r"cumulative $C_{\mathrm{tot}}$ for one assignment (log)",
                  fontsize=7)
    ax.set_xlim(0, 700)
    # log y, because the two structures differ by two orders of magnitude and a
    # linear axis renders CoEP as the x axis and hides where the lines cross
    ax.set_yscale("log")
    ax.set_ylim(0.02, 200)
    ax.grid(alpha=0.25, linewidth=0.4)
    arms = ax.legend(handles=[plt.Line2D([], [], color=c, lw=1.5, label=l)
                              for l, _a, c in ARMS],
                     fontsize=6, frameon=False, loc="upper left",
                     handlelength=1.5, labelspacing=0.25, borderaxespad=0.3)
    ax.add_artist(arms)
    ax.legend(handles=[plt.Line2D([], [], color="#777777", lw=1.5, ls="-",
                                  label="claude-sonnet-5"),
                       plt.Line2D([], [], color="#777777", lw=1.4, ls=":",
                                  label="gpt-5.4-mini")],
              fontsize=6, frameon=False, loc="lower right",
              handlelength=1.5, labelspacing=0.25, borderaxespad=0.3)

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_cost.pdf"
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_source(ver: str) -> Path:
    plt = _mpl()
    import numpy as np
    fig, ax = plt.subplots(figsize=(3.35, 2.3))
    keys = ["rules", "reference", "llm", "none"]
    # the three strategies of the Repair section, plus what none of them reached
    names = {"rules": "Rules", "reference": "Reference", "llm": "LLM",
             "none": "Failed"}
    mat = {k: [] for k in keys}
    labels = []
    for pid in ORDER:
        labels.append(IDS[pid])
        cnt = {k: 0 for k in keys}
        lf = pd.read_csv(ROOT / "results" / ver / pid / "coep_lf.csv",
                         keep_default_na=False)
        for _i, r in lf.iterrows():
            if not r["Fixed"]:
                cnt["none"] += 1
            elif r["Source"] in cnt:
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
    ax.set_ylabel("share of submissions (%)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=6, frameon=False, ncol=4, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), handlelength=1.1, columnspacing=1.4)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_source.pdf"
    fig.savefig(p)
    plt.close(fig)
    return p



def fig_learn(ver: str) -> Path:
    """RQ4 over the submissions the frozen tool failed on.

    Three bars on the same 56 programs: what the tool alone did, what the
    fallback then did, and what the rules distilled from those repairs do with
    no model at all. A funnel would have to change units halfway through, from
    submissions to rules, so the rule count is an annotation instead.
    """
    import re
    plt = _mpl()
    import numpy as np
    fig, ax = plt.subplots(figsize=(3.35, 1.35))

    failed = attempted = kept = recovered = 0
    for m in (FRONTIER, CHEAP):
        for pid in ORDER:
            l = pd.read_csv(ROOT / "results" / ver / pid / "coep_l.csv",
                            keep_default_na=False)
            l = l[l.Model == m]
            miss = set(l[~l.Fixed.astype(bool)].Buggy.astype(str))
            failed += len(miss)
            if not miss:
                continue
            lf = pd.read_csv(ROOT / "results" / ver / pid / "coep_lf.csv",
                             keep_default_na=False)
            lf = lf[(lf.Model == m) & lf.Buggy.astype(str).isin(miss)]
            attempted += int(lf.Fixed.astype(bool).sum())
            learned = tool_path(pid, m, "tools").parent / "sl" / "learned.py"
            if learned.exists():
                kept += len(re.findall(r'Rule\("([^"]+)"', learned.read_text()))
            f = ROOT / "results" / ver / pid / "coep_l_sl.csv"
            if not f.exists():
                continue
            sl = pd.read_csv(f, keep_default_na=False)
            sl = sl[sl.Model == m]
            recovered += len(set(sl[sl.Fixed.astype(bool)].Buggy.astype(str)) & miss)

    bars = [(r"CoEP$_{L}$", 0), (r"+ fallback LLM", attempted),
            (r"+ learned rules", recovered)]
    y = np.arange(len(bars))[::-1]
    for yy, (_lab, got) in zip(y, bars):
        ax.barh(yy, got, height=0.62, color="#1f4e79")
        ax.barh(yy, failed - got, left=got, height=0.62, color="#e6e6e6")
        if got:
            ax.text(got / 2, yy, str(got), fontsize=6.5, va="center",
                    ha="center", color="white")
        ax.text(failed - 0.6, yy, f"{failed - got} left", fontsize=6,
                va="center", ha="right", color="#555555")
    ax.set_yticks(y)
    ax.set_yticklabels([b[0] for b in bars], fontsize=7)
    ax.set_xlim(0, failed)
    ax.set_xlabel(f"submissions CoEP$_L$ failed to repair "
                  f"({failed} of 5,940)", fontsize=7)
    ax.set_xticks([])
    ax.tick_params(labelsize=6)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(f"{attempted} induction attempts kept {kept} rules",
                 fontsize=6.5, color="#555555", pad=3)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "fig_learn.pdf"
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
    print(" ", fig_learn(args.ver))
    print(" ", fig_gate(args.ver, Path(args.sweep) if args.sweep else None))
    return 0
