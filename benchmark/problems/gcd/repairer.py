"""Local, LLM-free automatic repair for the `gcd` assignment.

Strategy:
1. If the submission already passes, return it (validated via first_passing).
2. Try problem-specific AST rewrite rules targeting common gcd misconceptions:
   - wrong constant / wrong operator in a zero base-case guard
     (e.g. ``if b != 1: return a`` -> ``if b == 0: return a``),
   - swapped operands of ``%`` / ``-`` (e.g. ``b % a`` instead of ``a % b``),
   - a "one step only" Euclid that returns the remainder instead of recursing
     (``return remainder`` -> ``return gcd(b, remainder)``),
   - returning the wrong parameter in a base case.
3. Fall back to the generic single-edit search, then combinations of the
   above (two rule edits, rule edit + generic edit, two generic edits).

Every candidate is validated with `first_passing`, which enforces the full
visible test suite and the relative-patch-size cap (<= 0.35 vs the input).
"""

import ast

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "gcd"

TESTS = [
    {"args": [48, 18], "expected": 6},
    {"args": [18, 48], "expected": 6},
    {"args": [0, 5], "expected": 5},
    {"args": [5, 0], "expected": 5},
    {"args": [0, 0], "expected": 0},
    {"args": [7, 7], "expected": 7},
    {"args": [1, 999], "expected": 1},
    {"args": [12, 8], "expected": 4},
    {"args": [100, 75], "expected": 25},
    {"args": [13, 17], "expected": 1},
    {"args": [270, 192], "expected": 6},
    {"args": [1000000, 999999], "expected": 1},
    {"args": [36, 60], "expected": 12},
    {"args": [2, 4], "expected": 2},
]


def _param_names(tree):
    """Names of the first two parameters of the student's gcd (default a, b)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            names = [arg.arg for arg in node.args.args]
            if len(names) >= 2:
                return names[0], names[1]
    return "a", "b"


def _rule_variants(source):
    """Problem-specific single-edit candidate sources for this assignment."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    p0, p1 = _param_names(tree)
    base_nodes = list(ast.walk(tree))

    def fresh(index):
        t = ast.parse(source)
        return t, list(ast.walk(t))[index]

    mutations = []  # list of (node_index, mutator)

    def add(index, fn):
        mutations.append((index, fn))

    for i, node in enumerate(base_nodes):
        # Rule 1: comparisons against an integer constant -> canonical zero test.
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and len(node.comparators) == 1
            and isinstance(node.comparators[0], ast.Constant)
            and isinstance(node.comparators[0].value, int)
            and not isinstance(node.comparators[0].value, bool)
        ):
            def m_eq_zero(nd):
                nd.ops = [ast.Eq()]
                nd.comparators = [ast.Constant(0)]

            def m_ne_zero(nd):
                nd.ops = [ast.NotEq()]
                nd.comparators = [ast.Constant(0)]

            def m_const_zero(nd):
                nd.comparators = [ast.Constant(0)]

            def m_op_eq(nd):
                nd.ops = [ast.Eq()]

            def m_op_ne(nd):
                nd.ops = [ast.NotEq()]

            for fn in (m_eq_zero, m_ne_zero, m_const_zero, m_op_eq, m_op_ne):
                add(i, fn)

        # Rule 2: swapped operands of %, -, // (e.g. `b % a` for `a % b`).
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Mod, ast.Sub, ast.FloorDiv)
        ):
            def m_swap(nd):
                nd.left, nd.right = nd.right, nd.left

            add(i, m_swap)

        # Rule 3: missing recursion -- wrap a returned value in gcd(<param>, value).
        if (
            isinstance(node, ast.Return)
            and node.value is not None
            and isinstance(node.value, (ast.Name, ast.BinOp))
        ):
            def make_wrap(first_arg):
                def m(nd):
                    nd.value = ast.Call(
                        func=ast.Name(id=ENTRY, ctx=ast.Load()),
                        args=[ast.Name(id=first_arg, ctx=ast.Load()), nd.value],
                        keywords=[],
                    )
                return m

            add(i, make_wrap(p1))
            add(i, make_wrap(p0))

        # Rule 4: returning the wrong parameter.
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Name)
            and node.value.id in (p0, p1)
        ):
            other = p1 if node.value.id == p0 else p0

            def make_ret(name):
                def m(nd):
                    nd.value = ast.Name(id=name, ctx=ast.Load())
                return m

            add(i, make_ret(other))

    out, seen = [], {source}
    for index, fn in mutations:
        try:
            t2, nd2 = fresh(index)
            fn(nd2)
            ast.fix_missing_locations(t2)
            src2 = ast.unparse(t2)
        except Exception:
            continue
        if src2 not in seen:
            seen.add(src2)
            out.append(src2)
    return out


def _two_rule_variants(source, first_level, cap=250):
    """Compositions of two problem-specific rule edits."""
    out = []
    seen = {source}
    seen.update(first_level)
    for v in first_level:
        for w in _rule_variants(v):
            if w not in seen:
                seen.add(w)
                out.append(w)
                if len(out) >= cap:
                    return out
    return out


def repair(source: str) -> str | None:
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        try:
            ast.parse(source)
        except (SyntaxError, ValueError):
            return None

        # Quick sanity check that the code compiles/runs at all; if the module
        # itself cannot even be executed (e.g. no usable entry), still let the
        # search try, but bail out cleanly on library errors.
        try:
            failing_tests(source, ENTRY, TESTS)
        except Exception:
            pass

        # 0) Already correct? (validated, rps == 0)
        found = first_passing(iter([source]), ENTRY, TESTS, source)
        if found is not None:
            return found

        # 1) Problem-specific rewrite rules (single edit).
        rules = _rule_variants(source)
        found = first_passing(iter(rules), ENTRY, TESTS, source)
        if found is not None:
            return found

        # 2) Generic single-edit search.
        found = first_passing(
            candidates_generic(source, max_edits=1), ENTRY, TESTS, source
        )
        if found is not None:
            return found

        # 3) Two problem-specific rule edits.
        found = first_passing(
            iter(_two_rule_variants(source, rules)), ENTRY, TESTS, source
        )
        if found is not None:
            return found

        # 4) One rule edit followed by one generic edit.
        for variant in rules[:8]:
            found = first_passing(
                candidates_generic(variant, max_edits=1, budget=300),
                ENTRY,
                TESTS,
                source,
                max_checks=300,
            )
            if found is not None:
                return found

        # 5) Generic two-edit search.
        found = first_passing(
            candidates_generic(source, max_edits=2, budget=2000),
            ENTRY,
            TESTS,
            source,
        )
        return found
    except Exception:
        return None
