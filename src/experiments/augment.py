"""`run.py augment` — do the repairs still pass tests nobody searched against?

R1-R5 ship 7.4 instructor tests per assignment, and those same tests guide every
arm's search and decide what counts as a repair. This driver draws fresh inputs
from a per-assignment generator, labels each by differential testing -- the
majority output of the class's correct programs (a sample of them plus the
instructor's reference) -- and keeps only inputs on which at least 90% of them
agree, so an input outside the specification (where correct programs disagree)
never becomes a test. Every arm's repairs are then re-run on the original suite
plus these held-out tests. C1-C6 are skipped: their suites are Codeforces' full
official test sets.

    python run.py augment make     # data_aug/<pid>/problem.json (original + new)
    python run.py augment make-search   # data_dt/: CoEP+DT's repair-time suite (disjoint)
    python run.py augment make-search --gen llm --model M   # data_dtg/M/: builder-written generator
    python run.py augment link     # copy data/'s programs back into data_dt*/ (not tracked)
    python run.py augment check [--ver V]   # results/<V>/augmented.csv, per arm
    python run.py augment pairs --ver dt,dtg  # McNemar/Wilcoxon vs PyDex -> results/heldout_pairs.csv
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src.experiments._common import load_env, load_problem
from src.prompts import render
from src.experiments.refactory_results import unwrap
from src.runner.testing import run_tests
from src.utils import llm as llm_mod

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data_aug"
DT = ROOT / "data_dt"
CS1 = ["refactory_q1", "refactory_q2", "refactory_q3", "refactory_q4", "refactory_q5"]
N_CAND, N_KEEP, N_VOTERS, AGREE = 300, 100, 40, 0.9
SENTINEL = "__no_such_output__"
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def _gen(pid: str, rng: random.Random) -> dict:
    """One random test input in the assignment's own calling convention."""
    if pid == "refactory_q1":                  # search(x, sorted seq)
        seq = sorted(rng.sample(range(-15, 16), rng.randint(0, 7)))
        return {"args": [rng.randint(-20, 20), seq]}
    if pid == "refactory_q2":                  # birthdays as [month, day] pairs
        pb = [[rng.choice(MONTHS[:5]), str(rng.randint(1, 6))]
              for _ in range(rng.randint(1, 6))]
        pb = [list(p) for p in dict.fromkeys(map(tuple, pb))]
        entry = rng.choice(["unique_day", "unique_month", "contains_unique_day"])
        key = (str(rng.randint(1, 6)) if entry == "unique_day"
               else rng.choice(MONTHS[:5]))
        return {"args": [key, pb], "entry": entry}
    if pid == "refactory_q3":                  # remove_extras(lst)
        return {"args": [[rng.randint(0, 5) for _ in range(rng.randint(0, 8))]]}
    if pid == "refactory_q4":                  # sort_age([[gender, age], ...])
        ages = rng.sample(range(1, 90), rng.randint(0, 6))
        return {"args": [[[rng.choice("MF"), a] for a in ages]]}
    if pid == "refactory_q5":                  # top_k(lst, k)
        lst = [rng.randint(0, 9) for _ in range(rng.randint(0, 9))]
        return {"args": [lst, rng.randint(0, len(lst))]}
    raise ValueError(pid)


def _outputs(src: str, problem: dict, tests: list[dict]) -> list[str]:
    """Each test's output as a JSON string ('!err' on an error or timeout)."""
    probe = dict(problem, tests=[dict(t, expected=SENTINEL) for t in tests])
    res = run_tests(src, probe)
    out = ["!err"] * len(tests)
    for f in res.failures:
        if "got" in f:
            out[f["index"]] = json.dumps(f["got"], sort_keys=True)
    return out


def _key(t: dict) -> str:
    """A test's input, without its expected output."""
    return json.dumps({k: v for k, v in t.items() if k != "expected"}, sort_keys=True)


def _fresh(inputs, seen: set[str]) -> list[dict]:
    """Up to N_CAND distinct inputs not already in seen (which it extends)."""
    cands = []
    for t in inputs:
        k = _key(t)
        if k not in seen:
            seen.add(k)
            cands.append(t)
            if len(cands) == N_CAND:
                break
    return cands


def _vote(pid: str, cands: list[dict], voter_seed: int,
          pool_dir: Path | None = None) -> list[dict]:
    """Up to N_KEEP of cands, each labelled by the voters' majority output.

    Voters are a sample of the correct programs in pool_dir (default: the whole
    class) plus the instructor's reference.
    """
    problem = load_problem(pid)
    pool = sorted((pool_dir or ROOT / "data" / pid / "correct").glob("*.py"))
    voters = [p.read_text() for p in
              random.Random(voter_seed).sample(pool, min(N_VOTERS, len(pool)))]
    voters.append((ROOT / "data" / pid / "reference.py").read_text())
    with ThreadPoolExecutor(16) as ex:
        votes = list(ex.map(lambda s: _outputs(s, problem, cands), voters))
    kept = []
    for i, t in enumerate(cands):
        top, n = Counter(v[i] for v in votes).most_common(1)[0]
        if top != "!err" and n / len(votes) >= AGREE:
            kept.append(dict(t, expected=json.loads(top)))
        if len(kept) == N_KEEP:
            break
    return kept


_DRAW = """
import json, random, sys
rng, out, err = random.Random(sys.argv[1]), [], None
for _ in range(int(sys.argv[2])):
    try:
        out.append(gen(rng))
    except Exception as e:
        err = err or f"{type(e).__name__}: {e}"
print("\\n" + json.dumps({"inputs": out, "error": err}))
"""


def _draw(code: str, seed: str, n: int = 20 * N_CAND) -> tuple[list[dict], str | None]:
    """n calls of the generated gen(rng), in a child process; (inputs, first error)."""
    try:
        r = subprocess.run([sys.executable, "-c", code + _DRAW, seed, str(n)],
                           capture_output=True, text=True, timeout=120)
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return [], f"gen did not return {n} inputs within 120 s"
    except (json.JSONDecodeError, IndexError):
        return [], (r.stderr.strip().splitlines() or ["gen produced no output"])[-1]
    ok = [t for t in res["inputs"] if isinstance(t, dict) and isinstance(t.get("args"), list)
          and set(t) <= {"args", "entry"}]
    if len(ok) < len(res["inputs"]):
        res["error"] = res["error"] or 'gen returned something other than {"args": [...]}'
    return ok, res["error"]


def _llm_inputs(pid: str, model: str, seen: set[str], rounds: int = 3):
    """The builder writes gen(rng); validate it against the reference and refine.

    A round fails if gen raises, returns a malformed input, or the reference
    rejects more than 10% of its inputs; the next round sees why. The round
    with the most inputs the reference accepts is kept.
    """
    problem = load_problem(pid)
    reference = (ROOT / "data" / pid / "reference.py").read_text()
    best, cost, feedback = (None, []), {"in": 0, "out": 0, "usd": 0.0, "s": 0.0}, ""
    for rnd in range(rounds):
        call = llm_mod.complete(render(
            "input_gen", description=problem.get("description", ""), reference=reference,
            tests="\n".join(json.dumps(t) for t in problem["tests"]), feedback=feedback),
            model=model)
        for k, a in (("in", "in_tokens"), ("out", "out_tokens"), ("usd", "usd"), ("s", "seconds")):
            cost[k] += getattr(call, a)
        code = call.code or ""
        inputs, err = _draw(code, f"{pid}:llm")
        cands = _fresh(inputs, set(seen))
        outs = _outputs(reference, problem, cands) if cands else []
        rejected = [t for t, o in zip(cands, outs) if o == "!err"]
        valid = [t for t, o in zip(cands, outs) if o != "!err"]
        print(f"  {pid} {model} round {rnd + 1}: {len(cands)} distinct, "
              f"{len(rejected)} rejected by the reference" + (f", error: {err}" if err else ""))
        if len(valid) > len(best[1]):
            best = (code, valid)
        if not err and cands and len(rejected) <= 0.1 * len(cands):
            break
        why = err or (f"the reference raised an error or timed out on {len(rejected)} of "
                      f"{len(cands)} inputs, e.g. {json.dumps(rejected[:3])}" if cands
                      else "it produced no new inputs")
        feedback = (f"\n## This is a refinement round\nYour previous generator:\n"
                    f"```python\n{code}\n```\nIt failed because {why}.\n")
    cost["rounds"] = rnd + 1
    seen.update(_key(t) for t in best[1])
    return best[0], best[1], cost


def make() -> None:
    """The held-out evaluation suite: data_aug/<pid>/problem.json."""
    for pid in CS1:
        problem = load_problem(pid)
        rng = random.Random(pid)
        cands = _fresh(iter(lambda: _gen(pid, rng), None), {_key(t) for t in problem["tests"]})
        kept = _vote(pid, cands, 0)
        d = OUT / pid
        d.mkdir(parents=True, exist_ok=True)
        aug = dict(problem, tests=problem["tests"] + kept, n_original=len(problem["tests"]))
        (d / "problem.json").write_text(json.dumps(aug, indent=1))
        print(f"{pid}: {len(problem['tests'])} original + {len(kept)} held-out tests")


def make_search(gen: str = "hand", model: str = "") -> None:
    """The repair-time suite of CoEP+DT, with the buggy and correct programs.

    gen=hand: our per-assignment generators -> data_dt/<pid>/
    gen=llm:  a generator the builder `model` writes -> data_dtg/<model>/<pid>/

    Drawn with its own seed and voter sample, and disjoint from the held-out
    suite, so a repair accepted against it is still judged on inputs it never saw.
    Everything it uses -- the class's correct programs, the reference, and a
    generator of valid inputs -- is available at deployment; no instructor test
    is added.
    """
    if gen == "llm":
        load_env()
    for pid in CS1:
        problem = load_problem(pid)
        held = json.loads((OUT / pid / "problem.json").read_text())["tests"]
        seen = {_key(t) for t in held}
        n_held = len(held) - len(problem["tests"])
        d = (DT / pid) if gen == "hand" else (ROOT / "data_dtg" / model / pid)
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(ROOT / "data" / pid, d)
        if gen == "hand":
            rng = random.Random(f"{pid}:search")
            cands = _fresh(iter(lambda: _gen(pid, rng), None), seen)
        else:
            code, cands, cost = _llm_inputs(pid, model, seen)
            (d / "gen.py").write_text(code or "")
            (d / "gen_cost.json").write_text(json.dumps(cost))
        kept = _vote(pid, cands, 1)
        dt = dict(problem, tests=problem["tests"] + kept, n_original=len(problem["tests"]))
        (d / "problem.json").write_text(json.dumps(dt, indent=1))
        print(f"{pid}: {len(problem['tests'])} instructor + {len(kept)} differential tests "
              f"(disjoint from the {n_held} held-out ones)")


def link() -> None:
    """Restore the programs a CoEP+DT suite runs on.

    data_dt/ and data_dtg/ keep only what amplification produced (problem.json,
    plus the builder's gen.py and gen_cost.json); their buggy and correct
    programs are data/<pid>/'s, copied back so `--data-root data_dtg/<model>`
    works as data/ does.
    """
    for prob in [*DT.glob("*/problem.json"), *(ROOT / "data_dtg").glob("*/*/problem.json")]:
        d, src = prob.parent, ROOT / "data" / prob.parent.name
        for kind in ("buggy", "correct"):
            if not (d / kind).exists():
                shutil.copytree(src / kind, d / kind)
        if not (d / "reference.py").exists():
            shutil.copy(src / "reference.py", d / "reference.py")


ARMS = [("refactory", "Refactory"), ("pydex", "PyDex"), ("direct_llm", "LLM_Direct"),
        ("coep_l_fw", "CoEP_L_fw"), ("coep_l", "CoEP_L"), ("coep_lf", "CoEP_LF")]


def check(ver: str = "") -> pd.DataFrame:
    rows = []
    for pid in CS1:
        aug = json.loads((OUT / pid / "problem.json").read_text())
        for stem, arm in ARMS:
            f = ROOT / "results" / ver / pid / f"{stem}.csv"
            if not f.exists():
                continue
            d = pd.read_csv(f, keep_default_na=False)
            ok = d[d.Fixed.astype(str) == "True"]
            patches = {p: None for p in ok.Patch.astype(str)}
            unwrap_ = stem == "refactory"

            def passes(p: str) -> bool:
                r = run_tests(unwrap(p) if unwrap_ else p, aug)
                return r.error is None and r.total > 0 and r.passed == r.total

            with ThreadPoolExecutor(16) as ex:
                verdict = dict(zip(patches, ex.map(passes, patches)))
            for model, g in d.groupby(d.Model.astype(str)):
                gok = g[g.Fixed.astype(str) == "True"]
                still = sum(verdict[p] for p in gok.Patch.astype(str))
                rows.append({"pid": pid, "arm": arm, "model": model, "n": len(g),
                             "fixed": len(gok), "fixed_aug": int(still)})
            print(f"{pid} {arm}: " + ", ".join(
                f"{r['model']} {r['fixed']}->{r['fixed_aug']}" for r in rows
                if r["pid"] == pid and r["arm"] == arm))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / ver / "augmented.csv", index=False)
    return df


def pairs(vers: list[str]) -> pd.DataFrame:
    """Per-program held-out verdicts of CoEP_LF under each results/<ver>/ against
    PyDex and the campaign's CoEP_LF: exact McNemar on held-out repair, and
    Wilcoxon on RPS over the programs both arms repaired that survive.
    -> results/heldout_pairs.csv
    """
    from scipy.stats import binomtest, wilcoxon

    def verdicts(f: Path, aug: dict) -> dict:
        d = pd.read_csv(f, keep_default_na=False)
        ok = [r for _, r in d[d.Fixed.astype(str) == "True"].iterrows()]
        with ThreadPoolExecutor(16) as ex:
            got = ex.map(lambda r: run_tests(r.Patch, aug).all_pass, ok)
        return {(r.Model, r.Buggy): (v, float(r.RPS)) for r, v in zip(ok, got)}

    arms = {"pydex": "pydex", "campaign": "coep_lf"} | {v: "coep_lf" for v in vers}
    rows = []
    for pid in CS1:
        aug = json.loads((OUT / pid / "problem.json").read_text())
        got = {a: verdicts(ROOT / "results" / ("" if a in ("pydex", "campaign") else a)
                           / pid / f"{stem}.csv", aug) for a, stem in arms.items()}
        subs = sorted(p.stem for p in (ROOT / "data" / pid / "buggy").glob("*.py"))
        for m in ("claude-sonnet-5", "gpt-5.4-mini"):
            for b in subs:
                row = {"pid": pid, "model": m, "buggy": b}
                for a in arms:
                    v, r = got[a].get((m, b), (False, None))
                    row[a], row[f"{a}_rps"] = v, r
                rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "heldout_pairs.csv", index=False)
    for m, g in df.groupby("model"):
        for v in vers:
            for other in ("pydex", "campaign"):
                b10, b01 = int((g[v] & ~g[other]).sum()), int((~g[v] & g[other]).sum())
                p = binomtest(min(b10, b01), b10 + b01).pvalue if b10 + b01 else 1.0
                print(f"{m} {v} vs {other}: held-out RR {100 * g[v].mean():.1f} vs "
                      f"{100 * g[other].mean():.1f} (only {v} {b10}, only {other} {b01}, "
                      f"McNemar p={p:.2g})")
            c = g[g[v] & g.pydex]
            print(f"{m} {v} vs pydex on {len(c)} common survivors: RPS "
                  f"{c[f'{v}_rps'].mean():.3f} vs {c.pydex_rps.mean():.3f} "
                  f"(Wilcoxon p={wilcoxon(c[f'{v}_rps'], c.pydex_rps).pvalue:.2g})")
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run.py augment")
    ap.add_argument("action", choices=["make", "make-search", "link", "check", "pairs"])
    ap.add_argument("--ver", default="", help="results/<ver>/ to judge (check)")
    ap.add_argument("--gen", choices=["hand", "llm"], default="hand", help="make-search")
    ap.add_argument("--model", default="claude-sonnet-5", help="make-search --gen llm")
    args = ap.parse_args(argv)
    if args.action == "check":
        check(args.ver)
    elif args.action == "pairs":
        pairs(args.ver.split(","))
    elif args.action == "link":
        link()
    elif args.action == "make":
        make()
    else:
        make_search(args.gen, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
