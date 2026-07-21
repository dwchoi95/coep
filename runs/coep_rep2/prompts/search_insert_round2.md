You previously wrote the following per-assignment repair module for the assignment "search_insert":

```python
"""Local, LLM-free automatic repair for the `search_insert` assignment.

Strategy:
  1. Try the submission itself (it may already pass).
  2. Try problem-specific AST rewrites targeting common misconceptions for
     this assignment (wrong bisect branch bodies, early `== x` returns that
     break leftmost-index semantics, `return -1` / wrong sentinel instead of
     `len(lst)`, `/` vs `//`, `// 1` typos, `lst[mid+1]` index shifts,
     `lo = mid` non-progress assignments, returning the wrong variable).
  3. Generic single-edit search over the original.
  4. Generic single-edit search stacked on top of each specific rewrite
     (covers many two-fault submissions cheaply).
  5. Generic two-edit search as a last resort.

Every candidate is validated through `first_passing`, which enforces the
full visible test suite and the rps <= 0.35 patch-size cap against the
ORIGINAL student source.
"""

import ast
import copy

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "search_insert"

TESTS = [
    {"args": [[1, 3, 5, 7], 5], "expected": 2},
    {"args": [[1, 3, 5, 7], 4], "expected": 2},
    {"args": [[1, 3, 5, 7], 0], "expected": 0},
    {"args": [[1, 3, 5, 7], 8], "expected": 4},
    {"args": [[], 4], "expected": 0},
    {"args": [[2, 2, 2, 2], 2], "expected": 0},
    {"args": [[1, 2, 2, 3], 2], "expected": 1},
    {"args": [[10], 10], "expected": 0},
    {"args": [[10], 5], "expected": 0},
    {"args": [[10], 15], "expected": 1},
    {"args": [[1, 1, 2, 3, 3, 3, 4], 3], "expected": 3},
    {"args": [[-5, -2, 0, 3], -2], "expected": 1},
    {"args": [[1, 3, 5, 7], 1], "expected": 0},
    {"args": [[1, 3, 5, 7], 7], "expected": 3},
]


def _list_param(tree):
    """Name of the student's list parameter (first arg of the entry fn)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            if node.args.args:
                return node.args.args[0].arg
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.args.args:
            return node.args.args[0].arg
    return "lst"


def _nth(tree, typ, n):
    """n-th node of the given type in deterministic ast.walk order."""
    i = 0
    for node in ast.walk(tree):
        if isinstance(node, typ):
            if i == n:
                return node
            i += 1
    return None


def _count(tree, typ):
    return sum(1 for node in ast.walk(tree) if isinstance(node, typ))


def _stmt_lists(tree):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            val = getattr(node, field, None)
            if isinstance(val, list):
                yield node, field, val


def _emit(out, seen, tree):
    try:
        ast.fix_missing_locations(tree)
        src = ast.unparse(tree)
    except Exception:
        return
    if src not in seen:
        seen.add(src)
        out.append(src)


def _assigned_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
                elif isinstance(tgt, ast.Tuple):
                    for el in tgt.elts:
                        if isinstance(el, ast.Name):
                            names.add(el.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.For):
            tgt = node.target
            if isinstance(tgt, ast.Name):
                names.add(tgt.id)
            elif isinstance(tgt, ast.Tuple):
                for el in tgt.elts:
                    if isinstance(el, ast.Name):
                        names.add(el.id)
    return names


def _len_call(param):
    return ast.Call(
        func=ast.Name(id="len", ctx=ast.Load()),
        args=[ast.Name(id=param, ctx=ast.Load())],
        keywords=[],
    )


def _specific_variants(source):
    """Problem-specific single rewrites, each returned as full module source."""
    out, seen = [], set()
    try:
        tree = ast.parse(source)
    except Exception:
        return out
    seen.add(source)
    param = _list_param(tree)
    assigned = _assigned_names(tree)

    # --- If-statement rewrites -------------------------------------------
    for n in range(_count(tree, ast.If)):
        # (a) swap the two branch bodies (wrong bisect branch assignment)
        t = copy.deepcopy(tree)
        node = _nth(t, ast.If, n)
        if node is not None and node.orelse:
            node.body, node.orelse = list(node.orelse), list(node.body)
            _emit(out, seen, t)
        # (b) delete an early `if ...: return ...` (breaks leftmost semantics
        # for duplicates, e.g. `if lst[mid] == x: return mid`)
        t = copy.deepcopy(tree)
        node = _nth(t, ast.If, n)
        if (
            node is not None
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Return)
        ):
            for parent, field, stmts in _stmt_lists(t):
                if any(s is node for s in stmts):
                    i = next(k for k, s in enumerate(stmts) if s is node)
                    replacement = list(node.orelse)
                    if len(stmts) - 1 + len(replacement) >= 1:
                        stmts[i : i + 1] = replacement
                        _emit(out, seen, t)
                    break

    # --- Assignment rewrites: `lo = mid` -> `lo = mid + 1` / `mid - 1` ---
    for n in range(_count(tree, ast.Assign)):
        for op in (ast.Add, ast.Sub):
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Assign, n)
            if node is not None and isinstance(node.value, ast.Name):
                node.value = ast.BinOp(
                    left=node.value, op=op(), right=ast.Constant(1)
                )
                _emit(out, seen, t)

    # --- Return rewrites --------------------------------------------------
    for n in range(_count(tree, ast.Return)):
        base = _nth(tree, ast.Return, n)
        if base is None or base.value is None:
            continue
        v = base.value
        is_const_int = (
            isinstance(v, ast.Constant) and isinstance(v.value, int)
        ) or (
            isinstance(v, ast.UnaryOp)
            and isinstance(v.op, (ast.USub, ast.UAdd))
            and isinstance(v.operand, ast.Constant)
        )
        if is_const_int:
            # `return -1` / wrong sentinel -> `return len(lst)` or `return 0`
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Return, n)
            node.value = _len_call(param)
            _emit(out, seen, t)
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Return, n)
            node.value = ast.Constant(0)
            _emit(out, seen, t)
        elif isinstance(v, ast.Name):
            # returning the wrong variable, an off-by-one variable value,
            # or a variable where `len(lst)` was intended
            for other in sorted(assigned - {v.id}):
                t = copy.deepcopy(tree)
                node = _nth(t, ast.Return, n)
                node.value = ast.Name(id=other, ctx=ast.Load())
                _emit(out, seen, t)
            for op in (ast.Add, ast.Sub):
                t = copy.deepcopy(tree)
                node = _nth(t, ast.Return, n)
                node.value = ast.BinOp(
                    left=node.value, op=op(), right=ast.Constant(1)
                )
                _emit(out, seen, t)
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Return, n)
            node.value = _len_call(param)
            _emit(out, seen, t)

    # --- BinOp rewrites: `/` -> `//`, `// 1` -> `// 2` --------------------
    for n in range(_count(tree, ast.BinOp)):
        t = copy.deepcopy(tree)
        node = _nth(t, ast.BinOp, n)
        if node is not None and isinstance(node.op, ast.Div):
            node.op = ast.FloorDiv()
            _emit(out, seen, t)
        t = copy.deepcopy(tree)
        node = _nth(t, ast.BinOp, n)
        if (
            node is not None
            and isinstance(node.op, ast.FloorDiv)
            and isinstance(node.right, ast.Constant)
            and node.right.value == 1
        ):
            node.right = ast.Constant(2)
            _emit(out, seen, t)

    # --- Subscript rewrites: `lst[mid + 1]` / `lst[mid - 1]` -> `lst[mid]`
    for n in range(_count(tree, ast.Subscript)):
        t = copy.deepcopy(tree)
        node = _nth(t, ast.Subscript, n)
        if node is not None:
            sl = node.slice
            if (
                isinstance(sl, ast.BinOp)
                and isinstance(sl.op, (ast.Add, ast.Sub))
                and isinstance(sl.left, ast.Name)
                and isinstance(sl.right, ast.Constant)
            ):
                node.slice = sl.left
                _emit(out, seen, t)

    return out


def repair(source):
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except Exception:
            return None

        specific = _specific_variants(source)

        # Stage 0: identity + problem-specific single rewrites.
        res = first_passing(
            chain(iter([source]), iter(specific)),
            ENTRY,
            TESTS,
            source,
            max_rps=0.35,
            max_checks=len(specific) + 1,
        )
        if res is not None:
            return res

        # Stage 1: generic single-edit search on the original.
        res = first_passing(
            candidates_generic(source, max_edits=1, budget=600),
            ENTRY,
            TESTS,
            source,
            max_rps=0.35,
            max_checks=600,
        )
        if res is not None:
            return res

        # Stage 2: one generic edit stacked on each specific rewrite
        # (cheap coverage of common two-fault submissions; rps is still
        # measured against the true original).
        if specific:
            gens = [
                candidates_generic(sp, max_edits=1, budget=150)
                for sp in specific[:20]
            ]
            res = first_passing(
                chain(*gens),
                ENTRY,
                TESTS,
                source,
                max_rps=0.35,
                max_checks=1200,
            )
            if res is not None:
                return res

        # Stage 3: generic two-edit search as a last resort.
        res = first_passing(
            candidates_generic(source, max_edits=2, budget=2000),
            ENTRY,
            TESTS,
            source,
            max_rps=0.35,
            max_checks=1800,
        )
        return res
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: NOT REPAIRED — no_patch
- crafted_10.py: NOT REPAIRED — no_patch
- mutant_05.py: NOT REPAIRED — no_patch
- mutant_10.py: NOT REPAIRED — no_patch
- mutant_12.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission crafted_02.py
```python
def search_insert(lst, x):
    lo, hi = 0, len(lst)
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```

### Failed submission crafted_10.py
```python
def search_insert(lst, x):
    count = 0
    for v in lst:
        if v <= x:
            count += 1
    return count

```

### Failed submission mutant_05.py
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid + 1] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```

### Failed submission mutant_10.py
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 1
        if lst[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo

```

### Failed submission mutant_12.py
```python
def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 1
        if lst[mid] < x:
            lo = mid - 1
        else:
            hi = mid
    return lo

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
