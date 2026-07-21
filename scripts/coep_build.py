#!/usr/bin/env python3
"""Orchestrate COEP per-problem repairer synthesis and evaluation.

Subcommands:
  prompt <pid>     Write the next builder prompt (round 1 = initial synthesis,
                   later rounds = refinement with build-set feedback) to
                   runs/coep/prompts/<pid>_round<k>.md
  install <pid>    Extract the module from runs/coep/responses/<pid>_round<k>.md,
                   save as benchmark/problems/<pid>/repairer.py, evaluate it on
                   the BUILD split, and record the outcome.
  evalfinal <pid>  Evaluate the installed repairer on the held-out EVAL split;
                   write runs/coep/results/<pid>.json.

The evaluation harness re-validates every patch independently (subprocess test
run + RPS cap), so a repairer cannot self-report success.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep.evaluate import rps  # noqa: E402
from coep.llmio import extract_python_block  # noqa: E402
from coep.prompts import builder_prompt, builder_refine_prompt  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
RUNS = ROOT / "runs" / "coep"
MAX_RPS = 0.35
REPAIRER_TIMEOUT = 60


def load_problem(pid):
    return json.loads((PROBLEMS / pid / "problem.json").read_text())


def splits():
    return json.loads((ROOT / "benchmark" / "splits.json").read_text())


def rounds_done(pid) -> int:
    return len(list((RUNS / "responses").glob(f"{pid}_round*.md")))


def apply_repairer(pid: str, bug: str) -> dict:
    """Run repairer in a subprocess, then independently validate the patch."""
    p = load_problem(pid)
    buggy = (PROBLEMS / pid / "buggy" / bug).read_text()
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_repairer_one.py"), pid, bug],
            capture_output=True, text=True, timeout=REPAIRER_TIMEOUT)
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return {"bug": bug, "repaired": False, "status": "repairer_timeout"}
    except (json.JSONDecodeError, IndexError):
        return {"bug": bug, "repaired": False, "status": "repairer_crash",
                "detail": proc.stderr[-300:]}
    if out.get("error"):
        return {"bug": bug, "repaired": False, "status": "repairer_error",
                "detail": out["error"], "seconds": out.get("seconds")}
    patched = out.get("patched")
    if not patched:
        return {"bug": bug, "repaired": False, "status": "no_patch",
                "seconds": out.get("seconds")}
    val = run_tests(patched, p["entry"], p["tests"])
    patch_rps = rps(buggy, patched)
    if not val.all_pass:
        return {"bug": bug, "repaired": False, "status": "patch_fails_tests",
                "detail": f"{val.passed}/{val.total}", "seconds": out.get("seconds")}
    if patch_rps > MAX_RPS:
        return {"bug": bug, "repaired": False, "status": "patch_too_large",
                "detail": f"rps={patch_rps:.3f}", "seconds": out.get("seconds")}
    return {"bug": bug, "repaired": True, "status": "ok",
            "rps": round(patch_rps, 4), "seconds": out.get("seconds")}


def cmd_prompt(pid):
    (RUNS / "prompts").mkdir(parents=True, exist_ok=True)
    (RUNS / "responses").mkdir(parents=True, exist_ok=True)
    k = rounds_done(pid) + 1
    p = load_problem(pid)
    if k == 1:
        build = [{"id": n, "source": (PROBLEMS / pid / "buggy" / n).read_text()}
                 for n in splits()[pid]["build"]]
        refs = [f.read_text() for f in sorted((PROBLEMS / pid / "refs").glob("*.py"))]
        text = builder_prompt(p, build, refs)
    else:
        prev = (PROBLEMS / pid / "repairer.py").read_text()
        results = json.loads((RUNS / "build_eval" / f"{pid}_round{k-1}.json").read_text())
        fb = [{"id": r["bug"], "status": "REPAIRED" if r["repaired"] else "NOT REPAIRED",
               "detail": r.get("detail", r["status"] if not r["repaired"] else ""),
               "source": (PROBLEMS / pid / "buggy" / r["bug"]).read_text()}
              for r in results]
        text = builder_refine_prompt(p, prev, fb)
    path = RUNS / "prompts" / f"{pid}_round{k}.md"
    path.write_text(text)
    print(f"wrote {path}")


def cmd_install(pid):
    k = rounds_done(pid)
    resp = (RUNS / "responses" / f"{pid}_round{k}.md").read_text()
    module = extract_python_block(resp)
    if module is None:
        print("ERROR: no python block in response"); sys.exit(1)
    (PROBLEMS / pid / "repairer.py").write_text(module)
    results = [apply_repairer(pid, b) for b in splits()[pid]["build"]]
    (RUNS / "build_eval").mkdir(parents=True, exist_ok=True)
    (RUNS / "build_eval" / f"{pid}_round{k}.json").write_text(json.dumps(results, indent=2))
    ok = sum(r["repaired"] for r in results)
    print(f"{pid} round {k}: build-set repairs {ok}/{len(results)}")
    for r in results:
        print(f"  {r['bug']}: {r['status']}" + (f" ({r.get('detail')})" if r.get("detail") else ""))


def cmd_evalfinal(pid):
    results = [apply_repairer(pid, b) for b in splits()[pid]["eval"]]
    (RUNS / "results").mkdir(parents=True, exist_ok=True)
    (RUNS / "results" / f"{pid}.json").write_text(json.dumps(results, indent=2))
    ok = sum(r["repaired"] for r in results)
    print(f"{pid}: eval repairs {ok}/{len(results)}")


if __name__ == "__main__":
    {"prompt": cmd_prompt, "install": cmd_install, "evalfinal": cmd_evalfinal}[sys.argv[1]](sys.argv[2])
