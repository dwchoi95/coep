"""`run.py pydex` — the per-submission PyDex baseline over one problem, stored
in the agreed unified format:

    results/<ver>/<p_id>/pydex.csv      one row per truly-buggy submission
    results/<ver>/<p_id>/pydex_pc.csv   the same run re-priced under provider
                                        prompt caching (PyDex_PC)
    results/<ver>/<p_id>/summary.csv    upserted rows for both approaches

PyDex_PC repricing: the prompt's shared prefix (description + tests +
instructions — everything except the buggy program and its execution feedback)
is billed once at the 1.25x cache-write rate for the problem's first call and
at the 0.1x cache-read rate for every later call; the remainder and all output
tokens are billed normally. Providers only cache prefixes of >= 1024 tokens,
so below that PyDex_PC degenerates to PyDex (the honest outcome). Latency and
token counts are identical to the PyDex run — only dollars change.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from baselines.pydex.pydex import _render, repair
from src.experiments._common import load_env, load_problem
from src.experiments.results_io import (event_row, summarize_events,
                                        upsert_summary, write_events)
from src.runner.testing import run_tests
from src.utils.metrics import PRICES, count_tokens, rps

MODEL_LABEL = {"claude-haiku": "claude-haiku-4-5", "gpt-nano": "gpt-5.4-nano"}
CACHE_MIN_TOKENS = 1024
CACHE_READ, CACHE_WRITE = 0.1, 1.25


def _prefix_tokens(problem: dict) -> int:
    """Tokens of the prompt's shared prefix (empty dynamic fields)."""
    from baselines.pydex.pydex import _tests_block
    static = _render(description=problem.get("description", ""),
                     tests=_tests_block(problem), buggy="", feedback="")
    return count_tokens(static)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py pydex")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-haiku")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--ver", default="v2")
    args = ap.parse_args(argv)
    load_env()

    prob = load_problem(args.problem, args.data_root)
    files = sorted((Path(args.data_root) / args.problem / "buggy").glob("*.py"))
    if args.limit:
        files = files[:args.limit]
    model_label = MODEL_LABEL.get(args.model, args.model)
    in_rate = PRICES[args.model][0] / 1e6

    prefix = _prefix_tokens(prob)
    cacheable = prefix >= CACHE_MIN_TOKENS
    first_call_done = False

    rows, rows_pc = [], []
    noop = 0
    for f in files:
        src = f.read_text()
        if run_tests(src, prob).all_pass:
            noop += 1
            continue
        t0 = time.time()
        res = repair(src, prob, model=args.model, rounds=args.rounds, samples=1)
        wall = time.time() - t0
        att_api = res.seconds
        att_cpu = max(0.0, wall - att_api)     # candidate test-runs, selection
        pr = rps(src, res.patch) if res.repaired else None
        row = event_row(f.stem, model_label, "llm" if res.repaired else "none",
                        res.repaired, res.patch, pr, att_cpu=att_cpu,
                        att_api=att_api, in_tok=res.in_tokens,
                        out_tok=res.out_tokens, api_usd=res.usd)
        rows.append(row)

        # PyDex_PC: same call trace, prefix re-priced under provider caching
        pc = dict(row)
        if cacheable and res.calls:
            writes = 0 if first_call_done else 1
            reads = res.calls - writes
            full = res.usd
            discount = prefix * in_rate * (
                (writes * 1.0 + reads * 1.0)            # what was charged
                - (writes * CACHE_WRITE + reads * CACHE_READ))
            pc["$API"] = round(max(0.0, full - discount), 6)
            first_call_done = True
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
    print(f"=== {args.problem} PyDex [{model_label}] {n} buggy "
          f"({noop} noop excluded) ===")
    print(f"RR={100*fixed/max(1,n):.2f}%  $API={usd:.4f}  "
          f"PC $API={usd_pc:.4f} (prefix={prefix} tok, "
          f"{'cacheable' if cacheable else 'below 1024-token cache minimum'})")
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0
