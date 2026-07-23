A local repair tool failed on the submission below, and a language model
repaired it. Generalize that single repair into a reusable rule.

## Problem
{description}

## Buggy submission
```python
{buggy}
```

## Accepted repair
```python
{fixed}
```

## Failure signature
{signature}

## Task
Write one rule for the problem's `Fixer` that would have produced this repair,
and that also fires on other submissions exhibiting the same misconception.

Requirements:
- Locate the edit on the AST; apply it as a span replacement on the original
  source so untouched lines stay byte-identical. Do not re-render the whole
  module with `ast.unparse`.
- Give the rule a name that states the misconception it targets.
- Declare the failure classes it addresses via `symptoms`.
- Emit candidates only; never claim a repair is correct. Validation is the
  harness's job.

Output ONLY one ```python code block containing the rule method.
