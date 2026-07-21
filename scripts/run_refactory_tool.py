#!/usr/bin/env python3
"""Non-LLM baseline: the Refactory tool (Hu et al., ASE 2019) on our eval split.

Two subcommands:

  prepare <refactory_repo_dir> <out_data_dir>
      Build a trimmed copy of the Refactory dataset containing, per question,
      the full test suite, reference, ALL correct student submissions (the
      tool's standard -s 100 configuration), and ONLY the wrong/ files that
      belong to this repo's eval split (mapped from our real_XXX.py names,
      which were assigned by 1-based enumeration of sorted(wrong/*.py) at
      import time). Then run, per question:

          python3 run.py -d <out_data_dir> -q question_N -s 100 -o -m -b

  collect <out_data_dir>
      Parse each question's refactory_online.csv, map file names back to our
      submission ids, RE-VALIDATE every repair with this repo's own harness
      (same parsed test suite as all other arms) and recompute our token-level
      RPS. A repair only counts if it passes ALL tests AND rps <= 0.35 (the
      same acceptance rule every other arm is held to). Writes
      runs/refactory_tool/results.json.
"""
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.sandbox import run_tests  # noqa: E402
from coep.evaluate import rps  # noqa: E402

MAX_RPS = 0.35


def eval_split_original_names(qdir: pathlib.Path, pid: str) -> dict:
    """Map our real_XXX.py ids -> original wrong/*.py filenames for the eval split."""
    splits = json.loads((ROOT / "benchmark" / "splits.json").read_text())[pid]
    wrong_sorted = sorted((qdir / "code" / "wrong").glob("*.py"))
    mapping = {}
    for ours in splits["eval"]:
        idx = int(re.match(r"real_(\d+)\.py", ours).group(1))  # 1-based
        mapping[ours] = wrong_sorted[idx - 1].name
    return mapping


def prepare(repo: pathlib.Path, out: pathlib.Path):
    for qdir in sorted((repo / "data").glob("question_*")):
        pid = f"refactory_{qdir.name.replace('question_', 'q')}"
        if not (ROOT / "benchmark" / "problems" / pid).exists():
            continue
        dst = out / qdir.name
        (dst / "code").mkdir(parents=True, exist_ok=True)
        for sub in ("ans",):
            shutil.copytree(qdir / sub, dst / sub, dirs_exist_ok=True)
        for sub in ("reference", "correct"):
            shutil.copytree(qdir / "code" / sub, dst / "code" / sub, dirs_exist_ok=True)
        if (qdir / "code" / "global.py").exists():
            shutil.copy(qdir / "code" / "global.py", dst / "code" / "global.py")
        wdst = dst / "code" / "wrong"
        wdst.mkdir(exist_ok=True)
        mapping = eval_split_original_names(qdir, pid)
        for orig in mapping.values():
            shutil.copy(qdir / "code" / "wrong" / orig, wdst / orig)
        print(f"{pid}: staged {len(mapping)} eval-split wrong files at {dst}")
    print(f"\nNow run, per question (from {repo}):\n"
          f"  python3 run.py -d {out} -q question_N -s 100 -o -m -b")


def collect(out: pathlib.Path):
    import pandas as pd
    results = {}
    for qdir in sorted(out.glob("question_*")):
        pid = f"refactory_{qdir.name.replace('question_', 'q')}"
        pj = json.loads((ROOT / "benchmark" / "problems" / pid / "problem.json").read_text())
        csvs = list(qdir.glob("refactory_online.csv"))
        if not csvs:
            print(f"[skip] {pid}: no refactory_online.csv (tool not run yet)")
            continue
        df = pd.read_csv(csvs[0])
        orig_repo = pathlib.Path("/workspace/refactory")
        mapping = eval_split_original_names(orig_repo / "data" / qdir.name, pid)
        by_orig = {v: k for k, v in mapping.items()}
        per = {}
        for _, row in df.iterrows():
            orig_name = str(row["File Name"])
            ours = by_orig.get(orig_name)
            if ours is None:
                continue
            repair_src = row.get("Repair")
            buggy = (ROOT / "benchmark" / "problems" / pid / "buggy" / ours).read_text()
            rec = {"tool_status": str(row.get("Status")),
                   "tool_time": float(row.get("Total Time", float("nan"))),
                   "tool_rps": float(row.get("RPS", float("nan")))}
            if isinstance(repair_src, str) and repair_src.strip():
                r = run_tests(repair_src, pj["entry"], pj["tests"])
                rec["passes_our_tests"] = r.all_pass
                rec["our_rps"] = rps(buggy, repair_src)
                rec["repaired"] = bool(r.all_pass and rec["our_rps"] <= MAX_RPS)
            else:
                rec["passes_our_tests"] = False
                rec["our_rps"] = None
                rec["repaired"] = False
            per[ours] = rec
        # eval-split submissions the tool produced no row for count as failures
        for ours in mapping:
            per.setdefault(ours, {"tool_status": "missing", "repaired": False,
                                  "passes_our_tests": False, "our_rps": None,
                                  "tool_time": None, "tool_rps": None})
        n_ok = sum(1 for v in per.values() if v["repaired"])
        rps_ok = [v["our_rps"] for v in per.values() if v["repaired"]]
        results[pid] = {"n": len(per), "repaired": n_ok,
                        "mean_rps": sum(rps_ok) / len(rps_ok) if rps_ok else None,
                        "mean_time": sum(v["tool_time"] for v in per.values()
                                         if v["tool_time"] is not None) / max(
                            1, sum(1 for v in per.values() if v["tool_time"] is not None)),
                        "per_submission": per}
        print(f"{pid}: {n_ok}/{len(per)} repaired (our harness, rps<={MAX_RPS})")
    outp = ROOT / "runs" / "refactory_tool" / "results.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(results, indent=2))
    tot = sum(r["repaired"] for r in results.values())
    n = sum(r["n"] for r in results.values())
    print(f"TOTAL {tot}/{n}  -> {outp}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]))
    elif cmd == "collect":
        collect(pathlib.Path(sys.argv[2]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
