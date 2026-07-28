"""`run.py compare` — one deterministic pass over a problem's submission stream.

    results/<ver>/<p_id>/coep_l.csv      CoEP_L     (frozen local tool only)
    results/<ver>/<p_id>/coep_lf.csv     CoEP_LF    (+ LLM fallback)
    results/<ver>/<p_id>/coep_l_sl.csv   CoEP_L+SL  (--with-learned; separate run)
    results/<ver>/<p_id>/coep_l_fw.csv   CoEP_L_fw  (--framework-only ablation)
    results/<ver>/<p_id>/summary.csv     upserted rows (Approach, Model)

Single-pass derivation (no duplicated LLM calls): every submission runs the
frozen local tool, which is CoEP_L's outcome unconditionally -- it takes any
patch that passes the tests, which is the same acceptance rule the classical
symbolic baseline uses, so the two stay comparable.

CoEP_LF spends its one call in two places: on a miss, and on a patch at least
as large as the program it repairs (``rps > RPS_GATE``). Local repair's only
acceptance test is the instructor's suite, so transplant can return a patch
larger than the student's whole program; the gate is where the hybrid decides
that is worth a call. The smaller of the two patches is kept, so escalating can
cost money but never coverage or patch size.

The threshold is a constant rather than a calibrated quantity, and that is a
measured choice. Over 38 candidate rules -- median- or mean-anchored with MAD,
standard-deviation or interquartile spread, bare quantiles, multiples of the
assignment's median, corpus-wide variants, and constants -- repair rate is
identical to four decimals and mean RPS falls monotonically with the escalation
rate, so no setting is best and the choice is a budget. Making the threshold
relative to the assignment measurably does not pay: RPS is already normalized
by program size, and normalizing again per assignment sends calls to the
assignments the tool already handles well.

Self-learning does not run inside this pass. A successful fallback fix is still
generalized into a rule, but into a staging copy of the tool that this pass
never consults, so no submission's outcome depends on which submissions
preceded it and both arms are reproducible from the frozen artifact alone. The
accumulated rules are persisted beside the tool as a separate artifact
(``tools/<pid>/<model>/sl/``) and evaluated by a second frozen run,
``--with-learned``, reported as CoEP_L+SL. The absorption calls are priced to
that artifact rather than to CoEP_LF, which does not benefit from them.

The submission a rule was induced from is named in its CoEP_LF row's Rules_SL
cell, so the handful of submissions that fed the learned rules can be excluded
from -- or reported alongside -- the CoEP_L+SL numbers.
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
from src.experiments.results_io import (event_row, read_events,
                                        summarize_events, upsert_summary,
                                        write_events)
from src.utils.metrics import rps

# A patch at least as large as the program it repairs is a rewrite, not a
# repair, under any assignment's standards. This is the whole gate.
RPS_GATE = 1.0

# Generated fixers construct rules either positionally (``Rule('name', ...)``)
# or by keyword, often across lines (``Rule(\n    name="name", ...)``).
_RULE_NAME = re.compile(r"Rule\(\s*(?:name\s*=\s*)?['\"]([^'\"]+)['\"]")


def learned_path(problem: str, model: str, root: str = "tools") -> Path:
    """Where the self-learned augmentation of a tool lives.

    A sibling directory rather than a ``learned.py`` next to the tool itself:
    ``load_fixer`` picks up any sibling ``learned.py`` automatically, so
    storing it in place would silently fold the learned rules into CoEP_L and
    destroy the frozen-tool baseline.
    """
    return tool_path(problem, model, root).parent / "sl" / "fixer.py"


def _load_files(args, model_label: str = "") -> list[Path]:
    files = sorted((Path(args.data_root) / args.problem / "buggy").glob("*.py"))
    if args.subset:
        keep = set(json.loads(Path(args.subset).read_text())
                   ["problems"].get(args.problem, []))
        files = [f for f in files if f.stem in keep]
    if getattr(args, "only_missing", False):
        # Widening the pool should not re-run the submissions already measured:
        # the escalation tail on those was paid for once already, and buying it
        # again would both cost money and perturb a recorded result.
        done = {str(r["Buggy"]) for r in
                read_events(args.ver, args.problem, "coep_l", model_label)}
        before = len(files)
        files = [f for f in files if f.stem not in done]
        print(f"{args.problem} [{model_label}]: {before - len(files)} already "
              f"measured, {len(files)} to run")
    if args.limit:
        files = files[:args.limit]
    return files


def _already_learned(stage_fixer: Path, n_base: int, src: str, prob: dict,
                     index: ReferenceIndex, budget: SearchBudget) -> bool:
    """Would the rules learned so far already repair this submission?

    Inducing a second rule for a bug an earlier one already covers bloats the
    artifact and pays for a call that adds nothing. The check runs the staged
    tool locally, so it costs no API and its outcome is never recorded --
    CoEP_L and CoEP_LF are unaffected either way.
    """
    staged = load_fixer(stage_fixer)
    if len(staged) <= n_base:
        return False
    return local_repair(src, prob, staged, index, budget).repaired


def _build_cost(path: Path) -> tuple[float, float]:
    f = path.parent / "cost.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    return float(d.get("build_seconds") or 0.0), float(d.get("usd") or 0.0)


def run_with_learned(args, prob: dict, files: list[Path],
                     correct: list[str], model_label: str) -> int:
    """Frozen evaluation of the tool augmented with its self-learned rules."""
    path = learned_path(args.problem, args.model, args.tools_root)
    if not path.exists():
        print(f"{args.problem}: no learned rules at {path.parent}; "
              f"run `compare` first so self-learning can accumulate some")
        return 1
    rules = load_fixer(path)                      # picks up sibling learned.py
    base = load_fixer(tool_path(args.problem, args.model, args.tools_root))
    att_build, build_usd = _build_cost(path)
    index = ReferenceIndex(correct)
    budget = SearchBudget()

    rows = []
    for f in files:
        src = f.read_text()
        t0 = time.time()
        res = local_repair(src, prob, rules, index, budget)
        dt = time.time() - t0
        rows.append(event_row(f.stem, model_label,
                              res.source if res.repaired else "none",
                              res.repaired, res.patch,
                              rps(src, res.patch) if res.repaired else None,
                              att_cpu=dt, rules_l=res.rules))

    write_events(args.ver, args.problem, "coep_l_sl", rows)
    upsert_summary(args.ver, args.problem,
                   summarize_events("CoEP_L+SL", model_label, rows,
                                    att_build=att_build, build_usd=build_usd,
                                    rules_build=[r.name for r in rules
                                                 if not r.name.startswith("generic_")]))
    rr = 100 * sum(r["Fixed"] for r in rows) / max(1, len(rows))
    print(f"=== {args.problem} [{model_label}] CoEP_L+SL "
          f"{len(files)} programs ===")
    print(f"  base rules {len(base)} -> augmented {len(rules)} "
          f"(+{len(rules) - len(base)})")
    print(f"  CoEP_L+SL  RR={rr:6.2f}%  n={len(rows)}")
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py compare")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=0, help="0 = all buggy programs")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip fallback/absorption (CoEP_L only; no API key)")
    ap.add_argument("--framework-only", action="store_true",
                    help="drop the LLM-authored rules and keep the generic "
                         "library and the transplant, to isolate what the "
                         "build buys; writes to <approach>_fw.csv")
    ap.add_argument("--with-learned", action="store_true",
                    help="evaluate the frozen self-learned tool (CoEP_L+SL) "
                         "instead of running the main pass")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--tools-root", default="tools",
                    help="read tools from this root; pair with build's "
                         "--tools-root to evaluate an alternate configuration")
    ap.add_argument("--ver", default="v2")
    ap.add_argument("--gate-mode", default="pool", choices=["pool", "crossfit"],
                    help="pool: one threshold fitted on every calibration "
                         "patch (what a deployment ships). crossfit: each "
                         "submission judged by a threshold fitted with its "
                         "fold held out (no submission influences its own rule)")
    ap.add_argument("--subset", default="",
                    help="smoke_set.json manifest; restricts the pass to its "
                         "sampled submissions for this problem")
    ap.add_argument("--only-missing", action="store_true",
                    help="run only submissions with no row yet for this model, "
                         "and merge into what is already on disk")
    args = ap.parse_args(argv)
    if not args.no_llm:
        load_env()

    prob = load_problem(args.problem, args.data_root)
    model_label = args.model
    files = _load_files(args, model_label)
    if not files:
        print(f"{args.problem}: no submissions selected, nothing to run")
        return 0
    correct = [f.read_text() for f in
               sorted((Path(args.data_root) / args.problem / "correct").glob("*.py"))]

    if args.with_learned:
        return run_with_learned(args, prob, files, correct, model_label)

    frozen_path = tool_path(args.problem, args.model, args.tools_root)
    frozen_rules = load_fixer(frozen_path)
    if args.framework_only:
        # What the build buys, isolated: the generic library and the transplant
        # are the same code either way, so removing only the authored rules
        # leaves a tool that differs from the frozen one in exactly one layer.
        frozen_rules = [r for r in frozen_rules if r.name.startswith("generic_")]
        args.no_llm = True                     # the ablation is a local question
    # Self-learning stages its rules in a scratch copy this pass never reads.
    stage = Path(tempfile.mkdtemp(prefix=f"sl_{args.problem}_"))
    shutil.copy(frozen_path, stage / "fixer.py")
    stage_fixer = stage / "fixer.py"

    att_build, build_usd = _build_cost(frozen_path)
    rules_build = [r.name for r in frozen_rules
                   if not r.name.startswith("generic_")]

    index = ReferenceIndex(correct)
    budget = SearchBudget()

    # A patch as large as the program it repairs is a rewrite, not a repair.
    gate = None if args.no_llm else RPS_GATE

    rows_l: list[dict] = []
    rows_lf: list[dict] = []
    learned_names: list[str] = []
    gated = gate_won = 0
    sl_usd = sl_seconds = 0.0
    sl_in = sl_out = 0

    for f in files:
        src = f.read_text()
        t0 = time.time()
        fz = local_repair(src, prob, frozen_rules, index, budget)
        t_frozen = time.time() - t0

        if fz.repaired:
            pr = rps(src, fz.patch)
            row = event_row(f.stem, model_label, fz.source, True, fz.patch,
                            pr, att_cpu=t_frozen, rules_l=fz.rules)
            rows_l.append(row)                 # CoEP_L takes what passes
            if gate is None or pr <= gate:
                rows_lf.append(dict(row))
                continue
            # Gate: this patch is an outlier for this assignment, so spend the
            # call. Keep whichever patch is smaller, so escalating can lose
            # money but never coverage or patch size.
            gated += 1
            fb = fallback_repair(src, prob, correct, model=args.model)
            fb_pr = rps(src, fb.patch) if fb.repaired else None
            better = fb.repaired and fb_pr < pr
            if better:
                gate_won += 1
            rows_lf.append(event_row(
                f.stem, model_label, "llm" if better else fz.source, True,
                fb.patch if better else fz.patch, fb_pr if better else pr,
                att_cpu=t_frozen, att_api=fb.seconds, in_tok=fb.in_tokens,
                out_tok=fb.out_tokens, api_usd=fb.usd,
                rules_l=[] if better else fz.rules))
            continue

        rows_l.append(event_row(f.stem, model_label, "none", False,
                                att_cpu=t_frozen))
        if args.no_llm:                        # CoEP_L-only mode (dry runs)
            rows_lf.append(event_row(f.stem, model_label, "none", False,
                                     att_cpu=t_frozen))
            continue

        fb = fallback_repair(src, prob, correct, model=args.model)
        new_rule: list[str] = []
        if fb.repaired and not _already_learned(stage_fixer, len(frozen_rules),
                                                src, prob, index, budget):
            ab = absorb(stage_fixer, src, fb.patch, prob,
                        model=args.model, budget=budget)
            sl_usd += ab.usd; sl_seconds += ab.seconds
            sl_in += ab.in_tokens; sl_out += ab.out_tokens
            if ab.absorbed and ab.rule_added:
                m = _RULE_NAME.search(ab.rule_added)
                name = m.group(1) if m else f"learned_{len(learned_names)}"
                learned_names.append(name)
                new_rule = [name]              # provenance, not this arm's fix
        rows_lf.append(event_row(f.stem, model_label,
                                 "llm" if fb.repaired else "none", fb.repaired,
                                 fb.patch, rps(src, fb.patch) if fb.repaired else None,
                                 att_cpu=t_frozen, att_api=fb.seconds,
                                 in_tok=fb.in_tokens, out_tok=fb.out_tokens,
                                 api_usd=fb.usd, rules_sl=new_rule))

    # Persist the augmentation as its own artifact, priced to itself.
    learned_file = stage / "learned.py"
    if learned_names and learned_file.exists():
        out = learned_path(args.problem, args.model).parent
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy(frozen_path, out / "fixer.py")
        shutil.copy(learned_file, out / "learned.py")
        (out / "cost.json").write_text(json.dumps(
            {"model": args.model, "usd": build_usd + sl_usd,
             "build_seconds": att_build + sl_seconds,
             "base_usd": build_usd, "self_learning_usd": sl_usd,
             "self_learning_seconds": sl_seconds,
             "in_tokens": sl_in, "out_tokens": sl_out,
             "n_learned": len(learned_names), "rules": learned_names}, indent=1))

    if args.framework_only:
        write_events(args.ver, args.problem, "coep_l_fw", rows_l)
    else:
        write_events(args.ver, args.problem, "coep_l", rows_l)
        write_events(args.ver, args.problem, "coep_lf", rows_lf)
    # Summarize the whole file, not just the rows this pass produced: a
    # --only-missing run touches a handful of submissions, but the arm's
    # reported result is the pool.
    # Only summarize what this pass actually wrote. Upserting another arm's
    # row from an empty list zeroes a completed measurement, which is exactly
    # what the ablation did to CoEP_LF before this guard existed.
    written = ([("CoEP_L_fw", "coep_l_fw")] if args.framework_only
               else [("CoEP_L", "coep_l"), ("CoEP_LF", "coep_lf")])
    for approach, stem in written:
        rows = read_events(args.ver, args.problem, stem, model_label)
        upsert_summary(args.ver, args.problem,
                       summarize_events(approach, model_label, rows,
                                        att_build=att_build,
                                        build_usd=build_usd,
                                        rules_build=rules_build))

    def rr(rows):
        return 100 * sum(r["Fixed"] for r in rows) / max(1, len(rows))

    print(f"=== {args.problem} [{model_label}] {len(files)} programs ===")
    print(f"ATT_build={att_build}s  $Build={build_usd}")
    print("RPS gate: " + (f"tau={gate}, fired on {gated} "
                          f"({100*gated/max(1,len(rows_l)):.1f}%), "
                          f"smaller patch on {gate_won}"
                          if gate is not None else "off (--no-llm)"))
    shown = ([("CoEP_L_fw", rows_l)] if args.framework_only
             else [("CoEP_L", rows_l), ("CoEP_LF", rows_lf)])
    for name, rows in shown:
        print(f"  {name:10s} RR={rr(rows):6.2f}%  n={len(rows)}")
    print(f"self-learning: {len(learned_names)} rule(s) absorbed, "
          f"${sl_usd:.6f}, {sl_seconds:.1f}s"
          + (f" -> {learned_path(args.problem, args.model).parent}"
             if learned_names else " (nothing persisted)"))
    print(f"results -> results/{args.ver}/{args.problem}/")
    return 0
