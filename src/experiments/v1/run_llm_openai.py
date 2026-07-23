#!/usr/bin/env python3
"""OpenAI (GPT-family) backend: run every prompt file in a directory through a
GPT model and write one response file each — the same file-level protocol used
by the Claude arms, so all downstream collection/analysis scripts work
unchanged.

Setup:
    pip install openai
    export OPENAI_API_KEY=sk-...

Examples:
    # per-submission baseline with GPT
    python3 scripts/run_llm_openai.py \
        --prompts runs/baseline/prompts --out runs/baseline_gpt/responses \
        --model gpt-4o
    python3 scripts/collect_arm.py --arm baseline_gpt --model gpt-4o

    # builder round k with GPT (then install/eval with:
    #   COEP_RUNS=coep_gpt COEP_REPAIRER=repairer_gpt.py scripts/coep_build.py ...)
    python3 scripts/run_llm_openai.py \
        --prompts runs/coep_gpt/prompts --out runs/coep_gpt/responses \
        --model gpt-4o

Notes:
- Single-shot chat completion per prompt file, no tools, temperature as given
  (default 0 for reproducibility; some reasoning models ignore/reject it, use
  --no-temperature there).
- Skips prompts that already have a response (safe to re-run / resume).
"""
import argparse
import pathlib
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install openai  (and set OPENAI_API_KEY)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--max-completion-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--no-temperature", action="store_true",
                    help="omit temperature (required for o-series/reasoning models)")
    args = ap.parse_args()

    client = OpenAI()
    prompts = sorted(pathlib.Path(args.prompts).glob("*.md"))
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    done = skipped = 0
    for p in prompts:
        target = outdir / p.name
        if target.exists():
            skipped += 1
            continue
        kwargs = dict(model=args.model,
                      max_completion_tokens=args.max_completion_tokens,
                      messages=[{"role": "user", "content": p.read_text()}])
        if not args.no_temperature:
            kwargs["temperature"] = args.temperature
        resp = client.chat.completions.create(**kwargs)
        target.write_text(resp.choices[0].message.content or "")
        done += 1
        print(f"[{done}] {p.name}")
    print(f"done: {done} new, {skipped} already present")


if __name__ == "__main__":
    main()
