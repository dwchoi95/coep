"""`run.py tables` — regenerate the paper's generated table blocks.

Table rows are generated rather than typed, so a completed run is one command
away from a compiled PDF and no number is transcribed by hand. Everything here
reads results/<ver>/, which the collectors own; nothing is recomputed from the
tools. The main paper is a single main.tex, so the rows are spliced into its
marked block; the supplementary document keeps its own.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.experiments._common import tool_path
from src.experiments.splice import splice

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
BANDS = [("CS1", ORDER[:5]),
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



def tab_data(ver: str) -> str:
    """The benchmark: two corpora, their pools and their oracles."""
    out = [r"\begin{tabular}{lrrrr}", r"\toprule",
           r"Corpus & problems & buggy & correct & tests \\", r"\midrule"]
    tot = [0, 0, 0, 0]
    for gname, pids in (("Refactory (CS1)", ORDER[:5]), ("Codeforces", ORDER[5:])):
        nb = nc = nt = 0
        for pid in pids:
            d = ROOT / "data" / pid
            nb += len(list((d / "buggy").glob("*.py")))
            nc += len(list((d / "correct").glob("*.py")))
            nt += len(json.loads((d / "problem.json").read_text()).get("tests", []))
        out.append(f"{gname} & {len(pids)} & {nb:,} & {nc:,} & {nt}"
                   f" \\\\".replace(",", "{,}"))
        tot[0] += len(pids); tot[1] += nb; tot[2] += nc; tot[3] += nt
    out += [r"\midrule",
            (r"\textbf{Total} & \textbf{%d} & \textbf{%s} & \textbf{%s} & "
             r"\textbf{%d} \\"
             % (tot[0], f"{tot[1]:,}".replace(",", "{,}"),
                f"{tot[2]:,}".replace(",", "{,}"), tot[3])),
            r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def _pooled(ver: str, pid: str, approach: str) -> tuple[int, int, float] | None:
    """(n, repaired, mean RPS) pooled over every model this arm ran on.

    Refactory has no model, so it pools to itself. For the LLM arms this is the
    two builders' submissions taken together rather than one of them chosen for
    the table, which is what the arm's own row in RQ5 then decomposes.
    """
    models = ["none"] if approach == "Refactory" else [FRONTIER, CHEAP]
    n = rep = 0
    rps = 0.0
    for m in models:
        c = _cell(_summary(ver, pid), approach, m)
        if c is None:
            continue
        nn = int(c["N"]); k = round(float(c["RR"]) * nn)
        n += nn; rep += k; rps += float(c["RPS"]) * k
    return None if n == 0 else (n, rep, rps / max(rep, 1))


def tab_effect(ver: str) -> str:
    SHORT = {"Measuring Lengths in Baden": "Measuring Lengths",
             "Planning The Expedition": "Planning Expedition"}
    arms = [("Refactory", "none"), ("PyDex", FRONTIER), ("CoEP_L_fw", FRONTIER),
            ("CoEP_L", FRONTIER), ("CoEP_LF", FRONTIER)]
    head = " & ".join(["Refactory", "PyDex", r"\textsc{CoEP}\textsubscript{fw}",
                       r"\textsc{CoEP}\textsubscript{L}",
                       r"\textsc{CoEP}\textsubscript{LF}"])
    out = [r"\begin{tabular}{crlc rrrrr c rrrrr}", r"\toprule",
           r"& & & & \multicolumn{5}{c}{\textbf{RR} (\%)} & & "
           r"\multicolumn{5}{c}{\textbf{RPS}} \\",
           r"\cmidrule(lr){5-9}\cmidrule(lr){11-15}",
           r"& ID & Assignment & Rating & " + head + " & & " + head + r" \\",
           r"\midrule"]
    acc = {a: [0.0, 0.0, 0, 0] for a, _m in arms}      # rr*n, rps*rep, n, rep
    for gname, pids in (("Refactory", ORDER[:5]), ("Codeforces", ORDER[5:])):
        if gname == "Codeforces":
            out.append(r"\midrule")
        for i, pid in enumerate(pids):
            df = _summary(ver, pid)
            title, rating = _meta(pid)
            title = SHORT.get(title, title)
            spine = (r"\multirow{%d}{*}{\rotatebox[origin=c]{90}{\emph{%s}}}"
                     % (len(pids), gname)) if i == 0 else ""
            rr, rps = [], []
            for a, _m in arms:
                got = _pooled(ver, pid, a)
                if got is None:
                    rr.append("--"); rps.append("--"); continue
                n, rep, p_ = got
                rr.append(f"{100*rep/n:.1f}"); rps.append(f"{p_:.3f}")
                acc[a][0] += rep; acc[a][1] += p_ * rep
                acc[a][2] += n; acc[a][3] += rep
            out.append(f"{spine} & {IDS[pid]} & {title} & {rating} & "
                       + " & ".join(rr) + " & & " + " & ".join(rps) + r" \\")
    out.append(r"\midrule")
    rr = " & ".join(f"\\textbf{{{100*acc[a][0]/acc[a][2]:.1f}}}" for a, _m in arms)
    rps = " & ".join(f"\\textbf{{{acc[a][1]/acc[a][3]:.3f}}}" for a, _m in arms)
    out.append(r"& \multicolumn{3}{l}{\textbf{Overall}} & %s & & %s \\" % (rr, rps))
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def _source_split(ver: str, model: str | tuple = (FRONTIER, CHEAP)) -> dict:
    """Repaired submissions by the mechanism that produced them, over one
    builder or, by default, both pooled."""
    models = (model,) if isinstance(model, str) else tuple(model)
    agg: dict[str, list] = {}
    for model in models:
      for pid in ORDER:
        f = ROOT / "results" / ver / pid / "coep_l.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, keep_default_na=False)
        df = df[df["Model"] == model]
        for _i, r in df.iterrows():
            if not r["Fixed"]:
                continue
            a = agg.setdefault(r["Source"], [0, 0.0])
            a[0] += 1
            a[1] += float(r["RPS"]) if r["RPS"] != "" else 0.0
    # the fallback's share is CoEP_LF's llm-sourced repairs
    fb = [0, 0.0]
    for m in models:
        for pid in ORDER:
            f = ROOT / "results" / ver / pid / "coep_lf.csv"
            if not f.exists():
                continue
            df = pd.read_csv(f, keep_default_na=False)
            df = df[(df["Model"] == m) & (df["Source"] == "llm") & (df["Fixed"])]
            fb[0] += len(df)
            fb[1] += df["RPS"].astype(float).sum()
    agg["llm"] = fb
    return agg


def tab_source(ver: str) -> str:
    agg = _source_split(ver)
    tot = sum(v[0] for k, v in agg.items() if k != "llm")
    rows = [("rules", "1. rules", r"$\bullet$"),
            ("reference", "2. reference transplant", "--"),
            ("llm", "3. LLM (\\textsc{CoEP}\\textsubscript{LF})", "--")]
    out = [r"\begin{tabular}{lrrc}", r"\toprule",
           r"Repair source & share (\%) & mean RPS & labelled \\", r"\midrule"]
    for k, name, lab in rows:
        v = agg.get(k, [0, 0.0])
        if k == "llm":
            out.append(r"\midrule")
        out.append(f"{name} & {100*v[0]/max(tot,1):.1f} & "
                   f"{v[1]/max(v[0],1):.3f} & {lab} \\\\")
    # framework-only ablation, if the pass has been run
    fw = [(_cell(_summary(ver, p), "CoEP_L_fw", m), p)
          for m in (FRONTIER, CHEAP) for p in ORDER]
    fw = [(c, p) for c, p in fw if c is not None]
    out.append(r"\midrule")
    if fw:
        n = sum(int(c["N"]) for c, _p in fw)
        rep = sum(round(float(c["RR"]) * int(c["N"])) for c, _p in fw)
        rps = sum(float(c["RPS"]) * round(float(c["RR"]) * int(c["N"]))
                  for c, _p in fw) / max(rep, 1)
        base = [_cell(_summary(ver, p), "CoEP_L", m)
                for m in (FRONTIER, CHEAP) for p in ORDER]
        bn = sum(int(c["N"]) for c in base)
        brep = sum(round(float(c["RR"]) * int(c["N"])) for c in base)
        brps = sum(float(c["RPS"]) * round(float(c["RR"]) * int(c["N"]))
                   for c in base) / max(brep, 1)
        out += [r"\multicolumn{4}{l}{\emph{Framework-only ablation"
                r" (builder rules removed),}}\\",
                r"\multicolumn{4}{l}{\emph{first column is RR (\%) rather than share}}\\",
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




def tab_att(ver: str) -> str:
    """Turnaround, split into the local search and the model wait behind it."""
    out = [r"\begin{tabular}{llrrr}", r"\toprule",
           r"Arm & Builder & $\mathrm{ATT}_{\mathrm{cpu}}$ &"
           r" $\mathrm{ATT}_{\mathrm{api}}$ & $\mathrm{ATT}_{\mathrm{tot}}$ \\",
           r"\midrule"]
    for model, tag in ((FRONTIER, r"\texttt{claude-sonnet-5}"),
                       (CHEAP, r"\texttt{gpt-5.4-mini}")):
        if model == CHEAP:
            out.append(r"\midrule")
        for arm, label in (("PyDex", "PyDex"),
                           ("CoEP_LF", r"\textsc{CoEP}\textsubscript{LF}")):
            n = cpu = api = 0.0
            for pid in ORDER:
                c = _cell(_summary(ver, pid), arm, model)
                if c is None:
                    continue
                nn = int(c["N"]); n += nn
                cpu += float(c["ATT_cpu"]) * nn
                api += float(c["ATT_api"]) * nn
            cpu /= max(n, 1); api /= max(n, 1)
            out.append(f"{label} & {tag} & {cpu:.2f} & {api:.2f} & "
                       f"{cpu + api:.2f} \\\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"

def tab_learn(ver: str) -> str:
    """RQ4 as a funnel: what failed, what was tried, what survived, what it fixed."""
    import re
    failed = attempted = kept = 0
    fired: set[str] = set()
    gain = loss = 0
    for m in (FRONTIER, CHEAP):
        for pid in ORDER:
            l = pd.read_csv(ROOT / "results" / ver / pid / "coep_l.csv",
                            keep_default_na=False)
            l = l[l.Model == m]
            miss = l[~l.Fixed.astype(bool)]
            failed += len(miss)
            if not len(miss):
                continue
            # induction is only tried where the fallback repaired the miss
            lf = pd.read_csv(ROOT / "results" / ver / pid / "coep_lf.csv",
                             keep_default_na=False)
            lf = lf[(lf.Model == m)
                    & lf.Buggy.astype(str).isin(miss.Buggy.astype(str))]
            attempted += int(lf.Fixed.astype(bool).sum())
            learned = tool_path(pid, m, "tools").parent / "sl" / "learned.py"
            names = (re.findall(r'Rule\("([^"]+)"', learned.read_text())
                     if learned.exists() else [])
            kept += len(names)
            f = ROOT / "results" / ver / pid / "coep_l_sl.csv"
            if not f.exists() or not names:
                continue
            sl = pd.read_csv(f, keep_default_na=False)
            sl = sl[sl.Model == m]
            was = dict(zip(l.Buggy.astype(str), l.Fixed.astype(bool)))
            for _i, r in sl.iterrows():
                k = str(r["Buggy"])
                if k not in was:
                    continue
                now = bool(r["Fixed"])
                if now and not was[k]:
                    gain += 1
                    fired |= set(json.loads(r["Rules_L"] or "[]")) & set(names)
                elif was[k] and not now:
                    loss += 1
    rows = [("Submissions \\textsc{CoEP}\\textsubscript{L} failed to repair", failed),
            ("\\quad of those, induction attempted", attempted),
            ("\\quad\\quad new rules kept", kept),
            ("\\quad\\quad\\quad rules that later repaired a submission", len(fired)),
            ("Submissions newly repaired", gain),
            ("\\quad regressed", loss)]
    out = [r"\begin{tabular}{lr}", r"\toprule",
           r"Stage & count \\", r"\midrule"]
    for name, n in rows:
        if name.startswith("Submissions newly"):
            out.append(r"\midrule")
        out.append(f"{name} & {n} \\\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"



def tab_cost(ver: str) -> str:
    """Escalation and what it costs, per assignment, over both builders."""
    out = [r"\begin{tabular}{lrrrr}", r"\toprule",
           r"& $e$ (\%) & calls & $\mathrm{ATT}_{\mathrm{cpu}}$ (s) &"
           r" build (min) \\", r"\midrule"]
    tn = tc = 0
    tcpu = tb = 0.0
    for pid in ORDER:
        n = calls = 0
        cpu = bmin = 0.0
        for m in (FRONTIER, CHEAP):
            d = pd.read_csv(ROOT / "results" / ver / pid / "coep_lf.csv",
                            keep_default_na=False)
            d = d[d.Model == m]
            n += len(d)
            calls += int((pd.to_numeric(d["$API"], errors="coerce").fillna(0) > 0).sum())
            c = _cell(_summary(ver, pid), "CoEP_LF", m)
            cpu += float(c["ATT_cpu"]) * len(d)
            bmin += float(c["ATT_build"]) / 60
        out.append(f"{IDS[pid]} & {100 * calls / n:.1f} & {calls} & "
                   f"{cpu / n:.2f} & {bmin / 2:.0f} \\\\")
        tn += n; tc += calls; tcpu += cpu; tb += bmin
    out += [r"\midrule",
            r"\textbf{All} & \textbf{%.1f} & \textbf{%d} & \textbf{%.2f} & "
            r"\textbf{%.0f} \\" % (100 * tc / tn, tc, tcpu / tn, tb / 2),
            r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def tab_rules(ver: str) -> str:
    """The rules that carry the most submissions, counted as submissions."""
    from collections import defaultdict
    span, subs = defaultdict(set), defaultdict(set)
    for m in (FRONTIER, CHEAP):
        for pid in ORDER:
            d = pd.read_csv(ROOT / "results" / ver / pid / "coep_l.csv",
                            keep_default_na=False)
            d = d[(d.Model == m) & d.Fixed.astype(bool) & (d.Source == "rules")]
            for _i, r in d.iterrows():
                for n in set(json.loads(r["Rules_L"])):
                    span[n].add(IDS[pid]); subs[n].add((pid, str(r["Buggy"])))
    rows = sorted(subs.items(), key=lambda kv: -len(kv[1]))[:8]
    out = [r"\begin{tabular}{llrr}", r"\toprule",
           r"Rule & where & submissions & assignments \\", r"\midrule"]
    for n, sset in rows:
        kind = "always-on" if n.startswith("generic_") else ",".join(sorted(span[n]))
        out.append(f"\\texttt{{{n.replace('_', chr(92)+'_')}}} & {kind} & "
                   f"{len(sset)} & {len(span[n])} \\\\")
    au = {n for n in subs if not n.startswith("generic_")}
    multi = [n for n in au if len(span[n]) > 1]
    out += [r"\midrule",
            r"\multicolumn{4}{l}{%d builder-written rules fired, %d on more than "
            r"one assignment} \\" % (len(au), len(multi)),
            r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"


def tab_pool(ver: str) -> str:
    """The pool-size ablation: coverage and patch size as the pool thins."""
    from collections import defaultdict
    f = ROOT / "results" / ver / "pool_ablation.json"
    if not f.exists():
        return "% pool_ablation.json absent; run `run.py pool`\n"
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in json.loads(f.read_text()):
        a = agg[(r["k"], r["arm"])]
        a[0] += 1
        if r["fixed"]:
            a[1] += 1; a[2] += r["rps"] or 0.0
    out = [r"\begin{tabular}{lrrrr}", r"\toprule",
           r"& \multicolumn{2}{c}{RR (\%)} & \multicolumn{2}{c}{RPS} \\",
           r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
           r"pool & \textsc{CoEP}\textsubscript{fw} & full & "
           r"\textsc{CoEP}\textsubscript{fw} & full \\", r"\midrule"]
    for k in (0, 1, 2, 5, 10, -1):
        fw, fu = agg[(k, "fw")], agg[(k, "full")]
        if not fw[0]:
            continue
        lab = "all" if k < 0 else str(k)
        out.append(f"{lab} & {100*fw[1]/fw[0]:.1f} & {100*fu[1]/fu[0]:.1f} & "
                   f"{fw[2]/max(fw[1],1):.3f} & {fu[2]/max(fu[1],1):.3f} \\\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(out) + "\n"

def tab_robust(ver: str) -> str:
    def cell(t):
        return f"{100*t[0]:.1f} / {t[1]:.3f}" if t else "--"

    out = [r"\begin{tabular}{@{}l@{\hskip 4pt}ccc@{}}", r"\toprule",
           r"& Refactory & PyDex & \textsc{CoEP}\textsubscript{LF} \\",
           r"Stratum & \multicolumn{3}{c}{RR (\%) / RPS} \\", r"\midrule",
           r"\multicolumn{4}{l}{\emph{Difficulty} (\texttt{claude-sonnet-5})}\\"]
    for name, pids in BANDS:
        out.append(f"\\quad {name} & {cell(_band(ver, pids, 'Refactory', 'none'))}"
                   f" & {cell(_band(ver, pids, 'PyDex', FRONTIER))}"
                   f" & {cell(_band(ver, pids, 'CoEP_LF', FRONTIER))} \\\\")
    out += [r"\midrule", r"\multicolumn{4}{l}{\emph{Builder}}\\"]
    for model, name in ((FRONTIER, r"\texttt{claude-sonnet-5}"),
                        (CHEAP, r"\texttt{gpt-5.4-mini}")):
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
    ap.add_argument("--ver", default="",
                    help="optional subdirectory under results/; empty means "
                         "results/ itself, which is where the campaign wrote")
    args = ap.parse_args(argv)
    for name, body in (("tab_data", tab_data(args.ver)),
                       ("tab_effect", tab_effect(args.ver)),
                       ("tab_att", tab_att(args.ver)),
                       ):
        splice(name, body, "run.py tables")
        print(f"  spliced {name} into paper/main.tex")
    for name, body in (("tab_source", tab_source(args.ver)),
                       ("tab_cost", tab_cost(args.ver)),
                       ("tab_rules", tab_rules(args.ver)),
                       ("tab_pool", tab_pool(args.ver)),
                       ("tab_robust", tab_robust(args.ver)),
                       ):
        (PAPER / "supp" / f"{name}.tex").write_text(body)
        print(f"  wrote paper/supp/{name}.tex")
    return 0
