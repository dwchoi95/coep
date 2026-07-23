#!/usr/bin/env python3
"""Evaluate the cheap-model (Haiku-tier) baseline arm and derive the cascade
baseline (cheap model first, frontier fallback). Writes
runs/baseline_haiku/results.json."""
import json
import pathlib
import sys

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep import tokens  # noqa: E402
from coep.evaluate import rps  # noqa: E402
from coep.llmio import extract_python_block  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
BASE = ROOT / "runs" / "baseline"
OUT = ROOT / "runs" / "baseline_haiku"

# Haiku-tier pricing (Claude Haiku 4.5, July 2026): $1 / $5 per Mtok
PRICE_IN, PRICE_OUT = 1.00, 5.00


def main():
    manifest = json.loads((BASE / "manifest.json").read_text())
    frontier = {r["key"]: r for r in json.loads((BASE / "results.json").read_text())}
    results = []
    for item in manifest:
        key, pid = item["key"], item["pid"]
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        resp_path = OUT / "responses" / f"{key}.md"
        rec = {"key": key, "pid": pid, "bug": item["bug"],
               "prompt_tokens": frontier[key]["prompt_tokens"]}
        if not resp_path.exists():
            rec["status"] = "missing_response"
            results.append(rec)
            continue
        resp = resp_path.read_text()
        rec["response_tokens"] = tokens.count(resp)
        patch = extract_python_block(resp)
        buggy = (PROBLEMS / pid / "buggy" / item["bug"]).read_text()
        if patch is None:
            rec.update({"status": "no_code_block", "passed": False})
        else:
            r = run_tests(patch, p["entry"], p["tests"])
            rec["passed"] = r.all_pass
            rec["rps"] = round(rps(buggy, patch), 4)
            rec["status"] = "ok" if r.all_pass else f"fails {r.total - r.passed}/{r.total}"
        results.append(rec)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    done = [r for r in results if "passed" in r]
    fixed = [r for r in done if r["passed"]]
    q = [r for r in fixed if r.get("rps", 1) <= 0.35]
    usd_haiku = sum(r["prompt_tokens"] * PRICE_IN + r.get("response_tokens", 0) * PRICE_OUT
                    for r in done) / 1e6
    n = len(done)
    print(f"haiku arm: evaluated {n}, repair rate {len(fixed)}/{n} = {len(fixed)/n:.3f}, "
          f"quality {len(q)}/{n} = {len(q)/n:.3f}")
    print(f"haiku usd/inst: {usd_haiku/n*1000:.3f}e-3")
    # cascade: haiku first, frontier on failure
    fail = [r for r in done if not r["passed"]]
    usd_frontier_fb = sum(frontier[r["key"]]["prompt_tokens"] * 3 +
                          frontier[r["key"]].get("response_tokens", 0) * 15
                          for r in fail) / 1e6
    cascade_fixed = len(fixed) + sum(1 for r in fail if frontier[r["key"]].get("passed"))
    print(f"cascade (haiku->frontier): repair {cascade_fixed}/{n} = {cascade_fixed/n:.3f}, "
          f"usd/inst {(usd_haiku + usd_frontier_fb)/n*1000:.3f}e-3, "
          f"escalation rate {len(fail)/n:.3f}")


if __name__ == "__main__":
    main()
