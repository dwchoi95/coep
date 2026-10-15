"""`run.py assemble` — the results the paper reports: results/v2/.

CoEP on R1-R5 accepts a repair against the amplified suite T+ (Section III-D),
so its arms -- and the matched per-submission arm LLM_Direct, which must accept
exactly as CoEP_LF does -- come from the CoEP+DT pass (results/dtg/). Every
other arm, and every Codeforces assignment (whose suites are the judge's full
official test sets and are not amplified), comes from the campaign (results/).
The builder's generator call is one-off build spend, so it is added to $Build.

    python run.py assemble            # -> results/v2/<pid>/, pool_ablation.json
    python run.py tables --ver v2     # and numbers / stats / figures likewise
"""
from __future__ import annotations

import json
import shutil

import pandas as pd

from src.experiments.tables import ORDER, ROOT

DT_ARMS = {"CoEP_L", "CoEP_LF", "CoEP_L_fw", "CoEP_L+SL", "LLM_Direct"}
DT_FILES = ["coep_l.csv", "coep_lf.csv", "coep_l_fw.csv", "coep_l_sl.csv", "direct_llm.csv"]


def main(argv=None) -> int:
    out = ROOT / "results" / "v2"
    shutil.rmtree(out, ignore_errors=True)
    for pid in ORDER:
        src, dst = ROOT / "results" / pid, out / pid
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.json"))
        if not pid.startswith("refactory"):
            continue
        dt = ROOT / "results" / "dtg" / pid
        for f in DT_FILES:
            (dst / f).unlink(missing_ok=True)
            if (dt / f).exists():
                shutil.copy(dt / f, dst / f)
        s = pd.read_csv(src / "summary.csv")
        d = pd.read_csv(dt / "summary.csv")
        for m in d.Model.unique():
            gen = json.loads((ROOT / "data_dtg" / m / pid / "gen_cost.json").read_text())
            coep = (d.Model == m) & d.Approach.str.startswith("CoEP")
            d.loc[coep, "$Build"] += gen["usd"]
            d.loc[coep, "ATT_build"] += gen["s"]
        pd.concat([s[~s.Approach.isin(DT_ARMS)], d], ignore_index=True).to_csv(
            dst / "summary.csv", index=False)
    shutil.copy(ROOT / "results" / "dtg" / "pool_ablation.json", out / "pool_ablation.json")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
