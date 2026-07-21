"""Prompt construction for both repair paradigms.

Every LLM interaction in the study is a single-shot prompt->response pair.
Token accounting is computed from these exact strings.
"""
from __future__ import annotations

import json


def render_tests(entry: str, tests: list[dict]) -> str:
    lines = []
    for t in tests:
        args = ", ".join(json.dumps(a) for a in t["args"])
        fn = t.get("entry", entry)
        lines.append(f"assert {fn}({args}) == {json.dumps(t['expected'])}")
    return "\n".join(lines)


def baseline_repair_prompt(problem: dict, buggy_source: str) -> str:
    """Per-instance LLM repair prompt (the conventional APR-with-LLM setup)."""
    return f"""You are an automated program repair system for introductory programming assignments.

## Assignment
{problem['description']}

The solution must be a Python function named `{problem['entry']}`.

## Visible test suite
{render_tests(problem['entry'], problem['tests'])}

## Buggy student submission
```python
{buggy_source}
```

## Task
Fix the student's submission so that it passes every test above.
Rules:
- Preserve the student's overall approach and identifiers; make the smallest change that fixes the bug. Do NOT rewrite the program from scratch.
- Do not add comments or explanations.
- Output ONLY the complete corrected program in a single ```python code block, nothing else.
"""


REPAIRLIB_DOC = '''You may use the helper library `coep.repairlib` (importable as shown):

```python
from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps
```

- `candidates_generic(source, max_edits=1, budget=2000)` -> iterator of candidate
  programs obtained by small semantic edits at every applicable AST site
  (comparison/arithmetic/boolean operator swaps, integer off-by-one,
  boolean-constant flips, index shifts, argument swaps). `max_edits=2`
  enumerates pairs of edits (much larger; use a budget).
- `first_passing(candidates, entry, tests, original, max_rps=0.35, max_checks=800)`
  -> the first candidate passing ALL tests whose relative patch size vs the
  original is <= max_rps, else None. Each test is {"args": [...], "expected": ...}.
- `failing_tests(source, entry, tests)` -> RunResult with `.compiled`,
  `.passed`, `.total`, `.failures` (list of {index, args, expected, got, error}),
  useful for dispatching on the observed failure pattern.
- `rps(buggy, patched)` -> token-level relative patch size.
- `chain(gen1, gen2, ...)` -> compose candidate generators in priority order.
- Standard library (`ast`, `re`, `itertools`, ...) is fully available.
'''


def builder_prompt(problem: dict, build_examples: list[dict],
                   refs: list[str]) -> str:
    """Prompt asking the agent to synthesize a per-problem local repairer."""
    ex_parts = []
    for i, ex in enumerate(build_examples, 1):
        ex_parts.append(f"### Example buggy submission {i} (id: {ex['id']})\n"
                        f"```python\n{ex['source']}\n```")
    refs_part = "\n\n".join(f"### Reference solution {i}\n```python\n{r}\n```"
                            for i, r in enumerate(refs, 1))
    return f"""You are building a LOCAL, LLM-FREE automatic repair system for ONE programming assignment. It will be applied to many future buggy student submissions for this same assignment, so it must generalize beyond the examples below.

## Assignment
{problem['description']}

The solution must be a Python function named `{problem['entry']}`.

## Visible test suite (the repairer validates candidates against exactly these)
{render_tests(problem['entry'], problem['tests'])}

{refs_part}

## Sample buggy student submissions (from past semesters)
{chr(10).join(ex_parts)}

## Helper library
{REPAIRLIB_DOC}

## Your task
Write a Python module that defines:

```python
def repair(source: str) -> str | None:
    ...
```

`repair` takes a buggy submission (a string containing a definition of `{problem['entry']}`) and returns a corrected version passing ALL tests, or None. Requirements:

1. NO network or LLM calls — pure local computation. It must run in at most ~10 seconds per submission.
2. The repaired program must PRESERVE the student's own approach: its token-level relative patch size vs. the input (`rps`) must be <= 0.35. Returning a reference solution or any fixed correct program is FORBIDDEN and counts as failure — repairs must be edits of the student's code.
3. Generalize: anticipate the misconceptions students commonly have for THIS assignment (study the description, tests, and examples). Combine problem-specific rewrite rules (e.g. AST transformations fixing typical wrong base cases, wrong initializations, wrong boundary handling for this problem) with the generic edit search, dispatching on the observed failing-test pattern where helpful.
4. Always validate candidates with `first_passing` (it enforces the test suite and the patch-size cap). Returning an unvalidated candidate is not allowed.
5. Handle bad input gracefully (syntax errors -> return None). Never raise.

The module will be imported with `coep` on sys.path, so the imports shown above work as-is. Hard-code the entry name and the test list inside the module (copy the test suite above exactly as `TESTS = [{{"args": [...], "expected": ...}}, ...]`).

Output ONLY the complete module in a single ```python code block, nothing else.
"""


def builder_refine_prompt(problem: dict, prev_module: str,
                          results: list[dict]) -> str:
    """Feedback round: previous repairer + its per-example outcomes."""
    lines = []
    failed_srcs = []
    for r in results:
        lines.append(f"- {r['id']}: {r['status']}" + (f" — {r['detail']}" if r.get("detail") else ""))
        if r["status"] != "REPAIRED" and r.get("source"):
            failed_srcs.append(f"### Failed submission {r['id']}\n```python\n{r['source']}\n```")
    failed_part = ("\n\nFor reference, the submissions the module failed on:\n\n"
                   + "\n\n".join(failed_srcs)) if failed_srcs else ""
    return f"""You previously wrote the following per-assignment repair module for the assignment "{problem['id']}":

```python
{prev_module}
```

Evaluated on the sample buggy submissions, the outcomes were:
{chr(10).join(lines)}{failed_part}

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
"""
