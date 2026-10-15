"""`run.py splits` — build on earlier submissions, repair later ones.

The main campaign builds each tool from the same pool it is scored on. Here the
tool and its reference pool see only a training prefix of the submissions, and
it is scored on held-out buggy programs it could not have seen:

* Codeforces (C1-C5): a temporal split. Submission ids are assigned in time
  order, so the last quarter of all submissions (buggy and correct) is the
  future; its buggy programs are the test set.
* CS1 (R1-R5): the corpus records neither student nor time, so the order is a
  seeded shuffle (seeds 0-2) and the same positional split applies.

The training pool is the first f of that order, f in {10, 25, 50, 75}%, so the
pools are nested and the test set is fixed across f: the same programs are
repaired by tools built from more and more of the class. C6 has five
submissions and is left out.

    python run.py splits make                 # data_splits/<scheme>/f<NN>/{train,eval}/<pid>/
    python run.py splits jobs --phase build   # one line per missing tool
    python run.py splits jobs --phase eval    # one line per (scheme, f|same, pid)
    python run.py splits report               # aggregate results/splits/...
    python run.py splits make-dt              # CS1: eval_dt/<model>/ suites (CoEP+DT)
    python run.py splits jobs --phase eval --dt   # -> results/splits_dt/
    python run.py splits report --dt

Each job builds with `run.py build --data-root .../train --tools-root
tools_splits/<scheme>/f<NN>` and evaluates with `run.py compare --data-root
.../eval` (buggy = the test set, correct = the training pool's correct
programs, i.e. the references a course would hold at that point).
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SPLITS = ROOT / "data_splits"
TOOLS = ROOT / "tools_splits"

CS1 = ["refactory_q1", "refactory_q2", "refactory_q3", "refactory_q4", "refactory_q5"]
CF = ["cf_110A", "cf_131A", "cf_1011B", "cf_125A", "cf_11B"]
FRACS = [10, 25, 50, 75]
TEST = 0.25
SCHEMES = {"s0": 0, "s1": 1, "s2": 2}        # CS1 shuffle seeds; CF is temporal (s0)
MODELS = ["claude-sonnet-5", "gpt-5.4-mini"]


def _order(pid: str, seed: int) -> list[tuple[str, str]]:
    """All submissions as (kind, stem) in the split order."""
    subs = [(k, p.stem) for k in ("buggy", "correct")
            for p in sorted((DATA / pid / k).glob("*.py"))]
    if pid in CF:
        return sorted(subs, key=lambda s: int(s[1]))
    random.Random(seed).shuffle(subs)
    return subs


def schemes_for(pid: str) -> list[str]:
    return ["s0"] if pid in CF else list(SCHEMES)


def make() -> dict:
    manifest = {}
    for pid in CS1 + CF:
        for scheme in schemes_for(pid):
            order = _order(pid, SCHEMES[scheme])
            cut = int(round(len(order) * (1 - TEST)))
            test = [s for k, s in order[cut:] if k == "buggy"]
            entry = {"test": test, "train": {}}
            for f in FRACS:
                head = order[:int(round(len(order) * f / 100))]
                tb = [s for k, s in head if k == "buggy"]
                tc = [s for k, s in head if k == "correct"]
                entry["train"][f] = {"buggy": tb, "correct": tc}
                base = SPLITS / scheme / f"f{f:02d}"
                for part, buggy, correct in (("train", tb, tc), ("eval", test, tc)):
                    d = base / part / pid
                    shutil.rmtree(d, ignore_errors=True)
                    for kind, stems in (("buggy", buggy), ("correct", correct)):
                        (d / kind).mkdir(parents=True)
                        for s in stems:
                            shutil.copy(DATA / pid / kind / f"{s}.py", d / kind / f"{s}.py")
                    shutil.copy(DATA / pid / "problem.json", d / "problem.json")
            # same test programs, the full pool and the campaign's own tools: the
            # same-pool reference, re-measured under the same machine load
            d = SPLITS / scheme / "same" / "eval" / pid
            shutil.rmtree(d, ignore_errors=True)
            (d / "buggy").mkdir(parents=True)
            shutil.copytree(DATA / pid / "correct", d / "correct")
            for s in test:
                shutil.copy(DATA / pid / "buggy" / f"{s}.py", d / "buggy" / f"{s}.py")
            shutil.copy(DATA / pid / "problem.json", d / "problem.json")
            manifest.setdefault(scheme, {})[pid] = entry
            print(f"{scheme} {pid}: test {len(test)} buggy; train "
                  + ", ".join(f"{f}%={len(entry['train'][f]['buggy'])}b/"
                              f"{len(entry['train'][f]['correct'])}c" for f in FRACS))
    (SPLITS / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def make_dt(models: list[str] = MODELS) -> None:
    """CS1 eval dirs for CoEP+DT: data_splits/<scheme>/<tag>/eval_dt/<model>/<pid>/.

    The builder's input generator (data_dtg/<model>/<pid>/gen.py) sees no
    submission, so it is the campaign's own, drawn with the same seed; only the
    labels change: the voters are the training pool's correct programs (plus
    the reference), the ones a course would hold at that point.
    """
    from src.experiments.augment import OUT, _draw, _fresh, _key, _vote
    for scheme in SCHEMES:
        for tag in [f"f{f:02d}" for f in FRACS] + ["same"]:
            for pid in CS1:
                src = SPLITS / scheme / tag / "eval" / pid
                prob = json.loads((src / "problem.json").read_text())
                held = json.loads((OUT / pid / "problem.json").read_text())["tests"]
                for m in models:
                    inputs, _ = _draw((ROOT / "data_dtg" / m / pid / "gen.py").read_text(),
                                      f"{pid}:llm")
                    kept = _vote(pid, _fresh(inputs, {_key(t) for t in held}), 1,
                                 src / "correct")
                    d = SPLITS / scheme / tag / "eval_dt" / m / pid
                    shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(src, d)
                    (d / "problem.json").write_text(json.dumps(
                        dict(prob, tests=prob["tests"] + kept, n_original=len(prob["tests"])),
                        indent=1))
                    print(f"{scheme} {tag} {pid} {m}: {len(kept)} differential tests "
                          f"({len(list((src / 'correct').glob('*.py')))} correct programs vote)")


def jobs(models: list[str] = MODELS, phase: str = "build", dt: bool = False) -> None:
    """Shell lines, one per job.

    build: one line per (scheme, f, pid, model), skipped when that tool exists;
           LLM-bound, so it tolerates a busy machine.
    eval:  one line per (scheme, f, pid) running every compare for it in sequence
           (they share one results file), plus one same-pool line per (scheme,
           pid) on the campaign's tools (copied to tools_splits/same so its
           self-learning never touches tools/). The rule search and the tests run
           under wall clocks, so this phase should run on a quiet machine.
    """
    if phase == "eval" and not (TOOLS / "same").exists():
        shutil.copytree(ROOT / "tools", TOOLS / "same",
                        ignore=shutil.ignore_patterns("sl", "__pycache__"))
    tools_root = "tools_splits_dt" if dt else "tools_splits"
    if phase == "eval" and dt and not (ROOT / tools_root).exists():
        shutil.copytree(TOOLS, ROOT / tools_root,
                        ignore=shutil.ignore_patterns("sl", "__pycache__"))
    for scheme in SCHEMES:                     # s0 first, so results land early
        for f in FRACS + (["same"] if phase == "eval" else []):
            tag = f if f == "same" else f"f{f:02d}"
            for pid in CS1 + CF:
                if scheme not in schemes_for(pid) or (dt and pid not in CS1):
                    continue
                base = f"data_splits/{scheme}/{tag}"
                tools = f"{tools_root}/same" if f == "same" else f"{tools_root}/{scheme}/{tag}"
                ver = f"splits{'_dt' if dt else ''}/{scheme}/{tag}"
                if phase == "build":
                    for m in models:
                        if (TOOLS / scheme / tag / pid / m / "cost.json").exists():
                            continue
                        print(f"python3 run.py build --problem {pid} --data-root {base}/train "
                              f"--tools-root {tools} --model {m} "
                              f"> logs/splits/build_{scheme}_{tag}_{pid}_{m}.log 2>&1")
                    continue
                ev = (lambda m: f"{base}/eval_dt/{m}") if dt else (lambda m: f"{base}/eval")
                cmds = [f"python3 run.py compare --problem {pid} --data-root {ev(m)} "
                        f"--tools-root {tools} --ver {ver} --model {m}" for m in models]
                cmds += [f"python3 run.py compare --problem {pid} --data-root {ev(models[0])} "
                         f"--tools-root {tools} --ver {ver} --model {models[0]} --framework-only"]
                log = f"logs/splits/eval{'_dt' if dt else ''}_{scheme}_{tag}_{pid}.log"
                print(f"( {' && '.join(cmds)} ) > {log} 2>&1")


def _arm(ver: Path, pid: str, stem: str, model: str) -> tuple[int, int, float]:
    f = ver / pid / f"{stem}.csv"
    if not f.exists():
        return 0, 0, 0.0
    d = pd.read_csv(f, keep_default_na=False)
    d = d[d.Model.astype(str) == model]
    ok = d[d.Fixed.astype(str) == "True"]
    return len(d), len(ok), float(pd.to_numeric(ok.RPS).sum())


def report(models: list[str] = MODELS, dt: bool = False) -> pd.DataFrame:
    """results/splits[_dt]/report.csv; with dt, CS1 only (CF has no DT)."""
    results = ROOT / "results" / ("splits_dt" if dt else "splits")
    manifest = json.loads((SPLITS / "manifest.json").read_text())
    rows = []
    for scheme, pids in manifest.items():
        for pid, entry in pids.items():
            if dt and pid not in CS1:
                continue
            test = set(entry["test"])
            for f in FRACS:
                ver = results / scheme / f"f{f:02d}"
                for model in models:
                    cost = TOOLS / scheme / f"f{f:02d}" / pid / model / "cost.json"
                    c = json.loads(cost.read_text()) if cost.exists() else {}
                    row = {"scheme": scheme, "f": f, "pid": pid, "model": model,
                           "n_test": len(test),
                           "train_buggy": len(entry["train"][str(f)]["buggy"]),
                           "train_correct": len(entry["train"][str(f)]["correct"]),
                           "pairs": c.get("n_samples"), "in_tok": c.get("in_tokens"),
                           "out_tok": c.get("out_tokens"), "build_usd": c.get("usd"),
                           "build_s": c.get("build_seconds")}
                    for arm, stem, m in (("L", "coep_l", model), ("LF", "coep_lf", model),
                                         ("fw", "coep_l_fw", models[0])):
                        n, k, rps = _arm(ver, pid, stem, m)
                        row[f"{arm}_n"], row[f"{arm}_fixed"], row[f"{arm}_rps_sum"] = n, k, rps
                    # the same test programs, full pool, campaign tools (same load)
                    for arm, stem in (("same_L", "coep_l"), ("same_LF", "coep_lf")):
                        n, k, rps = _arm(results / scheme / "same", pid, stem, model)
                        row[f"{arm}_n"], row[f"{arm}_fixed"], row[f"{arm}_rps_sum"] = n, k, rps
                    rows.append(row)
    df = pd.DataFrame(rows)
    out = results / "report.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"-> {out}")
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run.py splits")
    ap.add_argument("action", choices=["make", "make-dt", "jobs", "report"])
    ap.add_argument("--dt", action="store_true", help="CS1 with CoEP+DT (jobs, report)")
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--phase", choices=["build", "eval"], default="build")
    args = ap.parse_args(argv)
    if args.action == "make":
        make()
    elif args.action == "make-dt":
        make_dt(args.models)
    elif args.action == "jobs":
        jobs(args.models, args.phase, args.dt)
    else:
        report(args.models, args.dt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
