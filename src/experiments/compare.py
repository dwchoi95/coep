"""`run.py compare` — one pass over a problem's submission stream, three
CoEP variants recorded simultaneously into the agreed CSV format:

    results/<ver>/<p_id>/coep_l.csv      CoEP_L    (frozen local tool only)
    results/<ver>/<p_id>/coep_lf.csv     CoEP_LF   (+ LLM fallback)
    results/<ver>/<p_id>/coep_lfsl.csv   CoEP_LFSL (+ self-learning absorption)
    results/<ver>/<p_id>/summary.csv     upserted rows (Approach, Model)

Single-pass derivation (no duplicated LLM calls): every submission first runs
the frozen local tool — that is CoEP_L's outcome and the other arms' whenever
it repairs (Source ``rules``/``reference``). Only on a frozen miss do we (a)
retry with the evolving tool if self-learning has added rules (Source
``sl_rules``), (b) make the one fallback call CoEP_LF needs anyway (Source
``llm``; shared with LFSL's accounting unless (a) repaired), and (c) absorb a
successful fallback fix into the LFSL tool (validate-or-rollback; its Rules_SL
cell names the rule; priced to LFSL alone).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

from src.core.fallback import absorb, fallback_repair
from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.core.synthesis import load_fixer
from src.experiments._common import load_env, load_problem, tool_path
from src.experiments.results_io import (event_row, summarize_events,
                                        upsert_summary, write_events)
from src.utils.metrics import rps

MODEL_LABEL = {"claude-sonnet": "claude-sonnet-5", "gpt-mini": "gpt-5.4-mini",
               "claude-haiku": "claude-haiku-4-5", "gpt-nano": "gpt-5.4-nano"}
# Generated fixers construct rules either positionally (``Rule('name', ...)``)
# or by keyword, often across lines (``Rule(\n    name="name", ...)``).
_RULE_NAME = re.compile(r"Rule\(\s*(?:name\s*=\s*)?['\"]([^'\"]+)['\"]")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py compare")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-sonnet")
    ap.add_argument("--limit", type=int, default=0, help="0 = all buggy programs")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip fallback/absorption (CoEP_L only; no API key)")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--ver", default="v2")
    args = ap.parse_args(argv)
    if not args.no_llm:
        load_env()

    prob = load_problem(args.problem, args.data_root)
    files = sorted((Path(args.data_root) / args.problem / "buggy").glob("*.py"))
    if args.limit:
        files = files[:args.limit]
    correct = [f.read_text() for f in
               sorted((Path(args.data_root) / args.problem / "correct").glob("*.py"))]

    frozen_path = tool_path(args.problem, args.model)
    frozen_rules = load_fixer(frozen_path)
    # LFSL evolves a *copy* of the tool so the frozen artifact stays pristine.
    sl_dir = Path(tempfile.mkdtemp(prefix=f"sl_{args.problem}_"))
    shutil.copy(frozen_path, sl_dir / "fixer.py")
    sl_path = sl_dir / "fixer.py"
    n_frozen_rules = len(frozen_rules)

    cost_file = frozen_path.parent / "cost.json"
    build = json.loads(cost_file.read_text()) if cost_file.exists() else {}
    att_build = float(build.get("build_seconds") or 0.0)
    build_usd = float(build.get("usd") or 0.0)
    rules_build = [r.name for r in frozen_rules
                   if not r.name.startswith("generic_")]

    index = ReferenceIndex(correct)
    budget = SearchBudget(max_candidates=150, max_combo=2, candidate_timeout=3)
    model_label = MODEL_LABEL.get(args.model, args.model)

    rows_l: list[dict] = []
    rows_lf: list[dict] = []
    rows_sl: list[dict] = []
    learned_names: list[str] = []
    noop = 0

    for f in files:
        src = f.read_text()
        stem = f.stem
        t0 = time.time()
        fz = local_repair(src, prob, frozen_rules, index, budget)
        t_frozen = time.time() - t0
        if fz.source == "noop":
            noop += 1
            continue

        if fz.repaired:                        # all three arms share this hit
            pr = rps(src, fz.patch)
            row = event_row(stem, model_label, fz.source, True, fz.patch, pr,
                            att_cpu=t_frozen, rules_l=fz.rules)
            rows_l.append(row)
            rows_lf.append(dict(row))
            rows_sl.append(dict(row))
            continue

        rows_l.append(event_row(stem, model_label, "none", False,
                                att_cpu=t_frozen))

        # LFSL-only retry with the evolving tool (only if rules were learned)
        sl_hit, sl_cpu, sl_pr, sl_patch, sl_chain = False, 0.0, 0.0, None, []
        sl_rules = load_fixer(sl_path)
        if len(sl_rules) > n_frozen_rules:
            t1 = time.time()
            evolved = local_repair(src, prob, sl_rules, index, budget)
            sl_cpu = time.time() - t1
            if evolved.repaired:
                sl_hit, sl_pr = True, rps(src, evolved.patch)
                sl_patch, sl_chain = evolved.patch, list(evolved.rules)

        if args.no_llm:                        # CoEP_L-only mode (dry runs)
            rows_lf.append(event_row(stem, model_label, "none", False,
                                     att_cpu=t_frozen))
            rows_sl.append(event_row(stem, model_label,
                                     "sl_rules" if sl_hit else "none", sl_hit,
                                     sl_patch, sl_pr,
                                     att_cpu=t_frozen + sl_cpu,
                                     rules_l=sl_chain))
            continue

        # the one fallback call CoEP_LF needs regardless
        fb = fallback_repair(src, prob, correct, model=args.model)
        fb_pr = rps(src, fb.patch) if fb.repaired else None
        rows_lf.append(event_row(stem, model_label,
                                 "llm" if fb.repaired else "none", fb.repaired,
                                 fb.patch, fb_pr, att_cpu=t_frozen,
                                 att_api=fb.seconds, in_tok=fb.in_tokens,
                                 out_tok=fb.out_tokens, api_usd=fb.usd))

        if sl_hit:                             # LFSL repaired locally: no call billed
            rows_sl.append(event_row(stem, model_label, "sl_rules", True,
                                     sl_patch, sl_pr,
                                     att_cpu=t_frozen + sl_cpu,
                                     rules_l=sl_chain))
        else:                                  # LFSL shares the fallback call
            t_ab = ab_in = ab_out = 0; ab_usd = 0.0
            new_rule = []
            if fb.repaired:                    # ...and absorbs the fix
                ab = absorb(sl_path, src, fb.patch, prob,
                            model=args.model, budget=budget)
                t_ab, ab_in, ab_out, ab_usd = (ab.seconds, ab.in_tokens,
                                               ab.out_tokens, ab.usd)
                if ab.absorbed and ab.rule_added:
                    m = _RULE_NAME.search(ab.rule_added)
                    name = m.group(1) if m else f"learned_{len(learned_names)}"
                    learned_names.append(name)
                    new_rule = [name]
            rows_sl.append(event_row(stem, model_label,
                                     "llm" if fb.repaired else "none",
                                     fb.repaired, fb.patch, fb_pr,
                                     att_cpu=t_frozen + sl_cpu,
                                     att_api=fb.seconds + t_ab,
                                     in_tok=fb.in_tokens + ab_in,
                                     out_tok=fb.out_tokens + ab_out,
                                     api_usd=fb.usd + ab_usd,
                                     rules_sl=new_rule))

    write_events(args.ver, args.problem, "coep_l", rows_l)
    write_events(args.ver, args.problem, "coep_lf", rows_lf)
    write_events(args.ver, args.problem, "coep_lfsl", rows_sl)
    for approach, rows, adds in (("CoEP_L", rows_l, []),
                                 ("CoEP_LF", rows_lf, []),
                                 ("CoEP_LFSL", rows_sl, learned_names)):
        upsert_summary(args.ver, args.problem,
                       summarize_events(approach, model_label, rows,
                                        att_build=att_build,
                                        build_usd=build_usd,
                                        rules_build=rules_build,
                                        rules_add=adds))

    def rr(rows):
        return 100 * sum(r["Fixed"] for r in rows) / max(1, len(rows))

    print(f"=== {args.problem} [{model_label}] {len(files)} programs "
          f"({noop} noop excluded) ===")
    print(f"ATT_build={att_build}s  $Build={build_usd}  "
          f"rules learned: {len(learned_names)}")
    for name, rows in (("CoEP_L", rows_l), ("CoEP_LF", rows_lf),
                       ("CoEP_LFSL", rows_sl)):
        print(f"  {name:10s} RR={rr(rows):6.2f}%  n={len(rows)}")
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0
