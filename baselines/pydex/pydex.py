"""PyDex baseline — reproduction.

Reproduces the PyDex pipeline (Zhang et al., "PyDex: Repairing Bugs in
Introductory Python Assignments using LLMs", OOPSLA 2024) as a *per-submission*
LLM repair baseline. It is driven by our own model (the same `src.utils.llm`
path as CoEP), so model choice is not a confound and ATT / InT / OuT / Cost are
measured identically across arms.

Reproduced components:

* **Multi-modal prompt** — problem description + buggy program + execution
  feedback (failing-test input/expected/got, or the interpreter error for a
  program that does not parse).
* **Multi-sample generation with test-based selection** — sample `samples`
  candidates per query, execute all, and select the best: any candidate passing
  the whole suite wins (ties broken by smallest edit, RPS); otherwise the
  candidate passing the most tests is carried forward.
* **Iterative refinement ("chaining")** — feed the surviving failures of the
  best candidate back into the prompt and re-query, up to `rounds` rounds.

This is a faithful reproduction of the algorithm, not of PyDex's original Codex
sampling: our cheapest models expose only the default temperature, so with
`samples == 1` the diversity comes from the iterative feedback loop rather than
temperature sampling. `samples > 1` issues independent calls where the model
allows it.
"""
from __future__ import annotations

import string
from dataclasses import dataclass
from pathlib import Path

from src.runner.testing import run_tests
from src.utils import llm as llm_mod
from src.utils.metrics import rps

_PROMPT = (Path(__file__).with_name("repair.md")).read_text()


@dataclass
class PyDexResult:
    repaired: bool
    patch: str | None
    rounds: int = 0
    calls: int = 0
    in_tokens: int = 0
    out_tokens: int = 0
    seconds: float = 0.0
    usd: float = 0.0


def _render(**fields) -> str:
    """Strict prompt fill (raise on a missing placeholder, like src.prompts)."""
    class _S(string.Formatter):
        def get_value(self, key, args, kwargs):
            if isinstance(key, str) and key not in kwargs:
                raise KeyError(key)
            return super().get_value(key, args, kwargs)
    return _S().vformat(_PROMPT, (), fields)


def _tests_block(problem: dict, limit: int = 6) -> str:
    lines = []
    for t in (problem.get("tests") or [])[:limit]:
        if "stdin" in t:
            lines.append(f"- input {t['stdin']!r} -> {t['expected']!r}")
        else:
            entry = t.get("entry", problem.get("entry"))
            lines.append(f"- {entry}({', '.join(map(repr, t.get('args', [])))}) "
                         f"= {t.get('expected')!r}")
    return "\n".join(lines)


def _feedback(source: str, problem: dict, limit: int = 5) -> str:
    """Execution feedback for the prompt: failing tests, or a parse error."""
    res = run_tests(source, problem)
    if res.error:
        return f"The program raised: {res.error}"
    lines = []
    for f in res.failures[:limit]:
        if f.get("timeout"):
            lines.append(f"- test {f['index']}: timed out")
        elif f.get("error"):
            lines.append(f"- test {f['index']}: {f['error']}")
        else:
            got = repr(f.get("got"))[:120]
            exp = repr(f.get("expected"))[:120]
            lines.append(f"- test {f['index']}: got {got}, expected {exp}")
    return "\n".join(lines) or "- (all example tests pass; hidden tests fail)"


def repair(buggy: str, problem: dict, model: str = "claude-haiku",
           rounds: int = 4, samples: int = 1, llm_fn=None) -> PyDexResult:
    """Repair one submission with the PyDex pipeline; measured, model-driven."""
    call = llm_fn or llm_mod.complete
    r = PyDexResult(repaired=False, patch=None)
    current = buggy
    best_partial, best_passed = buggy, -1

    for rnd in range(rounds):
        r.rounds = rnd + 1
        prompt = _render(description=problem.get("description", ""),
                         tests=_tests_block(problem),
                         buggy=current,
                         feedback=_feedback(current, problem))

        candidates = []
        for _ in range(max(1, samples)):
            comp = call(prompt, model=model)
            r.calls += 1
            r.in_tokens += comp.in_tokens
            r.out_tokens += comp.out_tokens
            r.seconds += comp.seconds
            r.usd += comp.usd
            if comp.code:
                candidates.append(comp.code)

        # test-based selection over this round's candidates
        round_best, round_passed = None, -1
        for cand in candidates:
            res = run_tests(cand, problem)
            if res.all_pass:
                # tie-break by smallest edit among fully-correct candidates
                if r.patch is None or rps(buggy, cand) < rps(buggy, r.patch):
                    r.patch, r.repaired = cand, True
            if res.passed > round_passed:
                round_best, round_passed = cand, res.passed
        if r.repaired:
            return r

        # chaining: carry the best partial candidate forward as the new source
        if round_best is not None and round_passed > best_passed:
            best_partial, best_passed = round_best, round_passed
        current = best_partial

    return r
