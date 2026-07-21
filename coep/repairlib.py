"""Repair-operator library available to per-problem repairers.

A per-problem repairer is a Python module defining::

    def repair(source: str) -> str | None

It receives a buggy submission and returns a repaired version (or None if it
cannot repair). Repairers typically combine:

  * generic mutation-inversion operators (``candidates_generic``) — small
    semantic edits at every applicable AST site;
  * problem-specific rules/templates the builder writes (custom candidate
    generators keyed on detected patterns);
  * test-driven validation (``first_passing``) — the first candidate that
    passes the full visible test suite wins, subject to a patch-size cap so
    wholesale rewrites are rejected.

No LLM is involved at repair time; everything here is deterministic local
computation.
"""
from __future__ import annotations

import ast
import itertools
from collections.abc import Callable, Iterable, Iterator

from .evaluate import rps
from .mutation import _sites, mutate
from .sandbox import run_tests_inproc as run_tests

MAX_RPS_DEFAULT = 0.35


def candidates_generic(source: str, max_edits: int = 1,
                       budget: int = 2000) -> Iterator[str]:
    """Enumerate small semantic edits of `source` (1..max_edits sites).

    The operator set covers comparison/arith/bool operator swaps, integer
    off-by-one, boolean-constant flips, index shifts and argument swaps —
    the same fault classes common in novice code, applied in reverse.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    sites = _sites(tree)
    seen = {source}
    count = 0
    for k in range(1, max_edits + 1):
        for combo in itertools.combinations(sites, k):
            if count >= budget:
                return
            m = mutate(source, list(combo))
            count += 1
            if m is None or m in seen:
                continue
            try:
                compile(m, "<cand>", "exec")
            except SyntaxError:
                continue
            seen.add(m)
            yield m


def first_passing(candidates: Iterable[str], entry: str, tests: list[dict],
                  original: str, max_rps: float = MAX_RPS_DEFAULT,
                  max_checks: int = 800, timeout: float = 1.5) -> str | None:
    """Return the first candidate that passes ALL tests within the RPS cap."""
    for i, cand in enumerate(candidates):
        if i >= max_checks:
            return None
        if rps(original, cand) > max_rps:
            continue
        r = run_tests(cand, entry, tests, timeout=timeout)
        if r.all_pass:
            return cand
    return None


def failing_tests(source: str, entry: str, tests: list[dict],
                  timeout: float = 1.5):
    """Convenience: run the suite and return the RunResult (has .failures)."""
    return run_tests(source, entry, tests, timeout=timeout)


def chain(*generators: Callable[[str], Iterable[str]]) -> Callable[[str], Iterator[str]]:
    """Compose candidate generators into one, in priority order."""
    def gen(source: str) -> Iterator[str]:
        for g in generators:
            yield from g(source)
    return gen
