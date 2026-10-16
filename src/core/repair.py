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

import ast
import signal
import threading
import time
from dataclasses import dataclass, field

from src.runner.testing import run_batch, run_tests

# A generated rule can contain an infinite loop; a rule's apply() runs in this
# process, so no subprocess timeout bounds it. Cap it with a wall-clock alarm.
RULE_APPLY_TIMEOUT = 2.0


def edit_sites(a, b) -> int:
    """Maximal AST positions at which ``a`` and ``b`` differ.

    A position is a node whose own name, constant or operator changed, a node
    replaced by one of another type, or one run of a statement or expression
    list replaced by another (an insertion or deletion is such a run).
    """
    if type(a) is not type(b):
        return 1
    if isinstance(a, list):
        if len(a) == len(b):
            return sum(edit_sites(x, y) for x, y in zip(a, b))
        return 1
    if isinstance(a, ast.AST):
        n = 0
        for f in a._fields:
            x, y = getattr(a, f, None), getattr(b, f, None)
            if isinstance(x, (ast.AST, list)) or isinstance(y, (ast.AST, list)):
                n += edit_sites(x, y) if (x is not None and y is not None) else 1
            elif x != y:
                return 1
        return n
    return 0 if a == b else 1


def single_site(source: str, candidate: str, _tree: ast.AST | None = None) -> bool:
    """The rule contract: one application rewrites exactly one AST position,
    a subtree or a run of a list, and leaves the rest of the program alone."""
    try:
        return edit_sites(_tree or ast.parse(source), ast.parse(candidate)) == 1
    except SyntaxError:
        return False


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
        out = [out] if isinstance(out, str) else list(out)
        # Enforce the contract the builder is asked to follow: a candidate that
        # rewrites more than one position is not this rule's to propose.
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return out                         # nothing to compare against
        return [c for c in out if isinstance(c, str) and single_site(source, c, tree)]


@dataclass
class SearchBudget:
    candidate_timeout: float = 3.0        # hard wall per candidate (subprocess kill)


def _ordered(rules: list[Rule], signature: tuple[str, ...]) -> list[Rule]:
    """Rules whose declared symptoms occur in this program's failures first."""
    present = set(signature)
    return sorted(rules, key=lambda r: 0 if (set(r.symptoms) & present) else 1)


def repair(source: str, problem: dict, rules: list[Rule],
           budget: SearchBudget | None = None) -> RepairResult:
    """Search rule combinations until all tests pass or the budget is spent."""
    budget = budget or SearchBudget()
    t0 = time.time()

    # No shortcut for a submission that already passes: the corpus labels it
    # buggy, so it enters the search like every other one and is measured on
    # whatever the strategies do to it. Returning it unedited would hand this
    # arm a free patch of size zero that the per-submission baselines, which
    # query the model regardless, never get.
    base = run_tests(source, problem, timeout=budget.candidate_timeout)
    signature = base.signature()
    ordered = _ordered(rules, signature)

    # One depth at a time: expand every program found so far by one more rule
    # application, test that layer, and stop at the first layer that passes.
    #
    # Nothing here is capped -- not combination length, not candidate count, not
    # fan-out. Those were three arbitrary numbers, and testing layer by layer
    # removes the need for them: a submission repaired by one edit costs one
    # small layer, and the combinatorial blow-up two or three layers down is
    # only ever reached by submissions no rule set was going to repair anyway,
    # where ``candidate_timeout`` ends the search.
    #
    # Testing per layer also makes the shallowest repair the one returned, by
    # construction rather than by luck of ordering. Depth is a proxy for patch
    # size, and small patches are the point.
    deadline = t0 + budget.candidate_timeout
    frontier: list[tuple[str, tuple[str, ...]]] = [(source, ())]
    seen = {source}
    tried = 0

    while frontier and time.time() < deadline:
        layer: list[tuple[str, tuple[str, ...]]] = []
        for parent, prov in frontier:
            if time.time() >= deadline:
                break
            for rule in ordered:
                for cand in rule(parent):
                    if cand in seen:
                        continue
                    seen.add(cand)
                    layer.append((cand, prov + (rule.name,)))
        if not layer:
            break
        tried += len(layer)
        cands = [c for c, _ in layer]
        flags = run_batch(cands, problem,
                          per_candidate_timeout=budget.candidate_timeout)
        for (cand, prov), ok in zip(layer, flags):
            if ok:
                return RepairResult(True, cand, prov, tried,
                                    time.time() - t0, "local", signature)
        frontier = layer

    return RepairResult(False, None, (), tried, time.time() - t0,
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
