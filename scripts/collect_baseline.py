#!/usr/bin/env python3
"""Evaluate baseline LLM responses: extract patch, run tests, compute RPS and
token usage. Writes runs/baseline/results.json."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from coep import tokens  # noqa: E402
from coep.evaluate import rps  # noqa: E402
from coep.llmio import extract_python_block  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"
OUT = ROOT / "runs" / "baseline"


def main():
    manifest = json.loads((OUT / "manifest.json").read_text())
    results = []
    missing = 0
    for item in manifest:
        key, pid = item["key"], item["pid"]
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        prompt_path = OUT / "prompts" / f"{key}.md"
        resp_path = OUT / "responses" / f"{key}.md"
        rec = {"key": key, "pid": pid, "bug": item["bug"],
               "prompt_tokens": tokens.count(prompt_path.read_text())}
        if not resp_path.exists():
            missing += 1
            rec.update({"status": "missing_response"})
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
    print(f"responses evaluated: {len(done)} (missing {missing})")
    if done:
        print(f"repair rate: {len(fixed)}/{len(done)} = {len(fixed)/len(done):.3f}")
        q = [r for r in fixed if r.get("rps", 1) <= 0.35]
        print(f"quality (rps<=0.35) repair rate: {len(q)}/{len(done)} = {len(q)/len(done):.3f}")


if __name__ == "__main__":
    main()
