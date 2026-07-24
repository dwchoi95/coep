"""`run.py compare` — one pass over a problem's submission stream, three
CoEP variants recorded simultaneously (no duplicated LLM calls):

* **CoEP_L**    — the frozen local tool alone (zero LLM at deployment).
* **CoEP_LF**   — CoEP_L plus per-submission LLM fallback on abstentions.
* **CoEP_LFSL** — CoEP_LF plus absorption of successful fallback fixes into new
  rules; later submissions run against the accumulated tool.

Derivation in a single pass: every submission first runs the *frozen* local
tool (that is CoEP_L's outcome; it is also the other two arms' local outcome
whenever it repairs). Only on a frozen miss do we (a) retry with the *evolving*
tool if self-learning has added rules (an LFSL-only local hit), (b) make the
one fallback call CoEP_LF needs anyway --- LFSL shares that call and its price
unless (a) already repaired --- and (c) absorb a successful fallback fix into
the LFSL tool (priced to LFSL alone). Timings are decomposed throughout:
``t_cpu`` (local search) vs ``t_api`` (model-call latency); the one-off build
wall-clock (``ATT_build``) is read from the tool's ``cost.json``.

Everything RQ1--RQ3 need is persisted under ``results/v2/runs/<pid>/<backend>/``:

* ``events.jsonl``  — one line per truly-buggy submission (see event schema in
  the code): repair source, fired rule chain, per-arm RPS, decomposed timings,
  fallback/absorption tokens+USD, and the *name* of every learned rule.
* ``summary.json``  — per-problem aggregates for all three arms (RR, RPS,
  ATT_cpu/api/all, InT/OuT, USD), the frozen source split, build cost/time,
  and the learned-rule list.
* ``learned.py``    — the final self-learned rules artifact.

So RQ1 (RR/RPS per arm), RQ2 (ATT decomposition, tokens, LLM cost), and RQ3
(rule provenance: builder-authored vs ``generic_*`` vs learned names, firing
counts, cross-problem recurrence) are all answerable from these files without
re-running anything.
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
from src.core.synthesis import backend_of, load_fixer
from src.experiments._common import load_env, load_problem, tool_path
from src.utils.metrics import rps


class _Arm:
    """Aggregates one variant's metrics."""

    def __init__(self, name):
        self.name = name
        self.n = self.repaired = 0
        self.rps_sum = self.t_cpu = self.t_api = self.usd = 0.0
        self.in_tok = self.out_tok = 0

    def add(self, repaired, patch_rps=0.0, t_cpu=0.0, t_api=0.0,
            in_tok=0, out_tok=0, usd=0.0):
        self.n += 1
        self.repaired += int(repaired)
        self.rps_sum += patch_rps if repaired else 0.0
        self.t_cpu += t_cpu; self.t_api += t_api
        self.in_tok += in_tok; self.out_tok += out_tok; self.usd += usd

    def row(self):
        n, r = max(1, self.n), self.repaired
        return {"n": self.n, "repaired": self.repaired,
                "RR": round(100*r/n, 2), "RPS": round(self.rps_sum/max(1, r), 3),
                "ATT_cpu": round(self.t_cpu/n, 3), "ATT_api": round(self.t_api/n, 3),
                "ATT_all": round((self.t_cpu+self.t_api)/n, 3),
                "InT": round(self.in_tok/n, 1), "OuT": round(self.out_tok/n, 1),
                "USD": round(self.usd, 4)}


_RULE_NAME = re.compile(r"Rule\(\s*['\"]([^'\"]+)['\"]")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py compare")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-haiku")
    ap.add_argument("--limit", type=int, default=0, help="0 = all buggy programs")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip fallback/absorption (CoEP_L only; no API key needed)")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--out", default="results/v2")
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
    index = ReferenceIndex(correct)
    budget = SearchBudget(max_candidates=150, max_combo=2, candidate_timeout=3)

    backend = backend_of(args.model)
    run_dir = Path(args.out) / "runs" / args.problem / backend
    run_dir.mkdir(parents=True, exist_ok=True)
    L, F, S = _Arm("CoEP_L"), _Arm("CoEP_LF"), _Arm("CoEP_LFSL")
    sources = {"rules": 0, "reference": 0, "none": 0}
    noop = 0
    learned_names: list[str] = []

    with (run_dir / "events.jsonl").open("w") as ev:
        for f in files:
            src = f.read_text()
            t0 = time.time()
            fz = local_repair(src, prob, frozen_rules, index, budget)
            t_frozen = time.time() - t0
            if fz.source == "noop":
                noop += 1
                continue
            sources[fz.source] = sources.get(fz.source, 0) + 1
            e = {"file": f.name, "frozen": fz.source,
                 "t_cpu_frozen": round(t_frozen, 3)}
            if fz.rules:
                e["rules"] = list(fz.rules)

            if fz.repaired:                   # all three arms share this hit
                pr = rps(src, fz.patch)
                for arm in (L, F, S):
                    arm.add(True, pr, t_cpu=t_frozen)
                e["rps"] = round(pr, 3)
                ev.write(json.dumps(e) + "\n"); ev.flush()
                continue

            L.add(False, t_cpu=t_frozen)      # CoEP_L abstains here

            # LFSL-only retry with the evolving tool (only if rules were learned)
            sl_hit, sl_cpu, sl_pr, sl_rules_used = False, 0.0, 0.0, []
            sl_rules = load_fixer(sl_path)
            if len(sl_rules) > n_frozen_rules:
                t1 = time.time()
                evolved = local_repair(src, prob, sl_rules, index, budget)
                sl_cpu = time.time() - t1
                if evolved.repaired:
                    sl_hit, sl_pr = True, rps(src, evolved.patch)
                    sl_rules_used = list(evolved.rules)
            if sl_cpu:
                e["t_cpu_sl"] = round(sl_cpu, 3)
            e["sl_local"] = sl_hit
            if sl_rules_used:
                e["sl_rules"] = sl_rules_used
                e["sl_rps"] = round(sl_pr, 3)

            if args.no_llm:                   # CoEP_L-only mode (format/dry runs)
                F.add(False, t_cpu=t_frozen)
                S.add(sl_hit, sl_pr, t_cpu=t_frozen + sl_cpu)
                ev.write(json.dumps(e) + "\n"); ev.flush()
                continue

            # the one fallback call CoEP_LF needs regardless
            fb = fallback_repair(src, prob, correct, model=args.model)
            fb_pr = rps(src, fb.patch) if fb.repaired else 0.0
            F.add(fb.repaired, fb_pr, t_cpu=t_frozen, t_api=fb.seconds,
                  in_tok=fb.in_tokens, out_tok=fb.out_tokens, usd=fb.usd)
            e.update({"fallback": fb.repaired, "t_api_fb": round(fb.seconds, 3),
                      "fb_in": fb.in_tokens, "fb_out": fb.out_tokens,
                      "fb_usd": round(fb.usd, 6)})
            if fb.repaired:
                e["fb_rps"] = round(fb_pr, 3)

            if sl_hit:                        # LFSL repaired locally: no call billed
                S.add(True, sl_pr, t_cpu=t_frozen + sl_cpu)
            else:                             # LFSL shares the fallback call
                t_ab = ab_in = ab_out = 0; ab_usd = 0.0
                if fb.repaired:               # ...and absorbs the fix
                    ab = absorb(sl_path, src, fb.patch, prob,
                                model=args.model, budget=budget)
                    t_ab, ab_in, ab_out, ab_usd = (ab.seconds, ab.in_tokens,
                                                   ab.out_tokens, ab.usd)
                    e["absorbed"] = ab.absorbed
                    if ab.absorbed and ab.rule_added:
                        m = _RULE_NAME.search(ab.rule_added)
                        name = m.group(1) if m else f"learned_{len(learned_names)}"
                        learned_names.append(name)
                        e["learned_rule"] = name
                    e.update({"t_api_ab": round(t_ab, 3), "ab_in": ab_in,
                              "ab_out": ab_out, "ab_usd": round(ab_usd, 6)})
                S.add(fb.repaired, fb_pr, t_cpu=t_frozen + sl_cpu,
                      t_api=fb.seconds + t_ab, in_tok=fb.in_tokens + ab_in,
                      out_tok=fb.out_tokens + ab_out, usd=fb.usd + ab_usd)
            ev.write(json.dumps(e) + "\n"); ev.flush()

    # persist the self-learned artifact and the per-problem summary
    if (sl_dir / "learned.py").exists():
        shutil.copy(sl_dir / "learned.py", run_dir / "learned.py")
    summary = {
        "pid": args.problem, "model": args.model, "backend": backend,
        "n_programs": len(files), "noop": noop, "n_buggy": len(files) - noop,
        "build": {"usd": build.get("usd"), "ATT_build": build.get("build_seconds"),
                  "rules": build.get("rules"), "rounds": build.get("rounds")},
        "sources_frozen": sources,
        "learned_rules": learned_names,
        "arms": {a.name: a.row() for a in (L, F, S)},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"=== {args.problem} [{args.model}] {len(files)} programs "
          f"({noop} noop excluded) ===")
    print(f"ATT_build = {build.get('build_seconds', 'n/a')}s  "
          f"build ${build.get('usd', 'n/a')}  rules learned: {len(learned_names)}")
    hdr = ["arm", "n", "RR", "RPS", "ATT_cpu", "ATT_api", "ATT_all", "InT", "OuT", "USD"]
    print("  ".join(f"{h:>8}" for h in hdr))
    for arm in (L, F, S):
        r = arm.row()
        print("  ".join(f"{str(r.get(h, arm.name)):>8}" for h in hdr))
    print(f"results -> {run_dir}/")
    return 0
