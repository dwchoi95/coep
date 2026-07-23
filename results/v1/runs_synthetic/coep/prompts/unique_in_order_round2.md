You previously wrote the following per-assignment repair module for the assignment "unique_in_order":

```python
"""Local, LLM-free automatic repair for the `unique_in_order` assignment.

Combines problem-specific AST rewrite rules (wrong initialization, missing
first-element/empty guards, membership-instead-of-adjacency checks, wrong
list variable in subscripts/returns) with the generic mutation search from
coep.repairlib, dispatching lightly on the observed failure pattern.
"""

import ast

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401  (available for completeness)

ENTRY = "unique_in_order"

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1]], "expected": [1]},
    {"args": [[1, 1]], "expected": [1]},
    {"args": [[1, 1, 2, 1]], "expected": [1, 2, 1]},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 1, 1, 1]], "expected": [1]},
    {"args": [["a", "a", "b", "b", "a"]], "expected": ["a", "b", "a"]},
    {"args": [[1, "1", 1]], "expected": [1, "1", 1]},
    {"args": [[2, 2, 2, 3, 3, 1, 1, 2]], "expected": [2, 3, 1, 2]},
    {"args": [["A", "a", "A"]], "expected": ["A", "a", "A"]},
    {"args": [[0, 0, 0]], "expected": [0]},
    {"args": [[5, 4, 4, 5, 5, 4]], "expected": [5, 4, 5, 4]},
    {"args": [["x"]], "expected": ["x"]},
    {"args": [[1, 2, 2, 3, 3, 3, 4]], "expected": [1, 2, 3, 4]},
]


# ---------------------------------------------------------------------------
# Small AST helpers
# ---------------------------------------------------------------------------

def _name(n):
    return ast.Name(id=n, ctx=ast.Load())


def _last(n):
    # <n>[-1]
    return ast.Subscript(
        value=_name(n),
        slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
        ctx=ast.Load(),
    )


def _is_empty_list_value(v):
    if isinstance(v, ast.List) and not v.elts:
        return True
    if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
            and v.func.id == "list" and not v.args and not v.keywords):
        return True
    return False


def _nth_variant(source, predicate, replace, n):
    """Re-parse `source`, apply `replace` to the n-th node matching
    `predicate` (in traversal order), return the new source string."""
    tree = ast.parse(source)
    counter = [0]

    class T(ast.NodeTransformer):
        def visit(self, node):
            node = self.generic_visit(node)
            try:
                hit = predicate(node)
            except Exception:
                hit = False
            if hit:
                idx = counter[0]
                counter[0] += 1
                if idx == n:
                    try:
                        new = replace(node)
                    except Exception:
                        new = None
                    if new is not None:
                        return new
            return node

    new_tree = T().visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules
# ---------------------------------------------------------------------------

def _specific_variants(source, prioritize_guards=False):
    """Enumerate problem-specific single-rewrite candidate sources."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            func = node
            break
    if func is None:
        return []

    param = func.args.args[0].arg if func.args.args else None

    # Accumulator variables: names assigned an empty list inside the function.
    accs = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and _is_empty_list_value(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    accs.append(t.id)
    accs = list(dict.fromkeys(accs))

    # Simple loop-index names (for i in ...).
    idx_names = list(dict.fromkeys(
        node.target.id for node in ast.walk(func)
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name)))

    list_names = list(dict.fromkeys(accs + ([param] if param else [])))

    guards, others = [], []

    def add(bucket, pred, rep, max_sites=8):
        try:
            n_sites = sum(1 for x in ast.walk(tree) if _safe(pred, x))
        except Exception:
            return
        for i in range(min(n_sites, max_sites)):
            try:
                src = _nth_variant(source, pred, rep, i)
            except Exception:
                continue
            if src and src != source:
                bucket.append(src)

    def _safe(pred, x):
        try:
            return bool(pred(x))
        except Exception:
            return False

    # --- Rule 1: wrong initialization `acc = []` -> `acc = param[:1]`
    # (fixes loops that start at index 1 and therefore drop the first element)
    if param:
        def pred_init(node):
            return isinstance(node, ast.Assign) and _is_empty_list_value(node.value)

        def rep_init(node, p=param):
            node.value = ast.Subscript(
                value=_name(p),
                slice=ast.Slice(lower=None, upper=ast.Constant(1), step=None),
                ctx=ast.Load(),
            )
            return node

        add(others, pred_init, rep_init)

    # --- Rule 2: missing emptiness / first-iteration guards on `if` tests
    def pred_if(node):
        return isinstance(node, ast.If)

    for acc in accs:
        def rep_or_not(node, a=acc):
            node.test = ast.BoolOp(
                op=ast.Or(),
                values=[ast.UnaryOp(op=ast.Not(), operand=_name(a)), node.test])
            return node

        def rep_and(node, a=acc):
            node.test = ast.BoolOp(op=ast.And(), values=[_name(a), node.test])
            return node

        add(guards, pred_if, rep_or_not)
        add(guards, pred_if, rep_and)

    for iname in idx_names:
        def rep_or_zero(node, i=iname):
            node.test = ast.BoolOp(
                op=ast.Or(),
                values=[ast.Compare(left=_name(i), ops=[ast.Eq()],
                                    comparators=[ast.Constant(0)]),
                        node.test])
            return node

        def rep_and_idx(node, i=iname):
            node.test = ast.BoolOp(op=ast.And(), values=[_name(i), node.test])
            return node

        add(guards, pred_if, rep_or_zero)
        add(guards, pred_if, rep_and_idx)

    # --- Rule 3: missing `i == 0 or` guard in a comprehension filter
    def pred_comp(node):
        return (isinstance(node, ast.comprehension) and node.ifs
                and isinstance(node.target, ast.Name))

    def rep_comp(node):
        tgt = node.target.id
        node.ifs = [ast.BoolOp(
            op=ast.Or(),
            values=[ast.Compare(left=_name(tgt), ops=[ast.Eq()],
                                comparators=[ast.Constant(0)]),
                    node.ifs[0]])] + node.ifs[1:]
        return node

    add(others, pred_comp, rep_comp)

    # --- Rule 4: membership test (removes ALL duplicates) -> adjacency test
    if accs:
        def pred_member(node):
            return (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], (ast.In, ast.NotIn))
                    and isinstance(node.comparators[0], ast.Name)
                    and node.comparators[0].id in accs)

        def rep_member(node):
            a = node.comparators[0].id
            if isinstance(node.ops[0], ast.NotIn):
                # x not in acc  ->  not acc or acc[-1] != x
                return ast.BoolOp(
                    op=ast.Or(),
                    values=[ast.UnaryOp(op=ast.Not(), operand=_name(a)),
                            ast.Compare(left=_last(a), ops=[ast.NotEq()],
                                        comparators=[node.left])])
            # x in acc  ->  acc and acc[-1] == x
            return ast.BoolOp(
                op=ast.And(),
                values=[_name(a),
                        ast.Compare(left=_last(a), ops=[ast.Eq()],
                                    comparators=[node.left])])

        add(others, pred_member, rep_member)

    # --- Rule 5: wrong list variable in a subscript (e.g. lst[-1] vs result[-1])
    if len(list_names) >= 2:
        def pred_sub(node):
            return (isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in list_names)

        for other in list_names:
            def rep_sub(node, o=other):
                if node.value.id == o:
                    return None
                node.value = _name(o)
                return node

            add(others, pred_sub, rep_sub)

        # --- Rule 6: returning the wrong variable
        def pred_ret(node):
            return (isinstance(node, ast.Return)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in list_names)

        for other in list_names:
            def rep_ret(node, o=other):
                if node.value.id == o:
                    return None
                node.value = _name(o)
                return node

            add(others, pred_ret, rep_ret)

    ordered = (guards + others) if prioritize_guards else (others + guards)
    return list(dict.fromkeys(ordered))


# ---------------------------------------------------------------------------
# Candidate assembly and repair entry point
# ---------------------------------------------------------------------------

def _dedup(it):
    seen = set()
    for c in it:
        if isinstance(c, str) and c not in seen:
            seen.add(c)
            yield c


def _safe_generic(src, max_edits, budget):
    try:
        for c in candidates_generic(src, max_edits=max_edits, budget=budget):
            yield c
    except Exception:
        return


def _combo(spec_variants):
    # One problem-specific rewrite followed by one generic edit.
    for s in spec_variants[:10]:
        try:
            for c in candidates_generic(s, max_edits=1, budget=120):
                yield c
        except Exception:
            continue


def repair(source: str) -> "str | None":
    try:
        if not isinstance(source, str):
            return None
        try:
            ast.parse(source)
        except SyntaxError:
            return None
        except Exception:
            return None

        # Light dispatch on the observed failure pattern: runtime IndexErrors
        # usually mean a missing emptiness/first-iteration guard, so try the
        # guard rewrites first in that case.
        prioritize_guards = False
        try:
            run = failing_tests(source, ENTRY, TESTS)
            if run.compiled and run.failures:
                prioritize_guards = any(
                    "IndexError" in str(f) for f in run.failures)
        except Exception:
            pass

        spec = _specific_variants(source, prioritize_guards)

        candidates = chain(
            iter([source]),                      # already-correct submissions
            iter(spec),                          # problem-specific rewrites
            _safe_generic(source, 1, 600),       # single generic edits
            _safe_generic(source, 2, 1200),      # pairs of generic edits
            _combo(spec),                        # specific rewrite + generic edit
        )

        return first_passing(
            _dedup(candidates), ENTRY, TESTS, source,
            max_rps=0.35, max_checks=1500)
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: NOT REPAIRED — no_patch
- crafted_09.py: NOT REPAIRED — no_patch
- mutant_02.py: NOT REPAIRED — no_patch
- mutant_06.py: NOT REPAIRED — no_patch
- mutant_14.py: NOT REPAIRED — no_patch

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
