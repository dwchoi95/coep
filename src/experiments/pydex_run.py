"""`run.py pydex` — the PyDex baseline (paper-faithful semantic phase) over one
problem, stored in the unified CSV format:

    results/<ver>/<p_id>/pydex.csv      one row per truly-buggy submission
    results/<ver>/<p_id>/pydex_pc.csv   the same run re-priced under provider
                                        prompt caching (PyDex_PC)
    results/<ver>/<p_id>/summary.csv    upserted rows for both approaches

Per submission: one Fig.6 zero-shot prompt (Fig.7 few-shot automatically when a
pairs.json bank exists) -> K sampled candidates -> full-suite oracle -> the
min-token-edit-distance survivor. ALL K calls are billed and timed, including
oracle-rejected candidates. ATT_api is the summed call latency; ATT_cpu is the
remaining wall time (candidate executions, retrieval, selection).

PyDex_PC is a documented-rules UPPER BOUND on what provider caching could
deliver for these exact queries (empirically, haiku-4-5 refuses prompts below
its 4,096-token minimum and gpt-5.4-nano's automatic caching did not engage at
all in our probes): cross-submission reuse is impossible (the buggy-first
layout shares a ~13-token leading prefix), so the only cacheable structure is
the K identical prompts *within* one submission — modeled as first call full
price, the remaining K-1 prompts read at 0.1x (write 1.25x on Anthropic, free
on pre-5.6 OpenAI), gated on each provider's cacheable minimum (4,096 tokens
for claude-haiku-4-5; 1,024 for gpt-5.4-nano). The PyDex arm itself is billed
from raw token counts at full rates, so no incidental provider cache hit can
leak a discount into the uncached baseline.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from baselines.pydex.pydex import (K_DEFAULT, ShotBank, repair,
                                   zero_shot_prompt)
from src.experiments._common import load_env, load_problem
from src.experiments.results_io import (event_row, summarize_events,
                                        upsert_summary, write_events)
from src.runner.testing import run_tests
from src.utils.metrics import PRICES, count_tokens, rps

MODEL_LABEL = {"claude-sonnet": "claude-sonnet-5", "gpt-mini": "gpt-5.4-mini",
               "claude-haiku": "claude-haiku-4-5", "gpt-nano": "gpt-5.4-nano"}
CACHE_MIN = {"claude-sonnet": 1024, "gpt-mini": 1024,   # provider cacheable minimums
             "claude-haiku": 4096, "gpt-nano": 1024}
CACHE_READ = 0.1
CACHE_WRITE = {"claude-sonnet": 1.25, "claude-haiku": 1.25,
               "gpt-mini": 0.0, "gpt-nano": 0.0}        # gpt-5.4 family: writes free


def _shared_prefix_tokens(problem: dict) -> int:
    """Tokens of the longest submission-independent LEADING segment."""
    a = zero_shot_prompt("PROBE_A", problem)
    b = zero_shot_prompt("PROBE_B", problem)
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return count_tokens(a[:i])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py pydex")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-sonnet")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k", type=int, default=K_DEFAULT,
                    help="candidates per prompt (paper: 10)")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--ver", default="v2")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    data_dir = Path(args.data_root) / args.problem
    files = sorted((data_dir / "buggy").glob("*.py"))
    if args.limit:
        files = files[:args.limit]
    model_label = MODEL_LABEL.get(args.model, args.model)

    bank = ShotBank(prob, data_dir)
    mode = "few-shot" if bank.entries else "zero-shot"
    pin, pout = PRICES[args.model]
    cache_min = CACHE_MIN.get(args.model, 1024)
    w_mult = CACHE_WRITE.get(args.model, 1.25)

    rows, rows_pc = [], []
    noop = 0
    for f in files:
        src = f.read_text()
        if run_tests(src, prob).all_pass:
            noop += 1
            continue
        t0 = time.time()
        res = repair(src, prob, model=args.model, k=args.k, bank=bank)
        wall = time.time() - t0
        att_api = res.seconds
        att_cpu = max(0.0, wall - att_api)
        pr = rps(src, res.patch) if res.repaired else None
        # PyDex billed from raw tokens at full rates: structurally uncached.
        raw_usd = (res.in_tokens * pin + res.out_tokens * pout) / 1e6
        row = event_row(f.stem, model_label, "llm" if res.repaired else "none",
                        res.repaired, res.patch, pr, att_cpu=att_cpu,
                        att_api=att_api, in_tok=res.in_tokens,
                        out_tok=res.out_tokens, api_usd=raw_usd)
        rows.append(row)

        # PC upper bound: the K identical prompts within this submission —
        # first at full price (+write premium), the rest read at 0.1x.
        pc = dict(row)
        prompt_tok = res.in_tokens / max(1, res.calls)
        if res.calls > 1 and prompt_tok >= cache_min:
            reads = res.calls - 1
            discount = prompt_tok * (pin / 1e6) * (
                reads * (1 - CACHE_READ) - (w_mult - 1.0))
            pc["$API"] = round(max(0.0, raw_usd - max(0.0, discount)), 6)
        rows_pc.append(pc)

    write_events(args.ver, args.problem, "pydex", rows)
    write_events(args.ver, args.problem, "pydex_pc", rows_pc)
    upsert_summary(args.ver, args.problem,
                   summarize_events("PyDex", model_label, rows))
    upsert_summary(args.ver, args.problem,
                   summarize_events("PyDex_PC", model_label, rows_pc))

    n = len(rows)
    fixed = sum(r["Fixed"] for r in rows)
    usd = sum(r["$API"] for r in rows)
    usd_pc = sum(r["$API"] for r in rows_pc)
    print(f"=== {args.problem} PyDex/{mode} [{model_label}] K={args.k} "
          f"{n} buggy ({noop} noop excluded) ===")
    print(f"RR={100*fixed/max(1,n):.2f}%  $API={usd:.4f}  PC $API={usd_pc:.4f} "
          f"(cache minimum {cache_min} tok for {model_label})")
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0
