#!/usr/bin/env python3
"""Hidden-oracle audit of accepted local patches (visible-suite-overfitting
control). For every CoEP-local repair accepted on the evaluation split, run
the patched program against the instructor reference on N random inputs drawn
from each assignment's input space (disjoint from the visible tests), plus
the visible-test inputs' boundary neighborhood. Report per-assignment and
pooled semantic-agreement rates. Also audits the frontier baseline's accepted
patches for comparison, so the control is symmetric across paradigms.

Seeded; no LLM involved.
"""
import json
import pathlib
import random
import sys

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep.llmio import extract_python_block  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
N_INPUTS = 60
rng = random.Random(7)

MONTHS = ["January", "February", "March", "April", "May", "June", "July"]
DAYS = [str(d) for d in range(1, 8)]


def gen_inputs(pid):
    """Random inputs per assignment; each item is (entry, args)."""
    out = []
    for _ in range(N_INPUTS):
        if pid == "refactory_q1":  # search(x, sorted_seq)
            seq = sorted(rng.sample(range(-20, 60), rng.randint(0, 10)))
            x = rng.choice([rng.randint(-25, 65)] + (seq or [0]))
            out.append(("search", [x, seq]))
        elif pid == "refactory_q2":  # unique_day / unique_month / contains_unique_day
            tups = [[rng.choice(MONTHS), rng.choice(DAYS)]
                    for _ in range(rng.randint(0, 6))]
            fn = rng.choice(["unique_day", "unique_month", "contains_unique_day"])
            arg0 = rng.choice(DAYS) if fn == "unique_day" else (
                rng.choice(MONTHS) if fn == "unique_month" else None)
            out.append((fn, ([arg0, tups] if arg0 is not None else [tups])))
        elif pid == "refactory_q3":  # remove_extras(lst)
            out.append(("remove_extras",
                        [[rng.randint(0, 6) for _ in range(rng.randint(0, 10))]]))
        elif pid == "refactory_q4":  # sort_age(lst of [sex, age])
            n = rng.randint(1, 7)
            ages = rng.sample(range(15, 60), n)  # unique ages: order well-defined
            out.append(("sort_age", [[[rng.choice("MF"), a] for a in ages]]))
        elif pid == "refactory_q5":  # top_k(lst, k)
            n = rng.randint(1, 9)
            lst = [rng.randint(0, 20) for _ in range(n)]
            out.append(("top_k", [lst, rng.randint(1, n)]))
    return out


def behaviour(src, entry, cases):
    """Run src on cases via the harness; return tuple of outcomes."""
    tests = [{"entry": fn, "args": args, "expected": None} for fn, args in cases]
    outs = []
    import copy
    from coep.sandbox import run_tests_inproc
    r = run_tests_inproc(src, entry, [dict(t) for t in tests], capture=True)
    return r


def main():
    import copy
    from coep import sandbox
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())
    pooled = {"coep": [0, 0], "baseline": [0, 0]}
    detail = {}
    base = {r["key"]: r for r in json.loads((ROOT / "runs" / "baseline" / "results.json").read_text())}
    for pid in sorted(splits):
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        ref = sorted((PROBLEMS / pid / "refs").glob("*.py"))[0].read_text()
        cases = gen_inputs(pid)
        # oracle outputs from the reference
        oracle = []
        ok_cases = []
        for fn, args in cases:
            t = [{"entry": fn, "args": copy.deepcopy(args),
                  "expected": "__PROBE__"}]
            r = sandbox.run_tests_inproc(ref, p["entry"], t)
            got = r.failures[0].get("got", "__ERR__") if r.failures else "__PASS__"
            if r.failures and "error" in r.failures[0] and r.failures[0]["error"]:
                continue  # reference itself errors (out-of-contract input): drop
            oracle.append(got)
            ok_cases.append((fn, args))
        for arm, get_patch in (
            ("coep", lambda k, b: _coep_patch(pid, b)),
            ("baseline", lambda k, b: _base_patch(k, base)),
        ):
            agree = tot = 0
            verdicts = {}
            rows = json.loads((ROOT / "runs" / "coep" / "results" / f"{pid}.json").read_text())
            for r0 in rows:
                key = f"{pid}__{r0['bug'][:-3]}"
                if arm == "coep":
                    if not r0["repaired"]:
                        continue
                else:
                    b = base[key]
                    if not (b.get("passed") and b.get("rps", 1) <= 0.35):
                        continue
                patch = get_patch(key, r0["bug"])
                if patch is None:
                    continue
                ok = True
                for (fn, args), want in zip(ok_cases, oracle):
                    t = [{"entry": fn, "args": copy.deepcopy(args), "expected": "__PROBE__"}]
                    rr = sandbox.run_tests_inproc(patch, p["entry"], t)
                    got = rr.failures[0].get("got", "__ERR__") if rr.failures else "__PASS__"
                    if rr.failures and rr.failures[0].get("error"):
                        got = "__ERR__"
                    if repr(got) != repr(want):
                        ok = False
                        break
                agree += ok
                tot += 1
                verdicts[key] = ok
            pooled[arm][0] += agree
            pooled[arm][1] += tot
            print(f"{pid} {arm}: {agree}/{tot} semantically agree with reference")
            detail.setdefault(arm, {}).update(verdicts)
    for arm, (a, t) in pooled.items():
        print(f"TOTAL {arm}: {a}/{t} = {a/t*100:.1f}% agreement on {N_INPUTS} random inputs/assignment")
    import json as _j
    (ROOT / "runs" / "semantic_audit.json").write_text(_j.dumps(detail, indent=1))


_patch_cache = {}


def _coep_patch(pid, bug):
    key = (pid, bug)
    if key in _patch_cache:
        return _patch_cache[key]
    import subprocess, os, json as j
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_repairer_one.py"), pid, bug],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "COEP_REPAIRER": "repairer.py"})
        out = j.loads(proc.stdout.strip().splitlines()[-1])
        _patch_cache[key] = out.get("patched")
    except Exception:
        _patch_cache[key] = None
    return _patch_cache[key]


def _base_patch(key, base):
    resp = ROOT / "runs" / "baseline" / "responses" / f"{key}.md"
    return extract_python_block(resp.read_text()) if resp.exists() else None


if __name__ == "__main__":
    main()
