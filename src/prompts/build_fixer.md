You are building a deterministic, local repair tool for ONE programming
assignment. You will be shown the problem, a correct reference solution or two,
and a small sample of buggy student submissions. You write a Python module that
repairs these and *other* submissions with the same misconceptions — with no
further help from you at run time.

## Problem
{description}

## Test suite (the tool's patches are validated against the full suite)
{tests}

## Correct reference solution(s) — the intended logic
{references}

## Worked repairs to generalize (buggy → a correct fix)
Each pair is one student misconception and a correct program close to it. Write a
rule that reproduces the *transformation* from buggy to fixed, and that also
fires on OTHER submissions with the same misconception. Do not hard-code these
exact programs.
{samples}

## What to write

A single Python module. It MUST expose:

```python
from src.core.repair import Rule

class Fixer:
    def rules(self):
        return [ Rule(name=..., apply=..., symptoms=(...)), ... ]
```

Each `Rule` is a *candidate generator*:
- `name`: a string naming the misconception it targets (e.g. `"strict_lt_should_be_lte"`).
- `apply`: a function `source_str -> list[str]` returning zero or more edited
  program sources. Return `[]` when the rule does not apply. Never return the
  input unchanged.
- `symptoms`: a tuple of failure classes it addresses (`"wrong"`, `"timeout"`,
  or `"err:<ExceptionType>"`), used only to order the search — never for
  correctness.

### The one hard rule: locate on the AST, edit as a source-span splice
Parse with `ast.parse`, find the target node, compute its character span from
`lineno/col_offset/end_lineno/end_col_offset`, and splice the replacement into
the ORIGINAL source text. Leave every other byte identical. Do NOT rebuild the
program with `ast.unparse` — it reformats untouched lines and inflates the patch.

A helper you may copy verbatim:

```python
import ast

def _span(source, node):
    """(start, end) char offsets of node in source."""
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e

def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]
```

### A worked example rule (relax a strict comparison to non-strict)

```python
def _lt_to_le(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            # replace this whole comparison, rebuilding only its operator
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out
```

## Requirements
- Output ONLY one ```python code block: the complete module, importable as-is.
- Import only the standard library and `from src.core.repair import Rule`.
- Prefer a few *problem-specific* rules that target the misconceptions you see
  in the samples, plus a couple of generic slips (comparison flips, off-by-one
  on a `range`/index, a wrong `return`) if cheap.
- Emit candidates only. Do not test, do not print, do not claim correctness —
  the harness validates every candidate against the full suite.
- No comments explaining your reasoning; a short docstring per rule is fine.

## Forbidden: wholesale rewrites
Each candidate must differ from its input by a **small, local edit** — a changed
operator, one rewritten expression, an inserted/removed statement, a fixed
argument or bound. A rule that **replaces an entire function or the whole module
with a fixed/"canonical" solution is not allowed**, even if it makes tests pass:
it defeats the tool's purpose. Patch size is measured (tree-edit distance over
the buggy AST) and reported; a repair that rewrites the program scores as badly
as no repair, and gives an instructor no misconception signal. If you cannot see
a targeted edit for a misconception, omit the rule and let the submission
escalate — do not paper over it with a copy of the reference. As a guard, do not
splice a replacement whose span covers a whole `FunctionDef` body or the module.

{feedback}
