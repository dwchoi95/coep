The local repair tool could not fix the submission below, but the LLM fallback
did. Generalize that single repair into a reusable rule the tool can apply on
its own next time.

## Problem
{description}

## Buggy submission
```python
{buggy}
```

## Accepted repair (passes every test)
```python
{fixed}
```

## What changed
{diff}

## Task
Write ONE rule that would have produced this repair and that also fires on other
submissions with the same misconception. Emit exactly this shape, and nothing
else:

```python
def _learned_<short_name>(source):
    """<the misconception this targets>"""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    # ... locate the target node(s); splice the edit into the ORIGINAL source
    # (compute the node's char span from lineno/col_offset/end_lineno/
    # end_col_offset; do NOT ast.unparse the whole module) ...
    return out

LEARNED.append(Rule("<short_name>", _learned_<short_name>, symptoms=({symptoms})))
```

Requirements:
- Small, local edit only — a changed operator, one rewritten expression, an
  inserted/removed statement. **No whole-function or whole-module rewrites.**
- `source -> list[str]` of edited programs; `[]` when it does not apply; never
  return the input unchanged.
- Use `Rule` and `LEARNED` directly (both are already defined; do not import or
  redefine them). Give the function a unique name.
- Output ONLY the one ```python code block.
