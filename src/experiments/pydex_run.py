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

PyDex_PC: provider caching bills a *leading* shared prefix — but the paper's
prompt layout places the buggy program first, so the only shared leading text
is the section header, far below the 1,024-token cache minimum. PyDex_PC is
therefore computed honestly (longest shared prefix, threshold applied) and, on
this layout, degenerates to PyDex — which is itself a finding.
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

MODEL_LABEL = {"claude-haiku": "claude-haiku-4-5", "gpt-nano": "gpt-5.4-nano"}
CACHE_MIN_TOKENS = 1024
CACHE_READ, CACHE_WRITE = 0.1, 1.25


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
    ap.add_argument("--model", default="claude-haiku")
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
    in_rate = PRICES[args.model][0] / 1e6

    bank = ShotBank(prob, data_dir)
    mode = "few-shot" if bank.entries else "zero-shot"
    prefix = _shared_prefix_tokens(prob)
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
        res = repair(src, prob, model=args.model, k=args.k, bank=bank)
        wall = time.time() - t0
        att_api = res.seconds
        att_cpu = max(0.0, wall - att_api)
        pr = rps(src, res.patch) if res.repaired else None
        row = event_row(f.stem, model_label, "llm" if res.repaired else "none",
                        res.repaired, res.patch, pr, att_cpu=att_cpu,
                        att_api=att_api, in_tok=res.in_tokens,
                        out_tok=res.out_tokens, api_usd=res.usd)
        rows.append(row)

        pc = dict(row)
        if cacheable and res.calls:
            writes = 0 if first_call_done else 1
            reads = res.calls - writes
            discount = prefix * in_rate * (
                (writes + reads) - (writes * CACHE_WRITE + reads * CACHE_READ))
            pc["$API"] = round(max(0.0, res.usd - discount), 6)
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
    print(f"=== {args.problem} PyDex/{mode} [{model_label}] K={args.k} "
          f"{n} buggy ({noop} noop excluded) ===")
    print(f"RR={100*fixed/max(1,n):.2f}%  $API={usd:.4f}  PC $API={usd_pc:.4f} "
          f"(leading shared prefix={prefix} tok, "
          f"{'cacheable' if cacheable else 'below 1024-token minimum -> PC = PyDex'})")
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0
