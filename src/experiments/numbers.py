"""`run.py numbers` — recompute every number the paper quotes, from results/.

The paper used to hold a spliced \\newcommand block; it now carries the values
literally, so this command no longer writes to main.tex. It prints each
quantity next to whether that exact string still occurs in main.tex, which is
how a number that drifted from the logs gets caught. Every value is read from
results/<ver>/, never recomputed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from src.experiments.splice import splice
from src.experiments.tables import (CHEAP, FRONTIER, ORDER, _cell, _source_split,
                                    _summary, ROOT, PAPER)

CS1 = ORDER[:5]
CF = ORDER[5:]


def agg(ver: str, approach: str, model: str | tuple, pids=tuple(ORDER)) -> dict:
    """Aggregate one arm. `model` may be a tuple, in which case the builders are
    pooled exactly as the paper's effectiveness tables pool them; cost is never
    pooled, since the two price schedules differ by an order of magnitude."""
    models = (model,) if isinstance(model, str) else tuple(model)
    n = rep = 0
    rr = rps = usd = 0.0
    for m in models:
        for pid in pids:
            c = _cell(_summary(ver, pid), approach, m)
            if c is None:
                continue
            nn = int(c["N"]); r_ = float(c["RR"]); k = round(r_ * nn)
            n += nn; rep += k; rr += r_ * nn
            rps += float(c["RPS"]) * k
            if m == models[0]:
                # cost is never pooled: the two price schedules differ by an
                # order of magnitude, so a mean of them is a number nobody pays
                usd += float(c["$API"]) + float(c["$Build"])
    return {"n": n, "rr": 100 * rr / max(n, 1), "rps": rps / max(rep, 1),
            "usd": usd}


def gate_stats(ver: str, model: str) -> tuple[int, float, int, float, float]:
    """(fired, rate over repaired, won, win fraction, spend)."""
    fired = won = rep = 0
    usd = 0.0
    for pid in ORDER:
        fl = ROOT / "results" / ver / pid / "coep_lf.csv"
        fk = ROOT / "results" / ver / pid / "coep_l.csv"
        if not (fl.exists() and fk.exists()):
            continue
        lf = pd.read_csv(fl, keep_default_na=False)
        lf = lf[lf["Model"] == model]
        loc = pd.read_csv(fk, keep_default_na=False)
        loc = loc[loc["Model"] == model].set_index("Buggy")
        usd += lf["$API"].astype(float).sum()
        for _i, r in lf.iterrows():
            b = loc.loc[r["Buggy"]] if r["Buggy"] in loc.index else None
            if b is None or not b["Fixed"]:
                continue                       # a miss, not a threshold firing
            rep += 1
            if float(r["$API"]) > 0:
                fired += 1
                if r["Source"] == "llm":
                    won += 1
    return fired, 100 * fired / max(rep, 1), won, 100 * won / max(fired, 1), usd


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py numbers")
    ap.add_argument("--ver", default="",
                    help="optional subdirectory under results/; empty means "
                         "results/ itself, which is where the campaign wrote")
    args = ap.parse_args(argv)
    v = args.ver

    BOTH = (FRONTIER, CHEAP)
    L = agg(v, "CoEP_L", BOTH)
    LF = agg(v, "CoEP_LF", BOTH)
    Lm = agg(v, "CoEP_L", CHEAP)
    LFm = agg(v, "CoEP_LF", CHEAP)
    P = agg(v, "PyDex", BOTH)
    Pm = agg(v, "PyDex", CHEAP)
    PC = agg(v, "PyDex_PC", FRONTIER)
    PCm = agg(v, "PyDex_PC", CHEAP)
    R = agg(v, "Refactory", "none")
    Lc, LFc, Rc, Pc = (agg(v, a, m, CS1) for a, m in
                       (("CoEP_L", BOTH), ("CoEP_LF", BOTH),
                        ("Refactory", "none"), ("PyDex", BOTH)))
    Lx, LFx, Rx = (agg(v, a, m, CF) for a, m in
                   (("CoEP_L", BOTH), ("CoEP_LF", BOTH),
                    ("Refactory", "none")))
    src = _source_split(v)
    tot = sum(x[0] for k, x in src.items() if k != "llm")
    rule_n, rule_sum = src.get("rules", [0, 0.0])
    rule_rps = rule_sum / max(rule_n, 1)
    ref = src.get("reference", [0, 0.0])
    fired, rate, won, winf, gusd = gate_stats(v, FRONTIER)

    att = {}
    for a, m in (("CoEP_L", FRONTIER), ("CoEP_LF", FRONTIER),
                 ("CoEP_L", CHEAP), ("CoEP_LF", CHEAP),
                 ("PyDex", FRONTIER), ("PyDex", CHEAP), ("Refactory", "none")):
        tt = nn = 0.0
        for pid in ORDER:
            c = _cell(_summary(v, pid), a, m)
            if c:
                tt += float(c["ATT_all"]) * int(c["N"]); nn += int(c["N"])
        att[(a, m)] = tt / max(nn, 1)

    def money(x): return f"{x:.2f}"

    M = {
        "NumEval": f"{L['n'] // 2:,}".replace(",", "{,}"),
        "NumEvalRefac": f"{Lc['n'] // 2:,}".replace(",", "{,}"),
        "NumEvalCF": f"{Lx['n'] // 2:,}".replace(",", "{,}"),
        # CS1 corpus (the head-to-head against the published symbolic tool)
        "LocalRR": f"{Lc['rr']:.2f}", "LocalRPS": f"{Lc['rps']:.3f}",
        "HybridRR": f"{LFc['rr']:.2f}", "HybridRPS": f"{LFc['rps']:.3f}",
        "RefacRR": f"{Rc['rr']:.2f}", "RefacRPS": f"{Rc['rps']:.3f}",
        "PydexRPS": f"{Pc['rps']:.3f}",
        # whole benchmark
        "LocalRRAll": f"{L['rr']:.2f}", "LocalRPSAll": f"{L['rps']:.3f}",
        "HybridRRAll": f"{LF['rr']:.2f}", "HybridRPSAll": f"{LF['rps']:.3f}",
        "PydexRRAll": f"{P['rr']:.2f}", "PydexRPSAll": f"{P['rps']:.3f}",
        "RefacRRAll": f"{R['rr']:.2f}", "RefacRPSAll": f"{R['rps']:.3f}",
        "LocalRRAllMini": f"{Lm['rr']:.2f}", "LocalRPSAllMini": f"{Lm['rps']:.3f}",
        "HybridRRAllMini": f"{LFm['rr']:.2f}", "HybridRPSAllMini": f"{LFm['rps']:.3f}",
        "PydexRRMini": f"{Pm['rr']:.2f}", "PydexRPSMini": f"{Pm['rps']:.3f}",
        # Codeforces half
        "LocalRRCF": f"{Lx['rr']:.2f}", "LocalRPSCF": f"{Lx['rps']:.3f}",
        "HybridRRCF": f"{LFx['rr']:.2f}", "HybridRPSCF": f"{LFx['rps']:.3f}",
        "RefacRRCF": f"{Rx['rr']:.2f}", "RefacRPSCF": f"{Rx['rps']:.3f}",
        # cost
        "HybridUsd": money(LF["usd"]), "HybridUsdMini": money(LFm["usd"]),
        "BuildUsdSonnet": money(L["usd"]), "BuildUsdMini": money(Lm["usd"]),
        "PydexUsd": money(P["usd"]), "PydexUsdMini": money(Pm["usd"]),
        "PydexPCUsd": money(PC["usd"]), "PydexPCUsdMini": money(PCm["usd"]),
        "CostRatio": f"{P['usd']/max(LF['usd'],1e-9):.0f}",
        "CostRatioMini": f"{Pm['usd']/max(LFm['usd'],1e-9):.0f}",
        "CacheSavingFrac": f"{100*(1-PC['usd']/max(P['usd'],1e-9)):.1f}",
        # turnaround
        "LocalATT": f"{att[('CoEP_L', FRONTIER)]:.2f}",
        "HybridATT": f"{att[('CoEP_LF', FRONTIER)]:.2f}",
        "LocalATTMini": f"{att[('CoEP_L', CHEAP)]:.2f}",
        "HybridATTMini": f"{att[('CoEP_LF', CHEAP)]:.2f}",
        "PydexATT": f"{att[('PyDex', FRONTIER)]:.2f}",
        "PydexATTMini": f"{att[('PyDex', CHEAP)]:.2f}",
        "RefacATT": f"{att[('Refactory', 'none')]:.2f}",
        # repair sources
        "RuleShare": f"{100*rule_n/max(tot,1):.1f}", "RuleRPS": f"{rule_rps:.3f}",
        "RefShare": f"{100*ref[0]/max(tot,1):.1f}",
        "RefRPS": f"{ref[1]/max(ref[0],1):.3f}",
        # the escalation gate
        "GateFired": str(fired), "GateRate": f"{rate:.1f}",
        "GateWon": str(won), "GateWinFrac": f"{winf:.1f}",
        "GateUsd": money(gusd),
    }

    tex = (PAPER / "main" / "main.tex").read_text()
    absent = []
    for k, val in M.items():
        if val in tex:
            print(f"  {k:<20}{val:>12}   in main.tex")
        else:
            absent.append((k, val))
            print(f"  {k:<20}{val:>12}   ABSENT")
    print(f"{len(M) - len(absent)}/{len(M)} quantities occur verbatim in main.tex")
    if absent:
        print("  absent values are either superseded or quoted with different "
              "formatting; check each before assuming the paper is stale")
    return 0
