#!/usr/bin/env python3
"""Aggregate experiment results, compute cost models, and emit paper figures.

Outputs:
  runs/summary.json           aggregated metrics
  paper/figures/*.pdf         figures used in the paper
"""
import json
import pathlib
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep import tokens  # noqa: E402
from coep.costmodel import (CACHE_READ_MULT, CACHE_WRITE_MULT,  # noqa: E402
                            PRICE_IN_PER_MTOK, PRICE_OUT_PER_MTOK, Usage)

PROBLEMS = ROOT / "benchmark" / "problems"
FIGDIR = ROOT / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

C_BASE = "#4477AA"
C_COEP = "#EE6677"
C_HYB = "#228833"
C_GREY = "#BBBBBB"


def prompt_prefix_tokens(pid: str) -> int:
    """Tokens of the per-problem shared prompt prefix (desc+tests), i.e. the
    cacheable portion of the baseline prompt."""
    text = (ROOT / "runs" / "baseline" / "prompts").glob(f"{pid}__*.md")
    first = sorted(text)[0].read_text()
    prefix = first.split("## Buggy student submission")[0]
    return tokens.count(prefix)


def main():
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    pids = sorted(splits)

    # ---------------- baseline ----------------
    base = json.loads((ROOT / "runs" / "baseline" / "results.json").read_text())
    base_by_key = {r["key"]: r for r in base}
    base_by_pid = defaultdict(list)
    for r in base:
        base_by_pid[r["pid"]].append(r)

    n_eval = len(base)
    b_fixed = [r for r in base if r.get("passed")]
    b_quality = [r for r in b_fixed if r.get("rps", 1) <= 0.35]
    base_usage = Usage(
        input_tokens=sum(r["prompt_tokens"] for r in base),
        output_tokens=sum(r.get("response_tokens", 0) for r in base))

    # cached-baseline model: per problem the prefix (description+tests) is
    # cache-written once and cache-read for the remaining instances
    cached = Usage()
    for pid in pids:
        rows = base_by_pid[pid]
        pref = prompt_prefix_tokens(pid)
        n = len(rows)
        cached.cache_write_tokens += pref
        cached.cache_read_tokens += pref * (n - 1)
        cached.input_tokens += sum(r["prompt_tokens"] - pref for r in rows)
        cached.output_tokens += sum(r.get("response_tokens", 0) for r in rows)

    # ---------------- coep ----------------
    coep_res = {}
    build_usage = Usage()
    rounds_by_pid = {}
    for pid in pids:
        coep_res[pid] = json.loads((ROOT / "runs" / "coep" / "results" / f"{pid}.json").read_text())
        prompts = sorted((ROOT / "runs" / "coep" / "prompts").glob(f"{pid}_round*.md"))
        resps = sorted((ROOT / "runs" / "coep" / "responses").glob(f"{pid}_round*.md"))
        rounds_by_pid[pid] = len(resps)
        for f in prompts[:len(resps)]:
            build_usage.input_tokens += tokens.count(f.read_text())
        for f in resps:
            build_usage.output_tokens += tokens.count(f.read_text())

    coep_all = [dict(r, pid=pid) for pid in pids for r in coep_res[pid]]
    c_fixed = [r for r in coep_all if r["repaired"]]

    # hybrid: local first; unrepaired instances fall back to the per-instance
    # LLM baseline (reusing the baseline run for those same instances)
    hybrid_fixed, fallback_usage = list(c_fixed), Usage()
    fb_count = 0
    for r in coep_all:
        if r["repaired"]:
            continue
        key = f"{r['pid']}__{r['bug'][:-3]}"
        b = base_by_key[key]
        fb_count += 1
        fallback_usage.input_tokens += b["prompt_tokens"]
        fallback_usage.output_tokens += b.get("response_tokens", 0)
        if b.get("passed"):
            hybrid_fixed.append(r)

    # ---------------- summary ----------------
    per_problem = {}
    for pid in pids:
        rows = coep_res[pid]
        brows = base_by_pid[pid]
        per_problem[pid] = {
            "n_eval": len(rows),
            "baseline_fixed": sum(1 for r in brows if r.get("passed")),
            "baseline_quality_fixed": sum(1 for r in brows if r.get("passed") and r.get("rps", 1) <= 0.35),
            "coep_local_fixed": sum(r["repaired"] for r in rows),
            "builder_rounds": rounds_by_pid[pid],
            "coep_mean_rps": round(float(np.mean([r["rps"] for r in rows if r["repaired"]] or [0])), 4),
            "baseline_mean_rps": round(float(np.mean([r["rps"] for r in brows if r.get("passed")] or [0])), 4),
            "coep_mean_seconds": round(float(np.mean([r.get("seconds") or 0 for r in rows])), 2),
        }

    per_inst_base_usd = base_usage.dollars() / n_eval
    per_inst_cached_usd = cached.dollars() / n_eval
    build_usd = build_usage.dollars()
    fb_rate = fb_count / len(coep_all)

    summary = {
        "tokenizer": tokens.MODE,
        "n_problems": len(pids),
        "n_eval_instances": n_eval,
        "baseline": {
            "repair_rate": len(b_fixed) / n_eval,
            "quality_repair_rate": len(b_quality) / n_eval,
            "mean_rps": round(float(np.mean([r["rps"] for r in b_fixed])), 4),
            "usage": base_usage.as_dict(),
            "usd_per_instance": round(per_inst_base_usd, 6),
            "cached_usage": cached.as_dict(),
            "cached_usd_per_instance": round(per_inst_cached_usd, 6),
        },
        "coep": {
            "local_repair_rate": len(c_fixed) / len(coep_all),
            "mean_rps": round(float(np.mean([r["rps"] for r in c_fixed])), 4),
            "build_usage": build_usage.as_dict(),
            "build_usd_total": round(build_usd, 4),
            "build_usd_per_problem": round(build_usd / len(pids), 4),
            "mean_repair_seconds": round(float(np.mean([r.get("seconds") or 0 for r in coep_all])), 2),
            "marginal_usd_per_instance": 0.0,
        },
        "hybrid": {
            "repair_rate": len(hybrid_fixed) / len(coep_all),
            "fallback_rate": fb_rate,
            "fallback_usage": fallback_usage.as_dict(),
            "usd_per_instance": round((build_usd + fallback_usage.dollars()) / len(coep_all), 6),
        },
        "per_problem": per_problem,
    }
    (ROOT / "runs" / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "per_problem"}, indent=2))

    # ---------------- figures ----------------
    plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

    # Fig 1: repair rates
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    labels = ["LLM baseline", "LLM baseline\n(RPS≤0.35)", "COEP-local", "COEP-hybrid"]
    vals = [summary["baseline"]["repair_rate"], summary["baseline"]["quality_repair_rate"],
            summary["coep"]["local_repair_rate"], summary["hybrid"]["repair_rate"]]
    bars = ax.bar(labels, vals, color=[C_BASE, C_BASE, C_COEP, C_HYB], width=0.6)
    bars[1].set_alpha(0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.1%}", ha="center", fontsize=8)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Repair rate")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGDIR / "repair_rates.pdf")

    # Fig 2: cumulative cost per problem vs #submissions
    n = np.arange(0, 501)
    per_inst_out = base_usage.output_tokens / n_eval
    base_cost = n * per_inst_base_usd
    cached_cost = n * per_inst_cached_usd
    coep_cost = build_usd / len(pids) + n * fb_rate * per_inst_base_usd
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    ax.plot(n, base_cost, color=C_BASE, label="LLM per-submission")
    ax.plot(n, cached_cost, color=C_BASE, ls="--", label="LLM + prompt caching")
    ax.plot(n, coep_cost, color=C_HYB, label="COEP-hybrid")
    ax.axhline(build_usd / len(pids), color=C_COEP, ls=":", lw=1,
               label="COEP build cost (one-off)")
    ax.set_xlabel("Submissions repaired per assignment")
    ax.set_ylabel("Cumulative LLM cost (USD)")
    ax.legend(frameon=False, fontsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGDIR / "cumulative_cost.pdf")

    # Fig 3: per-problem repair rates
    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    x = np.arange(len(pids))
    w = 0.38
    bvals = [per_problem[p]["baseline_fixed"] / per_problem[p]["n_eval"] for p in pids]
    cvals = [per_problem[p]["coep_local_fixed"] / per_problem[p]["n_eval"] for p in pids]
    ax.bar(x - w / 2, bvals, w, color=C_BASE, label="LLM baseline")
    ax.bar(x + w / 2, cvals, w, color=C_COEP, label="COEP-local")
    ax.set_xticks(x, pids, rotation=30, ha="right", fontsize=7.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Repair rate")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGDIR / "per_problem.pdf")

    # Fig 4: RPS distributions
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    data = [[r["rps"] for r in b_fixed], [r["rps"] for r in c_fixed]]
    bp = ax.boxplot(data, tick_labels=["LLM baseline", "COEP-local"], widths=0.5,
                    patch_artist=True, medianprops={"color": "black"})
    for patch, c in zip(bp["boxes"], [C_BASE, C_COEP]):
        patch.set_facecolor(c); patch.set_alpha(0.6)
    ax.set_ylabel("Relative patch size")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGDIR / "rps.pdf")

    print(f"figures written to {FIGDIR}")


if __name__ == "__main__":
    main()
