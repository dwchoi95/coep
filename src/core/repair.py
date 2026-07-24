"""Rule-combination search driver, with rule provenance.

A generated tool (``tools/<p_id>/fixer.py``) exposes a ``Fixer`` whose rules
are *candidate generators*: each rule maps a source string to zero or more
edited source strings. This driver composes them, validates every candidate
against the problem's tests, and stops as soon as one passes.

Two properties the rest of the system depends on:

* **Termination is test-pass only.** There is no patch-size gate; RPS is
  measured afterwards and reported, never used to reject a repair.
* **Provenance is recorded.** Every emitted patch carries the ordered list of
  rule identifiers that produced it, so per-rule statistics (which
  misconception fired how often) are available without re-running anything.
  v1 discarded this information; recovering it was impossible after the fact.

Search order is failure-signature driven: rules whose declared symptoms match
the program's failing tests are tried first, then single rules, then pairs,
then longer combinations, under an explicit budget rather than a blind 2^|R|.
"""
from __future__ import annotations

import itertools
import signal
import threading
import time
from dataclasses import dataclass, field

from src.runner.testing import run_batch, run_tests

# A generated rule can contain an infinite loop; a rule's apply() runs in this
# process, so no subprocess timeout bounds it. Cap it with a wall-clock alarm.
RULE_APPLY_TIMEOUT = 2.0


class _RuleTimeout(BaseException):
    """Not an ``Exception`` on purpose: a generated rule's ``except Exception``
    must not swallow its own runaway-loop timeout."""


def _apply_bounded(fn, source, seconds):
    """Run ``fn(source)`` under a wall-clock alarm (main thread + POSIX only)."""
    can_alarm = (hasattr(signal, "setitimer")
                 and threading.current_thread() is threading.main_thread())
    if not can_alarm:
        return fn(source)
    old = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(_RuleTimeout()))
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn(source)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


@dataclass
class RepairResult:
    """Outcome of repairing one buggy program."""
    repaired: bool
    patch: str | None = None
    rules: tuple[str, ...] = ()          # provenance: rules that produced the patch
    candidates_tried: int = 0
    seconds: float = 0.0
    source: str = "local"                # "local" | "fallback" | "none"
    failure_signature: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"repaired": self.repaired, "rules": list(self.rules),
                "candidates_tried": self.candidates_tried,
                "seconds": round(self.seconds, 3), "source": self.source,
                "failure_signature": list(self.failure_signature)}


@dataclass
class Rule:
    """One named repair rule from a generated tool.

    ``symptoms`` lets a rule declare which failure classes it targets
    (e.g. ``("wrong",)`` or ``("err:TypeError",)``); it is used only for search
    ordering, never for correctness.
    """
    name: str
    apply: callable                       # (source) -> Iterable[str]
    symptoms: tuple[str, ...] = ()

    def __call__(self, source: str):
        try:
            out = _apply_bounded(self.apply, source, RULE_APPLY_TIMEOUT)
        except (Exception, _RuleTimeout):     # bad rule (crash or runaway loop)
            return []
        if out is None:
            return []
        return [out] if isinstance(out, str) else list(out)


@dataclass
class SearchBudget:
    max_candidates: int = 2000
    max_seconds: float = 20.0
    max_combo: int = 3                    # longest rule combination to compose
    candidate_timeout: float = 3.0        # hard wall per candidate (subprocess kill)


def _ordered(rules: list[Rule], signature: tuple[str, ...]) -> list[Rule]:
    """Rules whose declared symptoms occur in this program's failures first."""
    present = set(signature)
    return sorted(rules, key=lambda r: 0 if (set(r.symptoms) & present) else 1)


def _compose(source: str, combo: tuple[Rule, ...]) -> list[str]:
    """Apply a rule combination in order, threading every intermediate result."""
    frontier = [source]
    for rule in combo:
        nxt = []
        for s in frontier:
            nxt.extend(rule(s))
        if not nxt:
            return []
        frontier = nxt[:16]               # keep the fan-out bounded
    return frontier


def repair(source: str, problem: dict, rules: list[Rule],
           budget: SearchBudget | None = None) -> RepairResult:
    """Search rule combinations until all tests pass or the budget is spent."""
    budget = budget or SearchBudget()
    t0 = time.time()

    base = run_tests(source, problem, timeout=budget.candidate_timeout)
    if base.all_pass:                     # already correct: nothing to repair
        return RepairResult(True, source, (), 0, time.time() - t0, "noop",
                            base.signature())
    signature = base.signature()
    ordered = _ordered(rules, signature)

    # Enumerate candidates (symptom-ordered, cheapest combinations first), then
    # validate the whole batch in ONE child process — spawning a subprocess per
    # candidate dominates otherwise. The batch stops at the first hit.
    cands: list[str] = []
    provs: list[tuple[str, ...]] = []
    seen = {source}
    for k in range(1, budget.max_combo + 1):
        combos = (itertools.permutations(ordered, k) if k > 1
                  else ((r,) for r in ordered))
        for combo in combos:
            for cand in _compose(source, combo):
                if cand in seen:
                    continue
                seen.add(cand)
                cands.append(cand)
                provs.append(tuple(r.name for r in combo))
                if len(cands) >= budget.max_candidates:
                    break
            if len(cands) >= budget.max_candidates:
                break
        if len(cands) >= budget.max_candidates:
            break

    flags = run_batch(cands, problem, per_candidate_timeout=budget.candidate_timeout)
    for cand, prov, ok in zip(cands, provs, flags):
        if ok:
            return RepairResult(True, cand, prov, len(cands), time.time() - t0,
                                "local", signature)
    return RepairResult(False, None, (), len(cands), time.time() - t0,
                        "none", signature)


# --------------------------------------------------------------- provenance
@dataclass
class ProvenanceLog:
    """Per-rule firing statistics across a problem's evaluation set.

    This is what turns the generated tool into a *diagnosis of the class*:
    how often each misconception rule fired, and on which programs.
    """
    fired: dict[str, list[str]] = field(default_factory=dict)

    def record(self, program_id: str, result: RepairResult) -> None:
        for name in result.rules:
            self.fired.setdefault(name, []).append(program_id)

    def profile(self) -> list[tuple[str, int]]:
        """Rules ranked by how many programs they repaired."""
        return sorted(((k, len(v)) for k, v in self.fired.items()),
                      key=lambda kv: -kv[1])

    def as_dict(self) -> dict:
        return {"profile": [{"rule": k, "count": n} for k, n in self.profile()],
                "fired": self.fired}
