#!/usr/bin/env python3
"""Sensitivity of every arm's quality repair rate to the RPS cap tau,
recomputed from stored per-submission RPS values (no new runs).

Arms: frontier baseline, baseline+retry, PyDex-style, Haiku, cascade,
Refactory tool, CoEP-local, CoEP+frontier fallback.
Note: CoEP repairers *search under* tau=0.35, so their curves are lower
bounds for tau>0.35 (they never emit larger patches) and exact for
tau<=0.35 recomputation. Writes paper/figures/tau_sweep.pdf and prints a
table.
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TAUS = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50]


def main():
    base = {r["key"]: r for r in json.loads(
        (ROOT / "runs" / "baseline" / "results.json").read_text())}
    pyd = {r["key"]: r for r in json.loads(
        (ROOT / "runs" / "pydex" / "results.json").read_text())}
    hai = {r["key"]: r for r in json.loads(
        (ROOT / "runs" / "baseline_haiku" / "results.json").read_text())}
    retry = {r["key"]: r for r in json.loads(
        (ROOT / "runs" / "baseline_retry" / "results.json").read_text())}
    rt = json.loads((ROOT / "runs" / "refactory_tool" / "results.json").read_text())
    coep = {}
    for p in sorted((ROOT / "runs" / "coep" / "results").glob("*.json")):
        for r in json.loads(p.read_text()):
            coep[f"{p.stem}__{r['bug'][:-3]}"] = r
    keys = sorted(coep)
    n = len(keys)

    def ok(row, tau):
        return bool(row.get("passed")) and row.get("rps", 1) <= tau

    def rate(fn):
        return [100 * sum(fn(k, t) for k in keys) / n for t in TAUS]

    tool_rows = {}
    for pid, v in rt.items():
        for bug, s in v["per_submission"].items():
            tool_rows[f"{pid}__{bug[:-3]}"] = s

    curves = {
        "Frontier per-subm.": rate(lambda k, t: ok(base[k], t)),
        "+ validator, 1 retry": rate(lambda k, t: ok(base[k], t) or (
            k in retry and retry[k].get("passed") and retry[k].get("retry_rps", 1) <= t)),
        "PyDex-style": rate(lambda k, t: ok(pyd[k], t)),
        "Cheap (Haiku)": rate(lambda k, t: ok(hai[k], t)),
        "Refactory tool": rate(lambda k, t: bool(tool_rows[k].get("passes_our_tests"))
                               and (tool_rows[k].get("our_rps") or 9) <= t),
        "CoEP-local": rate(lambda k, t: coep[k]["repaired"] and coep[k].get("rps", 1) <= t),
        "CoEP+frontier fb.": rate(lambda k, t: (coep[k]["repaired"] and coep[k].get("rps", 1) <= t)
                                  or (not coep[k]["repaired"] and ok(base[k], t))),
    }
    print("tau      " + "  ".join(f"{t:.2f}" for t in TAUS))
    for name, ys in curves.items():
        print(f"{name:22s}" + "  ".join(f"{y:4.1f}" for y in ys))

    plt.rcParams.update({"font.size": 8, "figure.dpi": 150})
    fig, ax = plt.subplots(figsize=(4.2, 1.6))
    styles = {"Frontier per-subm.": ("#4477AA", "-"), "+ validator, 1 retry": ("#4477AA", "--"),
              "PyDex-style": ("#66CCEE", "-"), "Cheap (Haiku)": ("#CCBB44", "-"),
              "Refactory tool": ("#AA3377", "-"), "CoEP-local": ("#EE6677", "--"),
              "CoEP+frontier fb.": ("#228833", "-")}
    for name, ys in curves.items():
        c, ls = styles[name]
        ax.plot(TAUS, ys, ls, color=c, marker="o", ms=2.5, lw=1.2, label=name)
    ax.axvline(0.35, color="grey", lw=0.7, ls=":")
    ax.set_xlabel(r"patch-size cap $\tau$")
    ax.set_ylabel("Quality repair rate (%)")
    ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=5.4, ncol=2, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = ROOT / "paper" / "figures" / "tau_sweep.pdf"
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
