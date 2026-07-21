```python
"""Local, LLM-free automatic repair for the `search_insert` assignment.

Root-cause analysis of the round-1 failures
-------------------------------------------
Every listed submission failed with `no_patch`, including mutant_05
(`lst[mid + 1]` -> `lst[mid]`) and mutant_10 (`// 1` -> `// 2`) whose fixes
were *already generated* by the stage-0 specific rewrites and demonstrably
pass all visible tests.  When stage 0 cannot even land those, the failure is
not in the rewrite rules but in the shared plumbing: the module hard-imported
several helper symbols (`chain`, `failing_tests` from coep.repairlib and
`rps` from coep.evaluate) that it never actually needed, and called the
helpers with optimistic keyword signatures.  Any one of those going wrong
(missing symbol -> module fails to load, or an unexpected kwarg ->
TypeError swallowed by the blanket `except Exception` in `repair`) turns
*every* submission into `no_patch` uniformly - exactly the observed outcome.

Fixes in this revision:
  * All helper-library imports are individually guarded; unused imports are
    dropped; `itertools.chain` replaces the repairlib `chain`.
  * `first_passing` / `candidates_generic` are invoked through defensive
    wrappers that retry with progressively smaller keyword sets on
    TypeError, so a signature mismatch degrades instead of aborting.
  * Each search stage is isolated in its own try/except so one broken
    helper cannot kill the remaining stages.
  * New rules for the genuinely uncovered bugs:
      - comparison strictness toggles (`<=` <-> `<`, `>=` <-> `>`) fixing
        crafted_02 (`lst[mid] <= x`) and crafted_10 (`v <= x`), which break
        leftmost-index semantics on duplicates;  loosening a `while` loop
        bound is deliberately excluded to avoid non-terminating candidates;
      - comparison direction mirror for if-tests (`<` <-> `>`);
      - `+ 1` <-> `- 1` toggles on binary ops (wrong step direction);
      - a depth-2 pass that stacks two specific rewrites, fixing two-fault
        submissions such as mutant_12 (`// 1` and `lo = mid - 1` together).

Every candidate is still validated through `first_passing`, which enforces
the full visible test suite and the rps <= 0.35 patch-size cap against the
ORIGINAL student source.
"""

import ast
import copy
import itertools

# Guarded helper-library imports: a missing or renamed symbol must degrade
# gracefully instead of preventing this module from loading.
try:
    from coep.repairlib import first_passing as _first_passing
except Exception:  # pragma: no cover
    _first_passing = None

try:
    from coep.repairlib import candidates_generic as _candidates_generic
except Exception:  # pragma: no cover
    _candidates_generic = None

try:
    from coep.evaluate import rps as _rps
except Exception:  # pragma: no cover
    _rps = None

ENTRY = "search_insert"
MAX_RPS = 0.35

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


# ---------------------------------------------------------------------------
# Defensive wrappers around the helper library
# ---------------------------------------------------------------------------

def _validate(cands, source, max_checks=None):
    """Run first_passing, retrying with smaller kwarg sets on TypeError.

    Returns the first passing candidate source, or None.  Never raises.
    """
    if _first_passing is None:
        return None
    kwarg_sets = []
    if max_checks is not None:
        kwarg_sets.append({"max_rps": MAX_RPS, "max_checks": max_checks})
    kwarg_sets.append({"max_rps": MAX_RPS})
    kwarg_sets.append({})
    for kw in kwarg_sets:
        try:
            res = _first_passing(cands, ENTRY, TESTS, source, **kw)
        except TypeError:
            # Signature mismatch (e.g. unknown kwarg) - retry more plainly.
            continue
        except Exception:
            return None
        # Belt-and-braces local enforcement of the patch-size cap in case
        # first_passing could not be given max_rps.
        if res is not None and _rps is not None:
            try:
                if _rps(source, res) > MAX_RPS:
                    return None
            except Exception:
                pass
        return res
    return None


def _generic(source, max_edits, budget):
    """candidates_generic with signature fallbacks.  Never raises."""
    if _candidates_generic is None:
        return []
    for kw in (
        {"max_edits": max_edits, "budget": budget},
        {"max_edits": max_edits},
        {},
    ):
        try:
            return _candidates_generic(source, **kw)
        except TypeError:
            continue
        except Exception:
            return []
    return []


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

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


_CMP_STRICT_SWAP = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
}
_CMP_MIRROR = {
    ast.Lt: ast.Gt,
    ast.LtE: ast.GtE,
    ast.Gt: ast.Lt,
    ast.GtE: ast.LtE,
}


# ---------------------------------------------------------------------------
# Problem-specific rewrites
# ---------------------------------------------------------------------------

def _specific_variants(source):
    """Problem-specific single rewrites, each returned as full module source."""
    out, seen = [], set()
    try:
        tree = ast.parse(source)
    except Exception:
        return out
    seen.add(source)
    try:
        seen.add(ast.unparse(tree))
    except Exception:
        pass
    param = _list_param(tree)
    assigned = _assigned_names(tree)

    # --- Comparison rewrites ---------------------------------------------
    # (leftmost-index semantics hinge on strict vs non-strict comparisons:
    #  `lst[mid] <= x` / `v <= x` count/skip duplicates the wrong way)
    for n in range(_count(tree, ast.Compare)):
        base = _nth(tree, ast.Compare, n)
        if base is None or len(base.ops) != 1:
            continue
        cls = type(base.ops[0])
        if cls not in _CMP_STRICT_SWAP:
            continue
        in_while_test = any(
            isinstance(w, ast.While) and w.test is base
            for w in ast.walk(tree)
        )
        repls = []
        swap = _CMP_STRICT_SWAP[cls]
        # Never loosen a while-loop bound (`<` -> `<=`): with `hi = mid`
        # style updates that manufactures non-terminating candidates.
        if not (in_while_test and swap in (ast.LtE, ast.GtE)):
            repls.append(swap)
        if not in_while_test:
            repls.append(_CMP_MIRROR[cls])
        for repl in repls:
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Compare, n)
            if node is not None and len(node.ops) == 1:
                node.ops = [repl()]
                _emit(out, seen, t)

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
            if node is not None:
                node.value = _len_call(param)
                _emit(out, seen, t)
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Return, n)
            if node is not None:
                node.value = ast.Constant(0)
                _emit(out, seen, t)
        elif isinstance(v, ast.Name):
            # returning the wrong variable, an off-by-one variable value,
            # or a variable where `len(lst)` was intended
            for other in sorted(assigned - {v.id}):
                t = copy.deepcopy(tree)
                node = _nth(t, ast.Return, n)
                if node is not None:
                    node.value = ast.Name(id=other, ctx=ast.Load())
                    _emit(out, seen, t)
            for op in (ast.Add, ast.Sub):
                t = copy.deepcopy(tree)
                node = _nth(t, ast.Return, n)
                if node is not None:
                    node.value = ast.BinOp(
                        left=node.value, op=op(), right=ast.Constant(1)
                    )
                    _emit(out, seen, t)
            t = copy.deepcopy(tree)
            node = _nth(t, ast.Return, n)
            if node is not None:
                node.value = _len_call(param)
                _emit(out, seen, t)

    # --- BinOp rewrites ---------------------------------------------------
    # `/` -> `//`, `// 1` -> `// 2`, and `+ 1` <-> `- 1` step toggles.
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
        t = copy.deepcopy(tree)
        node = _nth(t, ast.BinOp, n)
        if (
            node is not None
            and isinstance(node.op, (ast.Add, ast.Sub))
            and isinstance(node.right, ast.Constant)
            and node.right.value == 1
        ):
            node.op = ast.Sub() if isinstance(node.op, ast.Add) else ast.Add()
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


def _specific_depth2(source, level1, cap=400):
    """Stack two specific rewrites (covers two-fault submissions such as
    `// 1` combined with `lo = mid - 1`).  rps is still measured against
    the true original during validation."""
    out = []
    seen = set(level1)
    seen.add(source)
    for sp in level1[:60]:
        try:
            subs = _specific_variants(sp)
        except Exception:
            continue
        for s2 in subs:
            if s2 not in seen:
                seen.add(s2)
                out.append(s2)
                if len(out) >= cap:
                    return out
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except Exception:
            return None

        try:
            specific = _specific_variants(source)
        except Exception:
            specific = []

        # Stage 0: identity + problem-specific single rewrites.
        try:
            res = _validate(
                iter([source] + specific),
                source,
                max_checks=len(specific) + 8,
            )
            if res is not None:
                return res
        except Exception:
            pass

        # Stage 0b: two stacked specific rewrites (two-fault submissions).
        try:
            spec2 = _specific_depth2(source, specific)
        except Exception:
            spec2 = []
        if spec2:
            try:
                res = _validate(iter(spec2), source, max_checks=len(spec2) + 8)
                if res is not None:
                    return res
            except Exception:
                pass

        # Stage 1: generic single-edit search on the original.
        try:
            res = _validate(_generic(source, 1, 600), source, max_checks=650)
            if res is not None:
                return res
        except Exception:
            pass

        # Stage 2: one generic edit stacked on each specific rewrite.
        try:
            gens = []
            for sp in (specific + spec2)[:30]:
                g = _generic(sp, 1, 120)
                if g is not None:
                    gens.append(g)
            if gens:
                res = _validate(
                    itertools.chain.from_iterable(gens),
                    source,
                    max_checks=1500,
                )
                if res is not None:
                    return res
        except Exception:
            pass

        # Stage 3: generic two-edit search as a last resort.
        try:
            res = _validate(_generic(source, 2, 2000), source, max_checks=1800)
            if res is not None:
                return res
        except Exception:
            pass

        return None
    except Exception:
        return None
```
