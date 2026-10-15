"""`run.py ablation` — what each artifact the builder writes buys, at the level
of the deployed system (CoEP_LF), from the logs alone.

The builder writes two artifacts: the rewrite rules (Synthesize) and the input
generator behind the amplified suite T+ (Amplify). Removing either from CoEP_LF
needs no new model call, because the fallback query does not depend on the tool:
LLM_Direct already sent exactly that query, with the same prompt, model and
acceptance, for every buggy program. So an arm "local tool X + fallback" is
recomposed as CoEP_LF composes it (compare.py): keep X's patch when it exists
and RPS <= RPS_GATE; otherwise escalate, pay for the Direct query, and keep the
smaller of the two patches.

    arm               local tool            acceptance   fallback
    full              CoEP_L                T+           Direct (T+)
    (and, as run: CoEP_LF itself, and CoEP_LF accepting T on R1-R5)
    -rules            CoEP_L_fw             T+           Direct (T+)
    -amp              CoEP_L (T-only)       T            Direct (T)
    -rules-amp        CoEP_L_fw (T-only)    T            Direct (T)

"full" recomposed this way is checked against the CoEP_LF actually run, which is
what licenses the other three. On C1-C6, T+ = T, so -amp coincides with full.

Every patch is judged on the held-out suite (R1-R5) once, cached by its text.
RR_tau is the share of buggy programs repaired by a patch that passes the
held-out suite (C1-C6: the judge's full official tests) with RPS <= tau.

    results/ablation.csv   one row per (arm, pid, model, buggy)
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src.experiments._common import IDS, ORDER
from src.experiments.augment import _suite
from src.runner.testing import run_tests

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
MODELS = ["claude-sonnet-5", "gpt-5.4-mini"]
CS1 = ORDER[:5]
RPS_GATE = 1.0                      # compare.py
TAUS = (0.1, 0.25, 0.5)


def _log(pid: str, stem: str) -> dict:
    d = pd.read_csv(RES / pid / f"{stem}.csv", keep_default_na=False)
    out = {}
    for _, r in d.iterrows():
        ok = str(r.Fixed) == "True"
        out[(str(r.Model), str(r.Buggy))] = {
            "fixed": ok, "patch": str(r.Patch) if ok else "",
            "rps": float(r.RPS) if ok else None, "source": str(r.Source),
            "usd": float(r["$API"] or 0), "rules": str(r.Rules_L)}
    return out


def _compose(local: dict, direct: dict) -> dict:
    """CoEP_LF's rule (compare.py): escalate on a miss or an oversized patch."""
    out = {}
    for k, lo in local.items():
        if lo["fixed"] and lo["rps"] <= RPS_GATE:
            out[k] = dict(lo, usd=0.0)
            continue
        fb = direct[k]
        pick = lo if lo["fixed"] else None
        if fb["fixed"] and (pick is None or fb["rps"] < pick["rps"]):
            pick = dict(fb, source="llm")
        out[k] = dict(pick or {"fixed": False, "patch": "", "rps": None,
                               "source": "none", "rules": "[]"}, usd=fb["usd"])
    return out


def _arms(pid: str) -> dict:
    cs1 = pid in CS1
    na = "no_amplification/" if cs1 else ""
    direct, direct_t = _log(pid, "direct_llm"), _log(pid, f"{na}direct_llm")
    l, l_t = _log(pid, "coep_l"), _log(pid, f"{na}coep_l")
    fw, fw_t = _log(pid, "coep_l_fw"), _log(pid, f"{na}coep_l_fw")
    return {"CoEP_LF (run)": _log(pid, "coep_lf"),
            # the T-only arm as actually run (R1-R5; on C1-C6, T+ = T)
            "-amp (run)": _log(pid, f"{na}coep_lf"),
            "full": _compose(l, direct),
            "-rules": _compose(fw, direct),
            "-amp": _compose(l_t, direct_t),
            "-rules-amp": _compose(fw_t, direct_t),
            "PyDex": {k: dict(v, usd=v["usd"]) for k, v in _log(pid, "pydex").items()},
            "LLM_Direct": direct}


def _build_usd(pid: str, model: str, arm: str) -> float:
    """Rules: the tool's build; amplification: the generator's (R1-R5)."""
    rules = json.loads((ROOT / "tools" / pid / model / "cost.json").read_text())["usd"]
    amp_f = ROOT / "benchmark" / pid / "amplified" / model / "cost.json"
    amp = json.loads(amp_f.read_text())["usd"] if amp_f.exists() else 0.0
    if arm in ("CoEP_LF (run)", "full"):
        return rules + amp
    if arm == "-rules":
        return amp
    if arm in ("-amp", "-amp (run)"):
        if pid not in CS1:
            return rules
        s = pd.read_csv(RES / pid / "no_amplification" / "summary.csv", keep_default_na=False)
        s = s[(s.Approach == "CoEP_LF") & (s.Model == model)]
        return float(s.iloc[0]["$Build"])
    return 0.0                                   # -rules-amp, PyDex, LLM_Direct


def run() -> pd.DataFrame:
    rows = []
    for pid in ORDER:
        arms = _arms(pid)
        if pid in CS1:                           # judge every distinct patch once
            suite = _suite(pid)
            patches = {v["patch"] for a in arms.values() for v in a.values() if v["fixed"]}
            with ThreadPoolExecutor(16) as ex:
                verdict = dict(zip(patches, ex.map(
                    lambda p: run_tests(p, suite).all_pass, patches)))
        for arm, got in arms.items():
            for (model, buggy), v in got.items():
                held = (verdict[v["patch"]] if pid in CS1 else True) if v["fixed"] else False
                rows.append({"arm": arm, "pid": pid, "model": model, "buggy": buggy,
                             "fixed": v["fixed"], "heldout": held, "rps": v["rps"],
                             "source": v["source"], "rules": v["rules"],
                             "api_usd": v["usd"]})
        print(f"{IDS[pid]}: {len(arms)} arms judged")
    df = pd.DataFrame(rows)
    df.to_csv(RES / "ablation.csv", index=False)
    return df


def report(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (arm, model), g in df.groupby(["arm", "model"], sort=False):
        ok = g[g.fixed]
        row = {"arm": arm, "model": model, "n": len(g),
               "RR": 100 * g.fixed.mean(),
               "RR_held": 100 * g.heldout.mean(),
               "RPS": ok.rps.astype(float).mean(),
               "api_usd": g.api_usd.sum(),
               "build_usd": sum(_build_usd(p, model, arm) for p in ORDER)
               if arm not in ("PyDex", "LLM_Direct") else 0.0,
               "queries": int((g.api_usd > 0).sum())}
        for t in TAUS:
            row[f"RR_{t}"] = 100 * (g.heldout & (g.rps.astype(float) <= t)).mean()
        row["usd"] = row["api_usd"] + row["build_usd"]
        out.append(row)
    rep = pd.DataFrame(out)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(rep.round(3).to_string(index=False))
    # the recomposition must reproduce the run it stands in for
    run_, sim = (df[df.arm == a].set_index(["pid", "model", "buggy"])
                 for a in ("CoEP_LF (run)", "full"))
    agree = (run_.fixed == sim.fixed.reindex(run_.index)).mean()
    print(f"full (recomposed) vs CoEP_LF (run): same repaired/unrepaired on "
          f"{100 * agree:.2f}% of pairs")
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run.py ablation")
    ap.add_argument("--report-only", action="store_true",
                    help="summarize results/ablation.csv without re-judging")
    args = ap.parse_args(argv)
    df = (pd.read_csv(RES / "ablation.csv") if args.report_only else run())
    report(df)
    return 0
