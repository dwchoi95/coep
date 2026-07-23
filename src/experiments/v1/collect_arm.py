#!/usr/bin/env python3
"""Evaluate any per-submission LLM arm (responses under runs/<arm>/responses,
sharing runs/baseline/prompts) and price it by model. Generalizes
collect_baseline/collect_haiku to arbitrary arms, e.g. GPT models.

    python3 scripts/collect_arm.py --arm baseline_gpt --model gpt-4o
"""
import argparse
import json
import pathlib
import sys

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep import tokens  # noqa: E402
from coep.costmodel import MODEL_PRICES  # noqa: E402
from coep.evaluate import rps  # noqa: E402
from coep.llmio import extract_python_block  # noqa: E402
from coep.sandbox import run_tests  # noqa: E402

PROBLEMS = ROOT / "benchmark" / "problems"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="runs/<arm>/responses to evaluate")
    ap.add_argument("--model", required=True, help=f"pricing key, one of {sorted(MODEL_PRICES)}")
    args = ap.parse_args()
    price_in, price_out = MODEL_PRICES[args.model]

    out = ROOT / "runs" / args.arm
    # arms with their own prompts (e.g. pydex few-shot) are priced on those;
    # response-only arms (e.g. other models on the same prompts) fall back to baseline's
    prompts_dir = (out / "prompts") if (out / "prompts").exists() else (
        ROOT / "runs" / "baseline" / "prompts")
    manifest_path = (out / "manifest.json") if (out / "manifest.json").exists() else (
        ROOT / "runs" / "baseline" / "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    results = []
    for item in manifest:
        key, pid = item["key"], item["pid"]
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        prompt = (prompts_dir / f"{key}.md").read_text()
        rec = {"key": key, "pid": pid, "bug": item["bug"],
               "prompt_tokens": tokens.count(prompt)}
        resp_path = out / "responses" / f"{key}.md"
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
    (out / "results.json").write_text(json.dumps(results, indent=2))
    done = [r for r in results if "passed" in r]
    fixed = [r for r in done if r["passed"]]
    quality = [r for r in fixed if r.get("rps", 1) <= 0.35]
    usd = sum(r["prompt_tokens"] * price_in + r.get("response_tokens", 0) * price_out
              for r in done) / 1e6
    n = max(len(done), 1)
    print(f"{args.arm} ({args.model}): {len(done)} evaluated, "
          f"repair {len(fixed)}/{n}={len(fixed)/n:.3f}, quality {len(quality)/n:.3f}, "
          f"usd/inst {usd/n*1000:.3f}e-3")


if __name__ == "__main__":
    main()
