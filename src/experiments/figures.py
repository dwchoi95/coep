"""`run.py figures` — draw the paper's figures from results/ (dev branch only).

One figure per research question, two panels each, at the text width of the
acmsmall format, in color that stays legible in grayscale (PLDI's CFP):

  fig_effect   repair rate by difficulty band; patch size on the common pairs
  fig_cost     cumulative spend against class size, per builder (N*)
  fig_source   what repaired each assignment; how deep the rule compositions go
  fig_general  building on the first f of a class (replaces a table)
  fig_heldout  repair rate on T and on the held-out suite (replaces a table)

Writes paper/figures/*.pdf.
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess

import numpy as np
import pandas as pd

from src.experiments.tables import (BANDS, CHEAP, FRONTIER, IDS, ORDER, PAPER,
                                    ROOT, _cell, _summary)

OUT = PAPER / "figures"
RES = ROOT / "results"
W = 5.45                 # acmsmall \textwidth, in inches
LIB = "/usr/local/texlive/2024/texmf-dist/fonts/opentype/public/libertine/"
MODELS = ((FRONTIER, "claude-sonnet-5"), (CHEAP, "gpt-5.4-mini"))
# arm -> (label, color, hatch): Okabe-Ito hues, CoEP in blues and the
# baselines in warm colors; the colors also differ in lightness, and the hatches
# and line styles stay (baselines hatched, CoEP solid), so a grayscale print
# still tells the arms apart
BLUE, SKY, ORANGE, RED, PURPLE = "#0072B2", "#56B4E9", "#E69F00", "#D55E00", "#CC79A7"
ARM = {"Refactory": ("Refactory", ORANGE, "////"),
       "PyDex": ("PyDex", RED, "\\\\\\\\"),
       "LLM_Direct": (r"LLM$_{\mathrm{Direct}}$", PURPLE, "...."),
       "CoEP_L": (r"CoEP$_{\mathrm{L}}$", SKY, ""),
       "CoEP_LF": (r"CoEP$_{\mathrm{LF}}$", BLUE, "")}


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    for f in ("LinLibertine_R.otf", "LinLibertine_RI.otf", "LinLibertine_RB.otf"):
        fm.fontManager.addfont(LIB + f)
    # the body font of acmart; embedded as CFF, never Type 3
    plt.rcParams.update({
        "font.family": "Linux Libertine O", "font.size": 8,
        "mathtext.fontset": "custom", "mathtext.rm": "Linux Libertine O",
        "mathtext.it": "Linux Libertine O:italic",
        "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "hatch.linewidth": 0.5, "legend.frameon": False, "legend.fontsize": 7,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.01})
    return plt


def _save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.pdf"
    raw = p.with_suffix(".raw.pdf")
    fig.savefig(raw)
    # matplotlib embeds the OpenType font in a way PDF readers flag as a type
    # mismatch; Ghostscript rewrites it as a plain CFF font
    subprocess.run(["gs", "-q", "-o", str(p), "-sDEVICE=pdfwrite",
                    "-dEmbedAllFonts=true", str(raw)], check=True)
    raw.unlink()
    print(" ", p.relative_to(ROOT))


def _log(pid: str, stem: str) -> pd.DataFrame:
    d = pd.read_csv(RES / pid / f"{stem}.csv", keep_default_na=False)
    d["ok"] = d.Fixed.astype(str) == "True"
    return d


def _sub(fig, axes, labels):
    """Sub-captions "(a) ..." centered under the panels, all on one line."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    y = min(ax.get_tightbbox(r).transformed(fig.transFigure.inverted()).y0
            for ax in axes)
    for ax, s in zip(axes, labels):
        p = ax.get_position()
        fig.text((p.x0 + p.x1) / 2, y - 0.03, s, ha="center", va="top", fontsize=8)


def fig_effect():
    """(a) the gap to Refactory widens with difficulty; (b) patch sizes."""
    plt = _mpl()
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 1.75),
                               gridspec_kw={"width_ratios": [1.15, 1]})
    arms = ["Refactory", "PyDex", "CoEP_L", "CoEP_LF"]
    x = np.arange(len(BANDS))
    w = 0.2
    for i, arm in enumerate(arms):
        rr = []
        for _name, pids in BANDS:
            n = k = 0
            for pid in pids:
                for m in (["none"] if arm == "Refactory" else [FRONTIER, CHEAP]):
                    c = _cell(_summary("", pid), arm, m)
                    nn = int(c["N"]) * (2 if arm == "Refactory" else 1)
                    n += nn; k += float(c["RR"]) * nn
            rr.append(100 * k / n)
        lab, face, hatch = ARM[arm]
        bars = a.bar(x + (i - 1.5) * w, rr, w, color=face, hatch=hatch,
                     edgecolor="black", linewidth=0.5, label=lab)
        a.bar_label(bars, fmt="%.0f", fontsize=5.5, padding=1)
    a.set_xticks(x, ["CS1", "CF 800–1000", "CF 1200–2000"])
    a.set_ylim(40, 122)
    a.set_yticks([40, 60, 80, 100])
    a.set_ylabel("repair rate (%)")
    a.legend(ncol=4, loc="upper center", handlelength=1.2, columnspacing=0.8,
             handletextpad=0.4, borderaxespad=0.1)

    # RPS on the programs all three arms repaired, per builder pair
    rps = {k: [] for k in ("Refactory", "PyDex", "CoEP_LF")}
    for pid in ORDER:
        ref = _log(pid, "refactory").set_index("Buggy")
        for m, _ in MODELS:
            px = _log(pid, "pydex"); px = px[px.Model == m].set_index("Buggy")
            lf = _log(pid, "coep_lf"); lf = lf[lf.Model == m].set_index("Buggy")
            common = [s for s in lf.index
                      if lf.ok[s] and px.ok.get(s, False) and ref.ok.get(s, False)]
            for k, d in (("Refactory", ref), ("PyDex", px), ("CoEP_LF", lf)):
                rps[k] += pd.to_numeric(d.loc[common, "RPS"]).tolist()
    style = {"Refactory": ("--", ORANGE, 1.2), "PyDex": (":", RED, 1.4),
             "CoEP_LF": ("-", BLUE, 1.4)}
    for k, v in rps.items():
        v = np.sort(v)
        ls, col, lw = style[k]
        b.step(v, np.arange(1, len(v) + 1) / len(v), where="post", ls=ls,
               color=col, lw=lw, label=f"{ARM[k][0]} (mean {np.mean(v):.3f})")
    b.set_xlim(0, 1.5)
    b.set_ylim(0, 1.0)
    b.set_xlabel("relative patch size")
    b.set_ylabel("cumulative share")
    b.legend(loc="lower right", handlelength=1.8)
    print(f"    fig_effect: {len(rps['CoEP_LF']):,} pairs repaired by all three")
    fig.tight_layout(w_pad=1.5)
    _sub(fig, (a, b), ("(a) Repair rate by difficulty",
                       "(b) Patch size on the common pairs"))
    _save(fig, "fig_effect")
    plt.close(fig)


def fig_cost():
    """Cumulative spend for one assignment of n buggy submissions."""
    plt = _mpl()
    fig, axes = plt.subplots(1, 2, figsize=(W, 1.75), sharey=True)
    arms = [("PyDex", "-", RED, 1.0), ("PyDex_PC", "--", RED, 1.0),
            ("LLM_Direct", ":", PURPLE, 1.4), ("CoEP_LF", "-", BLUE, 1.6)]
    label = {"PyDex": "PyDex", "PyDex_PC": r"PyDex$_{\mathrm{PC}}$",
             "LLM_Direct": ARM["LLM_Direct"][0], "CoEP_LF": ARM["CoEP_LF"][0]}
    sizes = [int(_cell(_summary("", p), "CoEP_L", FRONTIER)["N"]) for p in ORDER]
    x = np.logspace(0, 3, 300)
    for ax, (m, name) in zip(axes, MODELS):
        per, build = {}, 0.0
        for arm, *_ in arms:
            api = n = 0.0
            for pid in ORDER:
                c = _cell(_summary("", pid), arm, m)
                api += float(c["$API"]); n += int(c["N"])
                if arm == "CoEP_LF":
                    build += float(c["$Build"]) / len(ORDER)
            per[arm] = api / n
        for arm, ls, col, lw in arms:
            ax.plot(x, (build if arm == "CoEP_LF" else 0) + per[arm] * x, ls=ls,
                    color=col, lw=lw, label=label[arm])
        for arm in ("PyDex", "LLM_Direct"):
            ns = build / (per[arm] - per["CoEP_LF"])
            ax.plot(ns, per[arm] * ns, "o", ms=3.5, mfc="white", mec="black",
                    mew=0.8, zorder=5)
            ax.annotate(f"$N^*={ns:.0f}$", (ns, per[arm] * ns), fontsize=6.5,
                        xytext=(3, -9), textcoords="offset points", ha="left")
        ax.plot(sizes, [0.0008] * len(sizes), "|", color="black", ms=5, mew=0.7)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlim(1, 1000); ax.set_ylim(0.0005, 100)
        ax.set_xlabel("buggy submissions per assignment")
        ax.grid(alpha=0.3, lw=0.4)
    axes[0].set_ylabel("model cost (\\$, log)")
    axes[0].text(1.3, 0.0011, "assignment sizes", fontsize=6, color="#404040")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.9),
               handlelength=2.4)
    fig.tight_layout(w_pad=1.0, rect=(0, 0, 1, 0.9))
    _sub(fig, axes, [f"({'ab'[i]}) {name}" for i, (_m, name) in enumerate(MODELS)])
    _save(fig, "fig_cost")
    plt.close(fig)


def fig_source():
    """(a) CoEP_LF's repairs by source; (b) depth of the rule compositions."""
    plt = _mpl()
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 1.75),
                               gridspec_kw={"width_ratios": [2.1, 1]})
    keys = [("rules", "rules", BLUE, ""),
            ("reference", "transplant", SKY, ""),
            ("llm", "fallback LLM", PURPLE, "////"),
            ("none", "unrepaired", RED, "")]
    share = {k: [] for k, *_ in keys}
    depth: dict[int, int] = {}
    for pid in ORDER:
        lf = _log(pid, "coep_lf")
        src = lf.Source.where(lf.ok, "none")
        for k, *_ in keys:
            share[k].append(100 * (src == k).mean())
        l = _log(pid, "coep_l")
        for r in l[l.ok & (l.Source == "rules")].Rules_L:
            d = len(json.loads(r))
            depth[d] = depth.get(d, 0) + 1
    x = np.arange(len(ORDER))
    bottom = np.zeros(len(ORDER))
    for k, lab, face, hatch in keys:
        a.bar(x, share[k], 0.7, bottom=bottom, color=face, hatch=hatch,
              edgecolor="black", linewidth=0.5, label=lab)
        bottom += share[k]
    a.axvline(4.5, color="black", lw=0.6, ls=":")
    a.set_xticks(x, [IDS[p] for p in ORDER])
    a.set_ylim(0, 100)
    a.set_ylabel("share of pairs (%)")
    a.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0),
             handlelength=1.2, columnspacing=1.0, handletextpad=0.4)
    ds = sorted(depth)
    bars = b.bar(ds, [depth[d] for d in ds], 0.6, color=BLUE,
                 edgecolor="black", linewidth=0.5)
    b.bar_label(bars, fontsize=6, padding=1)
    b.set_xticks(ds)
    b.set_xlabel("rule applications")
    b.set_ylabel("rule repairs")
    b.set_ylim(0, max(depth.values()) * 1.18)
    fig.tight_layout(w_pad=1.5)
    _sub(fig, (a, b), ("(a) Source of each repair", "(b) Composition depth"))
    _save(fig, "fig_source")
    plt.close(fig)


def fig_general():
    """(a) repair rate against the share of the class built from; (b) growth."""
    plt = _mpl()
    r = pd.read_csv(RES / "splits" / "report.csv")
    r["cs1"] = r.pid.str.startswith("refactory")
    fs = [10, 25, 50, 75]
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 1.75))
    pos = np.arange(len(fs) + 1)
    for cs1, name, mk, dx in ((True, "CS1", "o", -0.1), (False, "Codeforces", "s", 0.1)):
        d = r[r.cs1 == cs1]
        for arm, ls in (("LF", "-"), ("L", "--")):
            rr = [100 * d[d.f == f][f"{arm}_fixed"].sum() / d[d.f == f][f"{arm}_n"].sum()
                  for f in fs]
            same = d[d.f == fs[0]]
            full = 100 * same[f"same_{arm}_fixed"].sum() / same[f"same_{arm}_n"].sum()
            z = 3 if arm == "LF" else 2
            col = ARM["CoEP_" + arm][1]
            a.plot(pos[:-1], rr, ls=ls, marker=mk, color=col, ms=3.5, zorder=z,
                   mfc="white" if arm == "L" else col, mew=0.9, lw=1.1,
                   label=f"{name}, {ARM['CoEP_' + arm][0]}")
            a.plot(pos[-1] + dx, full, marker=mk, color=col, ms=3.5, mew=0.9, zorder=z,
                   mfc="white" if arm == "L" else col, ls="none")
    a.axvline(len(fs) - 0.5, color="#7f7f7f", lw=0.5, ls=":")
    a.set_xticks(pos, [f"{f}%" for f in fs] + ["all"])
    a.set_xlabel("share of the class the tool is built from")
    a.set_ylabel("repair rate (%)")
    a.set_ylim(88, 100.6)
    a.legend(loc="lower right", ncol=2, fontsize=6, handlelength=2.2,
             columnspacing=0.8)

    d = r[r.cs1]
    base = {}
    for col, lab, ls, mk, c in (("pairs", r"worked pairs $|S|$", "-", "o", BLUE),
                                ("in_tok", "builder input tokens", "--", "^", SKY),
                                ("out_tok", "builder output tokens", ":", "s", RED),
                                ("build_usd", r"$C_{\mathrm{build}}$", "-", "D", ORANGE)):
            v = [d[(d.f == f) & (d.model == FRONTIER)][col].mean() for f in fs]
            base[col] = v
            b.plot(fs, [y / v[0] for y in v], ls=ls, marker=mk, ms=3.5, color=c,
                   mfc="white", mew=0.9, lw=1.2, label=lab)
    b.set_xticks(fs, [f"{f}%" for f in fs])
    b.set_xlabel("share of the class (CS1, claude-sonnet-5)")
    b.set_ylabel("growth over 10%")
    b.set_yticks([1, 3, 5, 7, 9], [f"{t}×" for t in (1, 3, 5, 7, 9)])
    b.legend(loc="upper left", fontsize=6.5, handlelength=2.2)
    fig.tight_layout(w_pad=1.5)
    _sub(fig, (a, b), ("(a) Repair rate on the last quarter",
                       "(b) Growth of the build"))
    _save(fig, "fig_general")
    plt.close(fig)
    return base


def fig_heldout():
    """Repair rate on T and on the held-out suite, per builder."""
    plt = _mpl()
    h = pd.read_csv(RES / "heldout.csv")
    arms = [("Refactory", "Refactory"), ("PyDex", "PyDex"),
            ("LLM_Direct", ARM["LLM_Direct"][0]),
            ("CoEP_LF (T)", ARM["CoEP_LF"][0] + " accepting $T$"),
            ("CoEP_L", ARM["CoEP_L"][0]), ("CoEP_LF", ARM["CoEP_LF"][0])]
    color = [ARM.get(a, (0, "#6C8EBF"))[1] for a, _ in arms]   # muted blue: T only
    fig, axes = plt.subplots(1, 2, figsize=(W, 1.9), sharey=True)
    y = np.arange(len(arms))[::-1]
    for ax, (m, name) in zip(axes, MODELS):
        t, ho = [], []
        for arm, _ in arms:
            d = h[(h.arm == arm) & (h.model == ("none" if arm == "Refactory" else m))]
            t.append(100 * d.fixed.sum() / d.n.sum())
            ho.append(100 * d.fixed_heldout.sum() / d.n.sum())
        ax.barh(y + 0.19, t, 0.38, color="white", edgecolor=color, lw=0.6,
                hatch="////")
        bars = ax.barh(y - 0.19, ho, 0.38, color=color, edgecolor="black", lw=0.5)
        ax.bar_label(bars, fmt="%.1f", fontsize=6, padding=1.5)
        ax.set_xlim(80, 100)
        ax.set_xlabel("repair rate (%)")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_yticks(y, [lab for _, lab in arms])
    from matplotlib.patches import Patch
    fig.legend([Patch(facecolor="white", edgecolor="#555555", hatch="////"),
                Patch(facecolor="#888888", edgecolor="black", lw=0.5)],
               ["instructor's tests $T$", "held-out suite"], ncol=2,
               loc="lower center", bbox_to_anchor=(0.55, 0.93))
    fig.tight_layout(w_pad=1.5, rect=(0, 0, 1, 0.93))
    _sub(fig, axes, [f"({'ab'[i]}) {name}" for i, (_m, name) in enumerate(MODELS)])
    _save(fig, "fig_heldout")
    plt.close(fig)


def main(argv: list[str]) -> int:
    argparse.ArgumentParser(prog="run.py figures").parse_args(argv)
    fig_effect()
    fig_cost()
    fig_source()
    fig_general()
    fig_heldout()
    return 0
