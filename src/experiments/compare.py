"""`run.py compare` — one pass over a problem's submission stream, three
\textsc{CoEP} variants recorded simultaneously (no duplicated LLM calls):

* **CoEP-L**  — the frozen local tool alone (zero LLM at deployment).
* **CoEP-H**  — CoEP-L plus per-submission LLM fallback on abstentions.
* **CoEP-SL** — CoEP-H plus absorption of successful fallback fixes into new
  rules; later submissions run against the accumulated tool.

Derivation in a single pass: every submission first runs the *frozen* local
tool (that is CoEP-L's outcome; it is also CoEP-H's and CoEP-SL's local
outcome whenever it repairs). Only on a frozen miss do we (a) retry with the
*evolving* tool if self-learning has added rules (an SL-only local hit),
(b) make the one fallback call CoEP-H needs anyway --- SL shares that call and
its price unless (a) already repaired --- and (c) absorb a successful fallback
fix into the SL tool (priced to SL alone). Timings are decomposed throughout:
``t_cpu`` (local search) vs ``t_api`` (model-call latency); the one-off build
wall-clock (``ATT_build``) is read from the tool's ``cost.json``.

Per-submission events are appended to ``results/v2/<pid>_<backend>.jsonl`` so
RQ3's rule analysis (which rules fired, built vs learned) needs no re-run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

from src.core.fallback import absorb, fallback_repair
from src.core.reference_repair import ReferenceIndex, local_repair
from src.core.repair import SearchBudget
from src.core.synthesis import backend_of, load_fixer
from src.experiments._common import (load_env, load_pool, load_problem, tool_path)
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
        return {"arm": self.name, "n": self.n, "RR": round(100*r/n, 2),
                "RPS": round(self.rps_sum/max(1, r), 3),
                "ATT_cpu": round(self.t_cpu/n, 3), "ATT_api": round(self.t_api/n, 3),
                "ATT_all": round((self.t_cpu+self.t_api)/n, 3),
                "InT": round(self.in_tok/n, 1), "OuT": round(self.out_tok/n, 1),
                "USD": round(self.usd, 4)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="run.py compare")
    ap.add_argument("--problem", required=True)
    ap.add_argument("--model", default="claude-haiku")
    ap.add_argument("--limit", type=int, default=0, help="0 = all buggy programs")
    ap.add_argument("--no-llm", action="store_true",
                    help="skip fallback/absorption (CoEP-L only; no API key needed)")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--out", default="results/v2")
    args = ap.parse_args(argv)
    if not args.no_llm:
        load_env()

    prob = load_problem(args.problem, args.data_root)
    buggy = load_pool(args.problem, "buggy", args.data_root)
    if args.limit:
        buggy = buggy[:args.limit]
    correct = load_pool(args.problem, "correct", args.data_root)

    frozen_path = tool_path(args.problem, args.model)
    frozen_rules = load_fixer(frozen_path)
    # SL evolves a *copy* of the tool so the frozen artifact stays pristine.
    sl_dir = Path(tempfile.mkdtemp(prefix=f"sl_{args.problem}_"))
    shutil.copy(frozen_path, sl_dir / "fixer.py")
    sl_path = sl_dir / "fixer.py"
    n_frozen_rules = len(frozen_rules)

    cost_file = frozen_path.parent / "cost.json"
    build = json.loads(cost_file.read_text()) if cost_file.exists() else {}
    index = ReferenceIndex(correct)
    budget = SearchBudget(max_candidates=150, max_combo=2, candidate_timeout=3)

    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    events = out_dir / f"{args.problem}_{backend_of(args.model)}.jsonl"
    L, H, SL = _Arm("CoEP-L"), _Arm("CoEP-H"), _Arm("CoEP-SL")
    noop = absorbed = 0

    with events.open("w") as ev:
        for i, src in enumerate(buggy):
            t0 = time.time()
            fz = local_repair(src, prob, frozen_rules, index, budget)
            t_frozen = time.time() - t0
            if fz.source == "noop":
                noop += 1
                continue
            e = {"i": i, "frozen": fz.source, "rules": list(fz.rules),
                 "t_cpu_frozen": round(t_frozen, 3)}

            if fz.repaired:                       # all three variants share this hit
                pr = rps(src, fz.patch)
                L.add(True, pr, t_cpu=t_frozen)
                H.add(True, pr, t_cpu=t_frozen)
                SL.add(True, pr, t_cpu=t_frozen)
                e["rps"] = round(pr, 3)
                ev.write(json.dumps(e) + "\n"); ev.flush()
                continue

            L.add(False, t_cpu=t_frozen)          # CoEP-L abstains here

            # SL-only retry with the evolving tool (only if rules were learned)
            sl_hit, sl_extra_cpu, sl_pr, sl_rules_used = False, 0.0, 0.0, []
            sl_rules = load_fixer(sl_path)
            if len(sl_rules) > n_frozen_rules:
                t1 = time.time()
                ev_res = local_repair(src, prob, sl_rules, index, budget)
                sl_extra_cpu = time.time() - t1
                if ev_res.repaired:
                    sl_hit, sl_pr = True, rps(src, ev_res.patch)
                    sl_rules_used = list(ev_res.rules)
            e["sl_local"] = sl_hit
            if sl_rules_used:
                e["sl_rules"] = sl_rules_used

            if args.no_llm:                       # CoEP-L-only mode
                H.add(False, t_cpu=t_frozen)
                SL.add(sl_hit, sl_pr, t_cpu=t_frozen + sl_extra_cpu)
                ev.write(json.dumps(e) + "\n"); ev.flush()
                continue

            # the one fallback call CoEP-H needs regardless
            fb = fallback_repair(src, prob, correct, model=args.model)
            fb_pr = rps(src, fb.patch) if fb.repaired else 0.0
            H.add(fb.repaired, fb_pr, t_cpu=t_frozen, t_api=fb.seconds,
                  in_tok=fb.in_tokens, out_tok=fb.out_tokens, usd=fb.usd)
            e["fallback"] = fb.repaired

            if sl_hit:                            # SL repaired locally: no call billed
                SL.add(True, sl_pr, t_cpu=t_frozen + sl_extra_cpu)
            else:                                 # SL shares the fallback call
                t_ab = ab_in = ab_out = 0; ab_usd = 0.0
                if fb.repaired:                   # ...and absorbs the fix
                    ab = absorb(sl_path, src, fb.patch, prob,
                                model=args.model, budget=budget)
                    absorbed += int(ab.absorbed)
                    t_ab, ab_in, ab_out, ab_usd = (ab.seconds, ab.in_tokens,
                                                   ab.out_tokens, ab.usd)
                    e["absorbed"] = ab.absorbed
                SL.add(fb.repaired, fb_pr, t_cpu=t_frozen + sl_extra_cpu,
                       t_api=fb.seconds + t_ab, in_tok=fb.in_tokens + ab_in,
                       out_tok=fb.out_tokens + ab_out, usd=fb.usd + ab_usd)
            ev.write(json.dumps(e) + "\n"); ev.flush()

    print(f"=== {args.problem} [{args.model}] {len(buggy)} programs "
          f"({noop} noop excluded) ===")
    print(f"ATT_build = {build.get('build_seconds', 'n/a')}s  "
          f"build ${build.get('usd', 'n/a')}  rules learned: {absorbed}")
    hdr = ["arm", "n", "RR", "RPS", "ATT_cpu", "ATT_api", "ATT_all", "InT", "OuT", "USD"]
    print("  ".join(f"{h:>8}" for h in hdr))
    for arm in (L, H, SL):
        r = arm.row()
        print("  ".join(f"{str(r[h]):>8}" for h in hdr))
    print(f"events -> {events}")
    return 0
