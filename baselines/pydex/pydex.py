"""PyDex baseline — reproduction of the *semantic phase* of
Zhang et al., "PyDex: Repairing Bugs in Introductory Python Assignments using
LLMs" (OOPSLA 2024), driven by our own models through ``src.utils.llm`` so
token/latency/cost accounting is uniform across arms.

Faithful mechanics (per the paper's Sec. 4.2 and Figs. 6-7):

* **Prompt** — the multimodal zero-shot prompt of Fig. 6, laid out exactly as
  shown: the buggy program FIRST, then the natural-language description, then
  the instructor test cases, closing with ``### Correct Program ###``.
* **K candidates** — each prompt yields up to ``K = 10`` candidates (one
  sampled completion per call at the provider's default temperature).
* **Semantic oracle** — every candidate is executed on the full test suite;
  candidates that raise or fail any test are discarded.
* **Selection** — among the surviving candidates, return the one with the
  smallest token-based edit distance to the student's submission.
* **Few-shot** (Sec. 4.2.2, Fig. 7) — when an example bank of (p, p') pairs is
  available (p buggy, p' the same student's later accepted version), the three
  most similar p — by 1 − normalized Hamming distance between test-failure
  vectors — are laid out as shots before the target program. Our corpora carry
  no per-student edit histories (the open-r1 submission dump has no author
  field), so the operative arm is zero-shot, which the paper itself evaluates
  as a competitive ablation; the few-shot path activates automatically when a
  ``pairs.json`` bank exists.

Accounting: ALL K calls are summed into in/out tokens, $ and API seconds —
including candidates that fail the oracle — exactly as a real deployment pays.
There is no iterative refinement in the semantic phase.
"""
from __future__ import annotations

import io
import json
import tokenize
from dataclasses import dataclass
from pathlib import Path

from src.runner.testing import run_tests
from src.utils import llm as llm_mod

K_DEFAULT = 10
SHOTS = 3
PROMPT_TESTS_CAP = 4          # test cases shown in the prompt (oracle uses all)


# ------------------------------------------------------------------ prompts
def _tests_text(problem: dict, cap: int = PROMPT_TESTS_CAP) -> str:
    """Instructor test cases in the paper's '#input: / # output :' layout."""
    blocks = []
    for t in (problem.get("tests") or [])[:cap]:
        if "stdin" in t:
            tin, tout = t["stdin"].rstrip("\n"), str(t["expected"]).rstrip("\n")
        else:
            entry = t.get("entry", problem.get("entry"))
            tin = f"{entry}({', '.join(map(repr, t.get('args', [])))})"
            tout = str(t.get("expected"))
        blocks.append(f"#input:\n{tin}\n# output :\n{tout}")
    return "\n\n".join(blocks)


def _desc_text(problem: dict) -> str:
    return "\n".join("# " + l if l.strip() else "#"
                     for l in (problem.get("description", "").strip().splitlines() or [""]))


def zero_shot_prompt(buggy: str, problem: dict) -> str:
    """Fig. 6: buggy program, problem description, test suite, completion cue."""
    return (f"[[Buggy Program]]\n"
            f"### Buggy Program ###\n{buggy.rstrip()}\n\n\n"
            f"[[Problem Description]]\n{_desc_text(problem)}\n\n"
            f"[[Test Suite]]\n{_tests_text(problem)}\n\n"
            f"### Correct Program ###\n")


def few_shot_prompt(shots: list[tuple[str, str]], buggy: str,
                    problem: dict) -> str:
    """Fig. 7: shots as a prefix, target program, test suite, completion cue."""
    parts = []
    for p, p_fixed in shots:
        parts.append(f"[[Shot Starts]]\n# Incorrect Program #\n{p.rstrip()}\n"
                     f"# Correct Program #\n{p_fixed.rstrip()}\n[Shot Ends]")
    parts.append(f"[[Buggy Program Starts]]\n### Buggy Program ###\n"
                 f"{buggy.rstrip()}\n[[Buggy Program Ends]]")
    parts.append(f"[[Test Suite Starts]]\n{_tests_text(problem)}\n"
                 f"[[Test Suite Ends]]")
    parts.append("### Correct Program ###\n")
    return "\n\n".join(parts)


# ------------------------------------------------------------------ selection
def _tokens(source: str) -> list[str]:
    try:
        return [t.string for t in
                tokenize.generate_tokens(io.StringIO(source).readline)
                if t.string.strip()]
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        return source.split()


def token_edit_distance(a: str, b: str) -> int:
    """Levenshtein distance over lexical tokens (Yasunaga & Liang 2021)."""
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) > len(tb):
        ta, tb = tb, ta
    prev = list(range(len(ta) + 1))
    for j, y in enumerate(tb, 1):
        cur = [j]
        for i, x in enumerate(ta, 1):
            cur.append(min(prev[i] + 1, cur[i - 1] + 1,
                           prev[i - 1] + (x != y)))
        prev = cur
    return prev[-1]


# ------------------------------------------------------------------ few-shot bank
class ShotBank:
    """(p, p') example bank with failure-vector retrieval (Sec. 4.2.2).

    ``pairs.json`` maps buggy file names to the same student's later accepted
    file names: {"wrong_1_004.py": "correct_1_004.py", ...}. Failure vectors
    are computed once per bank program on the full suite.
    """

    def __init__(self, problem: dict, data_dir: Path):
        self.problem = problem
        self.entries: list[tuple[tuple, str, str]] = []
        pairs_file = data_dir / "pairs.json"
        if not pairs_file.exists():
            return
        pairs = json.loads(pairs_file.read_text())
        for wrong_name, correct_name in pairs.items():
            wp, cp = data_dir / "buggy" / wrong_name, data_dir / "correct" / correct_name
            if not (wp.exists() and cp.exists()):
                continue
            p_src = wp.read_text()
            vec = self._vector(p_src)
            self.entries.append((vec, p_src, cp.read_text()))

    def _vector(self, source: str) -> tuple:
        res = run_tests(source, self.problem)
        return res.signature()

    def retrieve(self, buggy: str, k: int = SHOTS) -> list[tuple[str, str]]:
        if not self.entries:
            return []
        tv = self._vector(buggy)

        def sim(vec):
            n = max(len(vec), len(tv), 1)
            ham = sum(1 for a, b in zip(vec, tv) if (a == "pass") != (b == "pass"))
            ham += abs(len(vec) - len(tv))
            return 1 - ham / n

        ranked = sorted(self.entries, key=lambda e: -sim(e[0]))
        return [(p, pf) for _v, p, pf in ranked[:k]]


# ------------------------------------------------------------------ repair
@dataclass
class PyDexResult:
    repaired: bool
    patch: str | None
    calls: int = 0
    valid: int = 0                 # candidates that passed the full suite
    in_tokens: int = 0
    out_tokens: int = 0
    seconds: float = 0.0           # summed API latency across ALL calls
    usd: float = 0.0
    prompt: str = ""               # the prompt used (for prefix analysis)


def repair(buggy: str, problem: dict, model: str = "claude-haiku",
           k: int = K_DEFAULT, bank: ShotBank | None = None,
           llm_fn=None) -> PyDexResult:
    """One semantic-phase repair: K sampled candidates, oracle, min-edit pick."""
    shots = bank.retrieve(buggy) if bank is not None else []
    prompt = (few_shot_prompt(shots, buggy, problem) if shots
              else zero_shot_prompt(buggy, problem))
    call = llm_fn or llm_mod.complete

    res = PyDexResult(False, None, prompt=prompt)
    survivors: list[str] = []
    for _ in range(k):
        comp = call(prompt, model=model, temperature=None)   # provider default
        res.calls += 1
        res.in_tokens += comp.in_tokens
        res.out_tokens += comp.out_tokens
        res.seconds += comp.seconds
        res.usd += comp.usd
        code = comp.code
        if not code:
            continue
        if run_tests(code, problem).all_pass:
            survivors.append(code)

    res.valid = len(survivors)
    if survivors:
        res.repaired = True
        res.patch = min(survivors, key=lambda c: token_edit_distance(buggy, c))
    return res
