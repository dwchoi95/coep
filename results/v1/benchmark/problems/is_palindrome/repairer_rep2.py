"""Local, LLM-free automatic repair for the `is_palindrome(s)` assignment.

Strategy:
  1. Problem-specific AST rewrite rules targeting the misconceptions students
     typically have for this assignment (wrong filter predicate such as
     isalpha/isdigit, forgotten case fold, forgotten alnum filter, comparing
     the two halves without reversing, comparing against `reversed(t)`
     directly, wrong filter conditions inside build loops, etc.).
  2. The generic single-edit search from coep.repairlib.
  3. Combinations: two targeted rewrites, a targeted rewrite plus one generic
     edit, and finally pairs of generic edits.

Every candidate is validated through `first_passing`, which enforces the full
visible test suite and the relative-patch-size cap (<= 0.35), so any returned
program is a small edit of the student's own code.
"""

import ast

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain

ENTRY = "is_palindrome"

TESTS = [
    {"args": [""], "expected": True},
    {"args": ["a"], "expected": True},
    {"args": ["abba"], "expected": True},
    {"args": ["abc"], "expected": False},
    {"args": ["A man, a plan, a canal: Panama"], "expected": True},
    {"args": ["race a car"], "expected": False},
    {"args": ["No 'x' in Nixon"], "expected": True},
    {"args": ["12321"], "expected": True},
    {"args": ["1231"], "expected": False},
    {"args": ["!!!"], "expected": True},
    {"args": ["Aa"], "expected": True},
    {"args": ["0P"], "expected": False},
    {"args": ["Was it a car or a cat I saw?"], "expected": True},
    {"args": ["ab"], "expected": False},
]

# Wrong character-class predicates -> the correct one; wrong case fold names.
_ATTR_RENAMES = {
    "isalpha": "isalnum",
    "isdigit": "isalnum",
    "isspace": "isalnum",
    "isupper": "isalnum",
    "islower": "isalnum",
    "upper": "lower",
}


# ---------------------------------------------------------------------------
# Small AST helpers
# ---------------------------------------------------------------------------

def _parse_nodes(source):
    tree = ast.parse(source)
    return tree, list(ast.walk(tree))


def _unparse(tree):
    try:
        return ast.unparse(ast.fix_missing_locations(tree))
    except Exception:
        return None


def _lower_of(node):
    return ast.Call(
        func=ast.Attribute(value=node, attr="lower", ctx=ast.Load()),
        args=[],
        keywords=[],
    )


def _is_lower_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("lower", "casefold")
    )


def _rev_slice(node):
    # node[::-1]
    return ast.Subscript(
        value=node,
        slice=ast.Slice(
            lower=None,
            upper=None,
            step=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
        ),
        ctx=ast.Load(),
    )


def _isalnum_of(name):
    return ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=name, ctx=ast.Load()), attr="isalnum", ctx=ast.Load()
        ),
        args=[],
        keywords=[],
    )


def _is_isalnum_call(node, name):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "isalnum"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == name
    )


def _edit(source, idx, fn):
    """Re-parse source, apply fn to the idx-th node (ast.walk order) of the
    fresh tree, return the new source or None. fn returns True if it applied."""
    try:
        tree, nodes = _parse_nodes(source)
        if idx >= len(nodes) or not fn(nodes[idx]):
            return None
        return _unparse(tree)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Problem-specific candidate rewrites
# ---------------------------------------------------------------------------

def _specific_variants(source):
    out = []

    def add(src):
        if src is not None:
            out.append(src)

    try:
        _tree, nodes = _parse_nodes(source)
    except Exception:
        return []

    try:
        for idx, node in enumerate(nodes):
            # --- wrong predicate / wrong case-fold method name -------------
            if isinstance(node, ast.Attribute) and node.attr in _ATTR_RENAMES:
                def rn(m):
                    if isinstance(m, ast.Attribute) and m.attr in _ATTR_RENAMES:
                        m.attr = _ATTR_RENAMES[m.attr]
                        return True
                    return False

                add(_edit(source, idx, rn))

            # --- `not c.isspace()` style filters -> `c.isalnum()` ----------
            if (
                isinstance(node, ast.UnaryOp)
                and isinstance(node.op, ast.Not)
                and isinstance(node.operand, ast.Call)
                and isinstance(node.operand.func, ast.Attribute)
                and isinstance(node.operand.func.value, ast.Name)
            ):
                def notfix(m):
                    if not (
                        isinstance(m, ast.UnaryOp)
                        and isinstance(m.op, ast.Not)
                        and isinstance(m.operand, ast.Call)
                        and isinstance(m.operand.func, ast.Attribute)
                        and isinstance(m.operand.func.value, ast.Name)
                    ):
                        return False
                    m.op = ast.Not()  # keep structure valid; replace below
                    m.operand = _isalnum_of(m.operand.func.value.id)
                    return True

                # `not c.isalnum()` is almost never the intended filter, but
                # the candidate simply fails validation if wrong; also try the
                # positive form by rewriting the whole UnaryOp via its parent
                # is complex, so emit both this and the rename variants.
                add(_edit(source, idx, notfix))

            # --- comprehensions used to clean the string -------------------
            if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)) and node.generators:
                def low_elt(m):
                    if _is_lower_call(m.elt):
                        return False
                    m.elt = _lower_of(m.elt)
                    return True

                def low_iter(m):
                    if _is_lower_call(m.generators[0].iter):
                        return False
                    m.generators[0].iter = _lower_of(m.generators[0].iter)
                    return True

                def add_filter(m):
                    g = m.generators[0]
                    if g.ifs or not isinstance(g.target, ast.Name):
                        return False
                    g.ifs = [_isalnum_of(g.target.id)]
                    return True

                def replace_filter(m):
                    g = m.generators[0]
                    if not g.ifs or not isinstance(g.target, ast.Name):
                        return False
                    if len(g.ifs) == 1 and _is_isalnum_call(g.ifs[0], g.target.id):
                        return False
                    g.ifs = [_isalnum_of(g.target.id)]
                    return True

                add(_edit(source, idx, low_elt))
                add(_edit(source, idx, low_iter))
                add(_edit(source, idx, add_filter))
                add(_edit(source, idx, replace_filter))

            # --- equality comparisons (the palindrome check itself) --------
            if (
                isinstance(node, ast.Compare)
                and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
            ):
                def low_both(m):
                    m.left = _lower_of(m.left)
                    m.comparators[0] = _lower_of(m.comparators[0])
                    return True

                def rev_left(m):
                    m.left = _rev_slice(m.left)
                    return True

                def rev_right(m):
                    m.comparators[0] = _rev_slice(m.comparators[0])
                    return True

                add(_edit(source, idx, low_both))
                add(_edit(source, idx, rev_left))
                add(_edit(source, idx, rev_right))

                for side in (0, 1):
                    # `t[:half] == t[half:]` -> `t[:half] == t[::-1][:half]`
                    def suffix_fix(m, side=side):
                        t = m.left if side == 0 else m.comparators[0]
                        if not (
                            isinstance(t, ast.Subscript)
                            and isinstance(t.slice, ast.Slice)
                            and t.slice.lower is not None
                            and t.slice.upper is None
                            and t.slice.step is None
                        ):
                            return False
                        new = ast.Subscript(
                            value=_rev_slice(t.value),
                            slice=ast.Slice(lower=None, upper=t.slice.lower, step=None),
                            ctx=ast.Load(),
                        )
                        if side == 0:
                            m.left = new
                        else:
                            m.comparators[0] = new
                        return True

                    # `t == reversed(t)` -> `t == ''.join(reversed(t))`
                    def join_rev(m, side=side):
                        t = m.left if side == 0 else m.comparators[0]
                        if not (
                            isinstance(t, ast.Call)
                            and isinstance(t.func, ast.Name)
                            and t.func.id == "reversed"
                        ):
                            return False
                        new = ast.Call(
                            func=ast.Attribute(
                                value=ast.Constant(value=""), attr="join", ctx=ast.Load()
                            ),
                            args=[t],
                            keywords=[],
                        )
                        if side == 0:
                            m.left = new
                        else:
                            m.comparators[0] = new
                        return True

                    add(_edit(source, idx, suffix_fix))
                    add(_edit(source, idx, join_rev))

            # --- loop-based cleaning: fix filter ifs, add missing lower ----
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                for bi, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.If):
                        def if_fix(m, bi=bi):
                            if bi >= len(m.body):
                                return False
                            st = m.body[bi]
                            if not isinstance(st, ast.If):
                                return False
                            if not isinstance(m.target, ast.Name):
                                return False
                            if _is_isalnum_call(st.test, m.target.id):
                                return False
                            st.test = _isalnum_of(m.target.id)
                            return True

                        add(_edit(source, idx, if_fix))

            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                def aug_lower(m):
                    if _is_lower_call(m.value):
                        return False
                    m.value = _lower_of(m.value)
                    return True

                add(_edit(source, idx, aug_lower))

            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"
                and len(node.args) == 1
            ):
                def app_lower(m):
                    if _is_lower_call(m.args[0]):
                        return False
                    m.args[0] = _lower_of(m.args[0])
                    return True

                add(_edit(source, idx, app_lower))
    except Exception:
        pass

    # Deduplicate, drop no-ops.
    seen = {source}
    uniq = []
    for s2 in out:
        if s2 not in seen:
            seen.add(s2)
            uniq.append(s2)
    return uniq


# ---------------------------------------------------------------------------
# Safe iteration / deduplication helpers
# ---------------------------------------------------------------------------

def _safe_iter(factory):
    try:
        it = iter(factory())
    except Exception:
        return
    while True:
        try:
            item = next(it)
        except StopIteration:
            return
        except Exception:
            return
        if isinstance(item, str):
            yield item


def _dedup(cands, seen):
    for c in cands:
        if isinstance(c, str) and c not in seen:
            seen.add(c)
            yield c


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # If the submission already passes, return it (validated via first_passing).
    try:
        run = failing_tests(source, ENTRY, TESTS)
        if run is not None and getattr(run, "compiled", False) and run.passed == run.total:
            ok = first_passing(iter([source]), ENTRY, TESTS, source,
                               max_rps=0.35, max_checks=5)
            if ok is not None:
                return ok
    except Exception:
        pass

    seen = {source}
    specs = _specific_variants(source)

    # Pass 1: targeted problem-specific rewrites, then single generic edits.
    def _pass1():
        for sp in specs:
            yield sp
        for c in _safe_iter(lambda: candidates_generic(source, max_edits=1)):
            yield c

    fixed = first_passing(_dedup(_pass1(), seen), ENTRY, TESTS, source,
                          max_rps=0.35, max_checks=800)
    if fixed is not None:
        return fixed

    # Pass 2: pairs of targeted rewrites, and targeted rewrite + one generic edit.
    def _pass2():
        for sp in specs[:12]:
            for s2 in _specific_variants(sp):
                yield s2
        for sp in specs[:12]:
            for s2 in _safe_iter(lambda sp=sp: candidates_generic(sp, max_edits=1, budget=400)):
                yield s2

    fixed = first_passing(_dedup(_pass2(), seen), ENTRY, TESTS, source,
                          max_rps=0.35, max_checks=700)
    if fixed is not None:
        return fixed

    # Pass 3: pairs of generic edits (e.g. two off-by-one initializations).
    fixed = first_passing(
        _dedup(_safe_iter(lambda: candidates_generic(source, max_edits=2, budget=2000)), seen),
        ENTRY, TESTS, source, max_rps=0.35, max_checks=800,
    )
    return fixed
