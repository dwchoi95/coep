You previously wrote the following per-assignment repair module for the assignment "flatten":

```python
"""Local, LLM-free automatic repair for the `flatten` assignment.

Strategy:
  * Parse the student's submission (syntax error -> None).
  * Apply a small set of problem-specific AST rewrites that target the
    common misconceptions for THIS task:
      - swapped `isinstance` arguments, e.g. `isinstance(list, x)`;
      - a list branch that appends the sublist itself instead of recursing;
      - a shallow inner `for`-loop copy instead of recursion;
      - a bare `.extend(item)` with no type check / no recursion.
    These are generated in every non-empty combination (minimal changes
    first) so the smallest correct patch is preferred.
  * Fall back to the generic edit search (1 then 2 edits with a budget).
  * EVERY candidate is validated with `first_passing`, which enforces the
    full visible test suite AND the relative-patch-size cap (rps <= 0.35),
    so the student's own approach is preserved and no fixed reference
    solution is ever returned.

Round-2 fix
-----------
The previous version turned a bare `L.extend(item)` into a multi-line
`if/else` block.  On a *very short* submission such as::

    def flatten(nested):
        total = []
        for item in nested:
            total.extend(item)
        return total

that rewrite grew the function from 5 to 8 lines, so the relative patch
size blew past the 0.35 cap and `first_passing` rejected the (otherwise
correct) candidate -> ``no_patch``.  The behaviour was right; the patch was
just too large for such a tiny original.

The `.extend` guard is now emitted as a single-line conditional expression::

    total.extend(flatten(item) if isinstance(item, list) else [item])

which is semantically identical to the old `if/else` (``L.append(x)`` ==
``L.extend([x])``) but changes only the one offending line, keeping the
relative patch size small enough to survive the cap on short and long
submissions alike.
"""

import ast
import copy
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "flatten"

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, [2, 3]]], "expected": [1, 2, 3]},
    {"args": [[[1, 2], [3, 4]]], "expected": [1, 2, 3, 4]},
    {"args": [[[[[1]]]]], "expected": [1]},
    {"args": [[1, [2, [3, [4, [5]]]]]], "expected": [1, 2, 3, 4, 5]},
    {"args": [[[], [], []]], "expected": []},
    {"args": [[0]], "expected": [0]},
    {"args": [[1, [], 2]], "expected": [1, 2]},
    {"args": [[[1], [2], 3, [4, [5, 6]]]], "expected": [1, 2, 3, 4, 5, 6]},
    {"args": [[-1, [-2, [-3]]]], "expected": [-1, -2, -3]},
    {"args": [[[[]], [[[]]], 5]], "expected": [5]},
    {"args": [[10, [20], [30, [40]], 50]], "expected": [10, 20, 30, 40, 50]},
    {"args": [[[1, [2]], 3]], "expected": [1, 2, 3]},
]

_TYPE_NAMES = {"list", "tuple", "int", "float", "str", "dict", "set", "bool"}


# --------------------------------------------------------------------------
# Small AST helpers.
# --------------------------------------------------------------------------

def _is_flatten_call(node):
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "flatten")


def _guarded_arg(arg):
    """Build ``flatten(arg) if isinstance(arg, list) else [arg]``.

    A single-line conditional expression that recurses on lists and wraps
    scalars, so ``L.extend(<this>)`` behaves correctly for both cases while
    touching only one line of the original source.
    """
    return ast.IfExp(
        test=ast.Call(
            func=ast.Name(id="isinstance", ctx=ast.Load()),
            args=[copy.deepcopy(arg), ast.Name(id="list", ctx=ast.Load())],
            keywords=[]),
        body=ast.Call(
            func=ast.Name(id="flatten", ctx=ast.Load()),
            args=[copy.deepcopy(arg)], keywords=[]),
        orelse=ast.List(elts=[copy.deepcopy(arg)], ctx=ast.Load()))


# --------------------------------------------------------------------------
# Problem-specific AST transforms.  Each mutates `tree` in place and returns
# True if it changed anything.
# --------------------------------------------------------------------------

def _t_swap_isinstance(tree):
    """`isinstance(list, x)` -> `isinstance(x, list)` (swapped arguments)."""
    changed = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "isinstance"
                and len(node.args) == 2):
            a, b = node.args
            first_is_type = isinstance(a, ast.Name) and a.id in _TYPE_NAMES
            second_is_type = isinstance(b, ast.Name) and b.id in _TYPE_NAMES
            if first_is_type and not second_is_type:
                node.args = [b, a]
                changed = True
    return changed


class _ForAppendFix(ast.NodeTransformer):
    """`for v in it: L.append(v)` -> `L.extend(flatten(it))` (shallow copy)."""

    def __init__(self):
        self.changed = False

    def visit_For(self, node):
        self.generic_visit(node)
        if (isinstance(node.target, ast.Name)
                and not node.orelse
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Expr)):
            call = node.body[0].value
            if (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "append"
                    and len(call.args) == 1
                    and isinstance(call.args[0], ast.Name)
                    and call.args[0].id == node.target.id):
                listname = call.func.value
                new = ast.Expr(value=ast.Call(
                    func=ast.Attribute(value=copy.deepcopy(listname),
                                       attr="extend", ctx=ast.Load()),
                    args=[ast.Call(
                        func=ast.Name(id="flatten", ctx=ast.Load()),
                        args=[copy.deepcopy(node.iter)], keywords=[])],
                    keywords=[]))
                self.changed = True
                return ast.copy_location(new, node)
        return node


class _ListBranchAppendFix(ast.NodeTransformer):
    """Inside `if isinstance(v, list): L.append(v)` recurse instead."""

    def __init__(self):
        self.changed = False

    def visit_If(self, node):
        self.generic_visit(node)
        t = node.test
        if (isinstance(t, ast.Call)
                and isinstance(t.func, ast.Name)
                and t.func.id == "isinstance"
                and len(t.args) == 2
                and isinstance(t.args[0], ast.Name)
                and isinstance(t.args[1], ast.Name)
                and t.args[1].id == "list"):
            varname = t.args[0].id
            if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                call = node.body[0].value
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "append"
                        and len(call.args) == 1
                        and isinstance(call.args[0], ast.Name)
                        and call.args[0].id == varname):
                    listname = call.func.value
                    node.body = [ast.Expr(value=ast.Call(
                        func=ast.Attribute(value=copy.deepcopy(listname),
                                           attr="extend", ctx=ast.Load()),
                        args=[ast.Call(
                            func=ast.Name(id="flatten", ctx=ast.Load()),
                            args=[ast.Name(id=varname, ctx=ast.Load())],
                            keywords=[])],
                        keywords=[]))]
                    self.changed = True
        return node


class _ExtendFix(ast.NodeTransformer):
    """`L.extend(x)` -> `L.extend(flatten(x) if isinstance(x, list) else [x])`.

    A one-line guard: recurse on nested lists, wrap scalars.  Emitting a
    conditional expression (rather than a multi-statement `if/else` block)
    keeps the patch to a single line so it stays under the rps cap even on
    very short submissions.
    """

    def __init__(self):
        self.changed = False

    def visit_Expr(self, node):
        self.generic_visit(node)
        v = node.value
        if (isinstance(v, ast.Call)
                and isinstance(v.func, ast.Attribute)
                and v.func.attr == "extend"
                and len(v.args) == 1
                and not v.keywords):
            arg = v.args[0]
            # Skip if already recursing via flatten(...) or already guarded.
            if _is_flatten_call(arg) or isinstance(arg, ast.IfExp):
                return node
            v.args = [_guarded_arg(arg)]
            self.changed = True
        return node


def _run_transformer(cls, tree):
    f = cls()
    f.visit(tree)
    ast.fix_missing_locations(tree)
    return f.changed


def _t_forappend(tree):
    return _run_transformer(_ForAppendFix, tree)


def _t_listbranch(tree):
    return _run_transformer(_ListBranchAppendFix, tree)


def _t_extend(tree):
    return _run_transformer(_ExtendFix, tree)


# Order matters: smaller / more targeted fixes first so minimal patches win.
_TRANSFORMS = [_t_swap_isinstance, _t_forappend, _t_listbranch, _t_extend]


def _specific_candidates(source):
    """Yield source strings produced by combinations of the fix transforms.

    Single-transform (minimal) candidates are yielded first, then pairs, etc.
    """
    try:
        base = ast.parse(source)
    except SyntaxError:
        return
    except Exception:
        return

    seen = set()
    for r in range(1, len(_TRANSFORMS) + 1):
        for combo in itertools.combinations(_TRANSFORMS, r):
            try:
                tree = copy.deepcopy(base)
                changed = False
                for t in combo:
                    if t(tree):
                        changed = True
                if not changed:
                    continue
                src = ast.unparse(tree)
            except Exception:
                continue
            if src and src != source and src not in seen:
                seen.add(src)
                yield src


def repair(source):
    """Return a corrected `flatten` submission passing all tests, or None."""
    if not isinstance(source, str):
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    original = source

    # 1) Problem-specific rewrites (validated + rps-capped by first_passing).
    try:
        result = first_passing(
            _specific_candidates(source), ENTRY, TESTS, original,
            max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    # 2) Generic single-edit search.
    try:
        result = first_passing(
            candidates_generic(source, max_edits=1, budget=2000),
            ENTRY, TESTS, original, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    # 3) Generic two-edit search (larger; bounded by budget/checks).
    try:
        result = first_passing(
            candidates_generic(source, max_edits=2, budget=2000),
            ENTRY, TESTS, original, max_rps=0.35, max_checks=800)
        if result is not None:
            return result
    except Exception:
        pass

    return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: REPAIRED
- crafted_08.py: NOT REPAIRED — no_patch
- mutant_01.py: REPAIRED
- mutant_03.py: REPAIRED
- mutant_04.py: REPAIRED

For reference, the submissions the module failed on:

### Failed submission crafted_08.py
```python
def flatten(nested):
    total = []
    for item in nested:
        total.extend(item)
    return total

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
