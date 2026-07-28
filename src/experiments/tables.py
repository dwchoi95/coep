"""`run.py tables` — regenerate every LaTeX table body and macro from results/.

The paper's tables are ``\\input`` bodies rather than hand-written rows, so a
completed run is one command away from a compiled PDF and no number is ever
transcribed by hand. Everything here reads results/<ver>/, which the collectors
own; nothing is recomputed from the tools.

Writes paper/tab_effect.tex, tab_source.tex, tab_robust.tex and numbers.tex.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"

ORDER = ["refactory_q1", "refactory_q2", "refactory_q3", "refactory_q4",
         "refactory_q5", "cf_110A", "cf_131A", "cf_1011B", "cf_125A",
         "cf_11B", "cf_10C"]
TITLE = {"refactory_q1": "Sequential search",
         "refactory_q2": "Unique dates/months",
         "refactory_q3": "Duplicate elimination",
         "refactory_q4": "Sorting tuples",
         "refactory_q5": "Top-$k$ elements"}
# Short ids the rest of the paper refers to, so a figure axis or an inline
# mention costs four characters instead of a title. R for the CS1 corpus, C for
# Codeforces in rating order, which is the order Table 2 lists them in.
IDS = {p: (f"R{i+1}" if i < 5 else f"C{i-4}") for i, p in enumerate(ORDER)}
BANDS = [("CS1 (Refactory)", ORDER[:5]),
         ("CF 800--1000", ["cf_110A", "cf_131A"]),
         ("CF 1200--2000", ["cf_1011B", "cf_125A", "cf_11B", "cf_10C"])]
FRONTIER = "claude-sonnet-5"
CHEAP = "gpt-5.4-mini"


def _meta(pid: str) -> tuple[str, str]:
    d = json.loads((ROOT / "data" / pid / "problem.json").read_text())
    title = TITLE.get(pid) or d["description"].strip().splitlines()[0].lstrip("# ").strip()
    return title, (str(d["rating"]) if d.get("rating") else "--")


def _summary(ver: str, pid: str) -> pd.DataFrame:
    f = ROOT / "results" / ver / pid / "summary.csv"
    return pd.read_csv(f, keep_default_na=False) if f.exists() else pd.DataFrame()


def _cell(df: pd.DataFrame, approach: str, model: str) -> dict | None:
    m = df[(df["Approach"] == approach) & (df["Model"] == model)]
    return m.iloc[0].to_dict() if len(m) else None


def tab_effect(ver: str) -> str:
    arms = [("Refactory", "none"), ("PyDex", FRONTIER),
            ("CoEP_L", FRONTIER), ("CoEP_LF", FRONTIER)]
    head = " & ".join(["Refactory", "PyDex", r"\textsc{CoEP}\textsubscript{L}",
                       r"\textsc{CoEP}\textsubscript{LF}"])
    out = [r"\begin{tabular}{crlc rrrr c rrrr}", r"\toprule",
           r"& & & & \multicolumn{4}{c}{\textbf{RR} (\%)} & & "
           r"\multicolumn{4}{c}{\textbf{RPS}} \\",
           r"\cmidrule(lr){5-8}\cmidrule(lr){10-13}",
           r"& ID & Assignment & Rating & " + head + " & & " + head + r" \\",
           r"\midrule"]
    acc = {a: [0.0, 0.0, 0, 0] for a, _m in arms}      # rr*n, rps*rep, n, rep
    for gname, pids in (("Refactory", ORDER[:5]), ("Codeforces", ORDER[5:])):
        if gname == "Codeforces":
            out.append(r"\midrule")
        for i, pid in enumerate(pids):
            df = _summary(ver, pid)
            title, rating = _meta(pid)
            spine = (r"\multirow{%d}{*}{\rotatebox[origin=c]{90}{\emph{%s}}}"
                     % (len(pids), gname)) if i == 0 else ""
            rr, rps = [], []
            for a, m in arms:
                c = _cell(df, a, m)
                if c is None:
                    rr.append("--"); rps.append("--"); continue
                n, r_, p_ = int(c["N"]), float(c["RR"]), float(c["RPS"])
                rep = round(r_ * n)
                rr.append(f"{100*r_:.1f}"); rps.append(f"{p_:.3f}")
                acc[a][0] += r_ * n; acc[a][1] += p_ * rep
                acc[a][2] += n; acc[a][3] += rep
            out.append(f"{spine} & {IDS[pid]} & {title} & {rating} & "
                       + " & ".join(rr) + " & & " + " & ".join(rps) + r" \\")
    out.append(r"\midrule")
    rr = " & ".join(f"\\textbf{{{100*acc[a][0]/acc[a][2]:.1f}}}" for a, _m in arms)
    rps = " & ".join(f"\\textbf{{{acc[a][1]/acc[a][3]:.3f}}}" for a, _m in arms)
    out.append(r"& \multicolumn{3}{l}{\textbf{Corpus} (%s submissions)} & %s & & %s \\"
               % (f"{acc['CoEP_L'][2]:,}".replace(",", "{,}"), rr, rps))
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def _source_split(ver: str, model: str) -> dict:
    """Repaired submissions by the mechanism that produced them."""
    agg: dict[str, list] = {}
    for pid in ORDER:
        f = ROOT / "results" / ver / pid / "coep_l.csv"
        if not f.exists():
            continue
        authored = set(json.loads(_cell(_summary(ver, pid), "CoEP_L",
                                        model)["Rules_build"]))
        df = pd.read_csv(f, keep_default_na=False)
        df = df[df["Model"] == model]
        for _i, r in df.iterrows():
            if not r["Fixed"]:
                continue
            src = r["Source"]
            if src == "rules":
                names = json.loads(r["Rules_L"])
                src = "authored" if any(n in authored for n in names) else "generic"
            a = agg.setdefault(src, [0, 0.0])
            a[0] += 1
            a[1] += float(r["RPS"]) if r["RPS"] != "" else 0.0
    # the fallback's share is CoEP_LF's llm-sourced repairs
    fb = [0, 0.0]
    for pid in ORDER:
        f = ROOT / "results" / ver / pid / "coep_lf.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, keep_default_na=False)
        df = df[(df["Model"] == model) & (df["Source"] == "llm") & (df["Fixed"])]
        fb[0] += len(df)
        fb[1] += df["RPS"].astype(float).sum()
    agg["llm"] = fb
    return agg


def tab_source(ver: str) -> str:
    agg = _source_split(ver, FRONTIER)
    tot = sum(v[0] for k, v in agg.items() if k != "llm")
    rows = [("authored", "LLM-authored rules", r"$\bullet$"),
            ("generic", "Generic-library rules", r"$\bullet$"),
            ("reference", "Reference transplant", "--"),
            ("noop", "Already passing (no edit)", "--"),
            ("llm", "LLM fallback (\\textsc{CoEP}\\textsubscript{LF})", "--")]
    out = [r"\begin{tabular}{lrrc}", r"\toprule",
           r"Repair source & share (\%) & mean RPS & labelled \\", r"\midrule"]
    for k, name, lab in rows:
        v = agg.get(k, [0, 0.0])
        if k == "llm":
            out.append(r"\midrule")
        out.append(f"{name} & {100*v[0]/max(tot,1):.1f} & "
                   f"{v[1]/max(v[0],1):.3f} & {lab} \\\\")
    # framework-only ablation, if the pass has been run
    fw = [(_cell(_summary(ver, p), "CoEP_L_fw", FRONTIER), p) for p in ORDER]
    fw = [(c, p) for c, p in fw if c is not None]
    out.append(r"\midrule")
    if fw:
        n = sum(int(c["N"]) for c, _p in fw)
        rep = sum(round(float(c["RR"]) * int(c["N"])) for c, _p in fw)
        rps = sum(float(c["RPS"]) * round(float(c["RR"]) * int(c["N"]))
                  for c, _p in fw) / max(rep, 1)
        base = [(_cell(_summary(ver, p), "CoEP_L", FRONTIER)) for p in ORDER]
        bn = sum(int(c["N"]) for c in base)
        brep = sum(round(float(c["RR"]) * int(c["N"])) for c in base)
        brps = sum(float(c["RPS"]) * round(float(c["RR"]) * int(c["N"]))
                   for c in base) / max(brep, 1)
        out += [r"\multicolumn{4}{l}{\emph{Framework-only ablation"
                r" (authored rules removed)}}\\",
                f"\\quad ablated & {100*rep/n:.2f} & {rps:.3f} & -- \\\\",
                f"\\quad full tool & {100*brep/bn:.2f} & {brps:.3f} & -- \\\\"]
    else:
        out += [r"\multicolumn{4}{l}{\emph{Framework-only ablation}}\\",
                r"\quad & \multicolumn{3}{l}{\emph{[pass not yet run]}} \\"]
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def _band(ver: str, pids: list[str], approach: str, model: str):
    n = rep = 0
    rr = rps = 0.0
    for pid in pids:
        c = _cell(_summary(ver, pid), approach, model)
        if c is None:
            continue
        nn = int(c["N"]); r_ = float(c["RR"]); k = round(r_ * nn)
        n += nn; rep += k; rr += r_ * nn; rps += float(c["RPS"]) * k
    if not n:
        return None
    return rr / n, rps / max(rep, 1)


def tab_robust(ver: str) -> str:
    def cell(t):
        return f"{100*t[0]:.1f} / {t[1]:.3f}" if t else "--"

    out = [r"\begin{tabular}{lccc}", r"\toprule",
           r"& Refactory & PyDex & \textsc{CoEP}\textsubscript{LF} \\",
           r"Stratum & \multicolumn{3}{c}{RR (\%) / RPS} \\", r"\midrule",
           r"\multicolumn{4}{l}{\emph{Difficulty} (Sonnet builder)}\\"]
    for name, pids in BANDS:
        out.append(f"\\quad {name} & {cell(_band(ver, pids, 'Refactory', 'none'))}"
                   f" & {cell(_band(ver, pids, 'PyDex', FRONTIER))}"
                   f" & {cell(_band(ver, pids, 'CoEP_LF', FRONTIER))} \\\\")
    out += [r"\midrule", r"\multicolumn{4}{l}{\emph{Builder}}\\"]
    for model, name in ((FRONTIER, "Claude Sonnet 5"), (CHEAP, "GPT-5.4-mini")):
        out.append(f"\\quad {name} & -- & {cell(_band(ver, ORDER, 'PyDex', model))}"
                   f" & {cell(_band(ver, ORDER, 'CoEP_LF', model))} \\\\")
    sweep = ROOT / "results" / ver / "threshold_sweep.json"
    out.append(r"\midrule")
    if sweep.exists():
        pts = json.loads(sweep.read_text())
        rr = {round(100 * q["rr"], 2) for q in pts}
        lo, hi = min(q["rps"] for q in pts), max(q["rps"] for q in pts)
        ulo, uhi = min(q["usd"] for q in pts), max(q["usd"] for q in pts)
        out += [r"\multicolumn{4}{l}{\emph{Threshold}, %d measured settings}\\" % len(pts),
                r"\quad range & -- & -- & %s / %.3f--%.3f \\"
                % (f"{next(iter(rr)):.1f}" if len(rr) == 1 else "varies", lo, hi),
                r"\quad spend & \multicolumn{3}{c}{\$%.2f--\$%.2f total} \\"
                % (ulo, uhi)]
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py tables")
    ap.add_argument("--ver", default="v2")
    args = ap.parse_args(argv)
    for name, body in (("tab_effect", tab_effect(args.ver)),
                       ("tab_source", tab_source(args.ver)),
                       ("tab_robust", tab_robust(args.ver))):
        (PAPER / f"{name}.tex").write_text(body)
        print(f"  wrote paper/{name}.tex")
    return 0
