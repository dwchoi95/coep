#!/usr/bin/env python3
"""Enforcement-parity arm: give the per-submission frontier baseline the SAME
size validator CoEP has, as a retry loop (PyDex-style iterative repair).

For every baseline response that passes tests but busts the RPS cap (the
baseline's only quality-failure mode on this corpus), generate ONE retry
prompt containing the original task, the oversized patch, and explicit
minimality feedback. The arm's final patch is the retry if it passes tests
within the cap, else the original. Cost = baseline + retry calls.

  gen      write runs/baseline_retry/prompts/K.md + batches
  collect  evaluate responses; print arm-level quality RR and cost
"""
import json
import pathlib
import sys

V1 = pathlib.Path(__file__).resolve().parent      # v1 package (coep/)
ROOT = V1.parents[2] / "results" / "v1"            # v1 data archive
sys.path.insert(0, str(V1))
from coep import tokens
from coep.costmodel import PRICE_IN_PER_MTOK, PRICE_OUT_PER_MTOK
from coep.evaluate import rps
from coep.llmio import extract_python_block
from coep.sandbox import run_tests

PROBLEMS = ROOT / "benchmark" / "problems"
OUT = ROOT / "runs" / "baseline_retry"
MAX_RPS = 0.35


def targets():
    rows = json.loads((ROOT / "runs" / "baseline" / "results.json").read_text())
    return [r for r in rows if r.get("passed") and r.get("rps", 0) > MAX_RPS]


def gen():
    (OUT / "prompts").mkdir(parents=True, exist_ok=True)
    (OUT / "responses").mkdir(parents=True, exist_ok=True)
    keys = []
    for r in targets():
        key = r["key"]
        orig_prompt = (ROOT / "runs" / "baseline" / "prompts" / f"{key}.md").read_text()
        prev_resp = (ROOT / "runs" / "baseline" / "responses" / f"{key}.md").read_text()
        prev_patch = extract_python_block(prev_resp)
        text = f"""{orig_prompt}

## Previous attempt (REJECTED: rewrites too much)
Your previous repair passes the tests but changes {r['rps']:.0%} of the program's tokens, exceeding the 35% relative-patch-size limit. It discards the student's own approach:
```python
{prev_patch}
```

## Retry task
Produce a NEW repair of the original buggy submission above that passes every test while changing as little of the student's code as possible (well under 35% of tokens). Preserve the student's identifiers, structure, and approach exactly wherever they are not wrong.
Output ONLY the complete corrected program in a single ```python code block, nothing else.
"""
        (OUT / "prompts" / f"{key}.md").write_text(text)
        keys.append(key)
    for b in range(0, len(keys), 10):
        (OUT / f"batch_{b // 10:02d}.txt").write_text("\n".join(keys[b:b + 10]) + "\n")
    print(f"wrote {len(keys)} retry prompts, {(len(keys)+9)//10} batches")


def collect():
    base_rows = json.loads((ROOT / "runs" / "baseline" / "results.json").read_text())
    base_by_key = {r["key"]: r for r in base_rows}
    price_base = sum(r["prompt_tokens"] * PRICE_IN_PER_MTOK
                     + r.get("response_tokens", 0) * PRICE_OUT_PER_MTOK
                     for r in base_rows) / 1e6
    fixed_keys = {r["key"] for r in base_rows
                  if r.get("passed") and r.get("rps", 1) <= MAX_RPS}
    retry_usd = 0.0
    results = []
    for r in targets():
        key, pid = r["key"], r["pid"]
        p = json.loads((PROBLEMS / pid / "problem.json").read_text())
        prompt = (OUT / "prompts" / f"{key}.md").read_text()
        resp_path = OUT / "responses" / f"{key}.md"
        rec = {"key": key, "pid": pid, "orig_rps": r["rps"]}
        if not resp_path.exists():
            rec["status"] = "missing"
            results.append(rec)
            continue
        resp = resp_path.read_text()
        retry_usd += (tokens.count(prompt) * PRICE_IN_PER_MTOK
                      + tokens.count(resp) * PRICE_OUT_PER_MTOK) / 1e6
        patch = extract_python_block(resp)
        if patch is None:
            rec["status"] = "no_code_block"
        else:
            buggy = (PROBLEMS / pid / "buggy" / base_by_key[key]["bug"]).read_text()
            v = run_tests(patch, p["entry"], p["tests"])
            rec["retry_rps"] = round(rps(buggy, patch), 4)
            rec["passed"] = v.all_pass
            ok = v.all_pass and rec["retry_rps"] <= MAX_RPS
            rec["status"] = "ok" if ok else "still_failing"
            if ok:
                fixed_keys.add(key)
        results.append(rec)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    n = len(base_rows)
    usd = price_base + retry_usd
    print(f"retry arm: {sum(1 for r in results if r['status']=='ok')}/{len(results)} "
          f"retries recovered; arm quality RR {len(fixed_keys)}/{n} = {len(fixed_keys)/n:.3f}; "
          f"usd/inst {usd/n*1000:.3f}e-3 (base {price_base/n*1000:.3f} + retry {retry_usd/n*1000:.3f})")


if __name__ == "__main__":
    {"gen": gen, "collect": collect}[sys.argv[1]]()
