"""Local, LLM-free automatic repair for the `flatten` assignment.

Strategy:
  1. Parse the submission (syntax errors -> None).
  2. Diagnose the failure pattern with `failing_tests` and reorder the
     problem-specific rewrite rules accordingly (wrong order -> stack/pop
     rules first, TypeError -> guarded-extend rules first, etc.).
  3. Generate candidates from problem-specific AST rewrite rules targeting
     the common misconceptions for THIS assignment:
       - swapped isinstance arguments (single site and all sites at once),
       - append/extend confusion,
       - missing recursion (shallow one-level flattening),
       - missing isinstance guard around extend,
       - inverted / negated isinstance tests, int<->list confusion,
       - any/all confusion, `if` instead of `while` for repeated passes,
       - sorting / deduplication of the result,
       - stack-order bugs (pop index, missing/extra reversed),
       - return placed inside the loop, missing/wrong return,
       - misuse of append's return value, `+` without assignment, etc.
  4. Chain with the generic mutation search (1 edit, then rule x rule
     compositions, then 2 generic edits).
  5. Every candidate is validated by `first_passing`, which enforces the
     full visible test suite and the rps <= 0.35 patch-size cap.
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

MAX_RPS = 0.35


# --------------------------------------------------------------------------
# small AST helpers
# --------------------------------------------------------------------------

def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _unparse(tree):
    try:
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:
        return None


def _name(i):
    return ast.Name(id=i, ctx=ast.Load())


def _call(fname, args):
    return ast.Call(func=_name(fname), args=list(args), keywords=[])


def _is_name(n, ids):
    return isinstance(n, ast.Name) and n.id in ids


def _is_call_named(n, names):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in names and len(n.args) == 1 and not n.keywords)


def _m_iso(n):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "isinstance" and len(n.args) == 2)


# --------------------------------------------------------------------------
# generic "apply rewrite at the n-th matching site" machinery
# --------------------------------------------------------------------------

def _apply_nth(source, match, rewrite, n):
    """Apply `rewrite` at the n-th matching node (DFS pre-order).
    n=None rewrites every matching site. Returns new source or None."""
    tree = _parse(source)
    if tree is None:
        return None
    state = {"i": 0, "done": False}

    class _T(ast.NodeTransformer):
        def visit(self, node):
            try:
                hit = bool(match(node))
            except Exception:
                hit = False
            if hit and not (n is not None and state["done"]):
                idx = state["i"]
                state["i"] += 1
                if n is None or idx == n:
                    try:
                        new = rewrite(node)
                    except Exception:
                        new = None
                    if new is not None:
                        state["done"] = True
                        return new
            return self.generic_visit(node)

    try:
        new_tree = _T().visit(tree)
    except Exception:
        return None
    if not state["done"]:
        return None
    return _unparse(new_tree)


def _count(source, match):
    tree = _parse(source)
    if tree is None:
        return 0
    c = 0
    for nd in ast.walk(tree):
        try:
            if match(nd):
                c += 1
        except Exception:
            pass
    return c


# --------------------------------------------------------------------------
# problem-specific rewrite rules
# --------------------------------------------------------------------------

def _r_iso_swap(n):
    n.args = [n.args[1], n.args[0]]
    return n


def _m_method_ae(n):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("append", "extend")
            and len(n.args) == 1 and not n.keywords)


def _r_toggle_ae(n):
    n.func.attr = "extend" if n.func.attr == "append" else "append"
    return n


def _m_wrap_arg(n):
    return _m_method_ae(n) and not _is_call_named(n.args[0], (ENTRY,))


def _r_wrap_arg(n):
    n.args = [_call(ENTRY, [n.args[0]])]
    return n


def _m_for(n):
    return isinstance(n, ast.For) and not _is_call_named(n.iter, (ENTRY,))


def _r_wrap_iter(n):
    n.iter = _call(ENTRY, [n.iter])
    return n


def _m_entry_call(n):
    return _is_call_named(n, (ENTRY,))


def _r_unwrap_call(n):
    return n.args[0]


def _m_expr_ae(n):
    return isinstance(n, ast.Expr) and _m_method_ae(n.value)


def _r_guard_extend(n):
    call = n.value
    e = call.args[0]
    if isinstance(e, ast.IfExp) or _is_call_named(e, (ENTRY,)):
        return None
    call.func.attr = "extend"
    call.args = [ast.IfExp(
        test=_call("isinstance", [copy.deepcopy(e), _name("list")]),
        body=_call(ENTRY, [copy.deepcopy(e)]),
        orelse=ast.List(elts=[e], ctx=ast.Load()),
    )]
    return n


def _m_iso_type(n):
    return _m_iso(n) and _is_name(n.args[1], ("int", "list"))


def _r_iso_type(n):
    n.args[1].id = "list" if n.args[1].id == "int" else "int"
    return n


def _m_test_holder(n):
    return isinstance(n, (ast.If, ast.While, ast.IfExp))


def _r_toggle_not(n):
    t = n.test
    if isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not):
        n.test = t.operand
        return n
    if _m_iso(t):
        n.test = ast.UnaryOp(op=ast.Not(), operand=t)
        return n
    return None


def _m_if_full(n):
    return isinstance(n, ast.If) and n.body and n.orelse


def _r_swap_branches(n):
    n.body, n.orelse = n.orelse, n.body
    return n


def _m_anyall(n):
    return _is_call_named(n, ("any", "all"))


def _r_anyall(n):
    n.func.id = "all" if n.func.id == "any" else "any"
    return n


def _m_sorted_set(n):
    return _is_call_named(n, ("sorted", "set"))


def _m_sort_stmt(n):
    return (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and n.value.func.attr in ("sort", "reverse")
            and not n.value.args and not n.value.keywords)


def _r_drop_stmt(n):
    return ast.Pass()


def _m_pop(n):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "pop" and not n.keywords
            and (not n.args or (len(n.args) == 1
                                and isinstance(n.args[0], ast.Constant)
                                and n.args[0].value == 0)))


def _r_pop(n):
    n.args = [] if n.args else [ast.Constant(value=0)]
    return n


def _m_rev(n):
    return _is_call_named(n, ("reversed",))


def _m_ext_norev(n):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "extend" and len(n.args) == 1
            and not n.keywords
            and not _is_call_named(n.args[0], ("reversed",)))


def _r_wrap_rev(n):
    n.args = [_call("reversed", [n.args[0]])]
    return n


def _m_list_call(n):
    return _is_call_named(n, ("list",)) and not _is_call_named(n.args[0], ("reversed",))


def _r_list_rev(n):
    n.args = [_call("reversed", [n.args[0]])]
    return n


def _m_if_noelse(n):
    return isinstance(n, ast.If) and not n.orelse


def _r_if_to_while(n):
    # only convert the "repeated passes" shape: test uses any/all and the
    # body reassigns a name that occurs in the test (progress guarantee)
    has_anyall = any(_is_call_named(x, ("any", "all")) for x in ast.walk(n.test))
    if not has_anyall:
        return None
    test_names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
    assigned = set()
    for st in n.body:
        for x in ast.walk(st):
            if isinstance(x, ast.Assign):
                for t in x.targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
    if not (test_names & assigned):
        return None
    return ast.While(test=n.test, body=n.body, orelse=[])


def _m_loop_ret(n):
    return (isinstance(n, (ast.For, ast.While)) and n.body
            and isinstance(n.body[-1], ast.Return))


def _r_hoist(n):
    ret = n.body[-1]
    n.body = n.body[:-1] if len(n.body) > 1 else [ast.Pass()]
    return [n, ret]


def _m_fn_noret(n):
    return (isinstance(n, ast.FunctionDef) and n.name == ENTRY
            and not any(isinstance(x, ast.Return) for x in ast.walk(n)))


def _r_add_return(n):
    accs = [st.targets[0].id for st in n.body
            if isinstance(st, ast.Assign) and len(st.targets) == 1
            and isinstance(st.targets[0], ast.Name)
            and isinstance(st.value, ast.List)]
    if not accs:
        return None
    n.body = list(n.body) + [ast.Return(value=_name(accs[0]))]
    return n


def _m_none_init(n):
    return (isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and isinstance(n.value, ast.Constant) and n.value.value is None)


def _r_none_init(n):
    n.value = ast.List(elts=[], ctx=ast.Load())
    return n


def _m_assign_mut(n):
    return (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and n.value.func.attr in ("append", "extend"))


def _r_drop_assign(n):
    return ast.Expr(value=n.value)


def _m_expr_bin(n):
    return (isinstance(n, ast.Expr) and isinstance(n.value, ast.BinOp)
            and isinstance(n.value.op, ast.Add)
            and isinstance(n.value.left, ast.Name))


def _r_expr_aug(n):
    return ast.AugAssign(target=ast.Name(id=n.value.left.id, ctx=ast.Store()),
                         op=ast.Add(), value=n.value.right)


def _m_aug_add(n):
    return isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add)


def _r_aug_listwrap(n):
    if isinstance(n.value, ast.List):
        return None
    n.value = ast.List(elts=[n.value], ctx=ast.Load())
    return n


def _r_aug_flat(n):
    if _is_call_named(n.value, (ENTRY,)):
        return None
    n.value = _call(ENTRY, [n.value])
    return n


def _r_aug_unwrap(n):
    if isinstance(n.value, ast.List) and len(n.value.elts) == 1:
        n.value = n.value.elts[0]
        return n
    return None


def _m_ret_val(n):
    return (isinstance(n, ast.Return) and n.value is not None
            and not isinstance(n.value, ast.List))


def _r_ret_wrap(n):
    n.value = ast.List(elts=[n.value], ctx=ast.Load())
    return n


def _m_ret_list1(n):
    return (isinstance(n, ast.Return) and isinstance(n.value, ast.List)
            and len(n.value.elts) == 1)


def _r_ret_unwrap(n):
    n.value = n.value.elts[0]
    return n


_STATIC_RULES = [
    ("iso_swap", _m_iso, _r_iso_swap, True),
    ("toggle_ae", _m_method_ae, _r_toggle_ae, False),
    ("wrap_arg", _m_wrap_arg, _r_wrap_arg, False),
    ("wrap_iter", _m_for, _r_wrap_iter, False),
    ("unwrap_flat", _m_entry_call, _r_unwrap_call, False),
    ("guard_extend", _m_expr_ae, _r_guard_extend, False),
    ("iso_type", _m_iso_type, _r_iso_type, False),
    ("toggle_not", _m_test_holder, _r_toggle_not, False),
    ("swap_branches", _m_if_full, _r_swap_branches, False),
    ("any_all", _m_anyall, _r_anyall, False),
    ("sorted_unwrap", _m_sorted_set, _r_unwrap_call, False),
    ("drop_sort_stmt", _m_sort_stmt, _r_drop_stmt, False),
    ("pop_toggle", _m_pop, _r_pop, False),
    ("rev_unwrap", _m_rev, _r_unwrap_call, False),
    ("rev_wrap_extend", _m_ext_norev, _r_wrap_rev, False),
    ("list_rev", _m_list_call, _r_list_rev, False),
    ("if_to_while", _m_if_noelse, _r_if_to_while, False),
    ("hoist_return", _m_loop_ret, _r_hoist, False),
    ("add_return", _m_fn_noret, _r_add_return, False),
    ("none_init", _m_none_init, _r_none_init, False),
    ("drop_assign", _m_assign_mut, _r_drop_assign, False),
    ("expr_aug", _m_expr_bin, _r_expr_aug, False),
    ("aug_list", _m_aug_add, _r_aug_listwrap, False),
    ("aug_flat", _m_aug_add, _r_aug_flat, False),
    ("aug_unwrap", _m_aug_add, _r_aug_unwrap, False),
    ("ret_wrap_list", _m_ret_val, _r_ret_wrap, False),
    ("ret_unwrap_list", _m_ret_list1, _r_ret_unwrap, False),
]


def _rules_for(source):
    """Static rules plus context-dependent return-fix rules."""
    rules = list(_STATIC_RULES)
    accs = []
    tree = _parse(source)
    if tree is not None:
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.List)
                    and not node.value.elts):
                accs.append(node.targets[0].id)
    if accs:
        acc = accs[0]

        def m_bare(n):
            return isinstance(n, ast.Return) and (
                n.value is None
                or (isinstance(n.value, ast.Constant) and n.value.value is None))

        def r_bare(n):
            n.value = _name(acc)
            return n

        def m_wrongret(n):
            return (isinstance(n, ast.Return) and isinstance(n.value, ast.Name)
                    and n.value.id != acc)

        def r_wrongret(n):
            n.value = _name(acc)
            return n

        rules.append(("bare_return", m_bare, r_bare, False))
        rules.append(("fix_return_name", m_wrongret, r_wrongret, False))
    return rules


def _specific_candidates(source, order=None):
    """Yield candidate sources from the problem-specific rules."""
    rules = _rules_for(source)
    if order:
        pri = {name: i for i, name in enumerate(order)}
        rules.sort(key=lambda r: pri.get(r[0], len(order) + 1))
    seen = {source}
    for _nm, m, r, allflag in rules:
        try:
            total = min(_count(source, m), 12)
            targets = ([None] if (allflag and total > 1) else []) + list(range(total))
            for t in targets:
                s = _apply_nth(source, m, r, t)
                if s and s not in seen:
                    seen.add(s)
                    yield s
        except Exception:
            continue


def _level2(source, bases, cap=300):
    """Compose two specific rules (rule applied on a level-1 candidate)."""
    seen = set(bases)
    seen.add(source)
    produced = 0
    for b in bases[:50]:
        try:
            for c in _specific_candidates(b):
                if c in seen:
                    continue
                seen.add(c)
                yield c
                produced += 1
                if produced >= cap:
                    return
        except Exception:
            continue


# --------------------------------------------------------------------------
# failure-pattern dispatch
# --------------------------------------------------------------------------

def _get(f, k):
    try:
        return f.get(k)
    except Exception:
        return getattr(f, k, None)


def _dispatch_order(source):
    """Inspect the failing tests and return a priority prefix of rule names."""
    try:
        res = failing_tests(source, ENTRY, TESTS)
        fails = list(getattr(res, "failures", []) or [])
    except Exception:
        return None
    wrong_order = type_err = shallow = sorted_like = False
    for f in fails:
        got = _get(f, "got")
        exp = _get(f, "expected")
        err = _get(f, "error")
        if err:
            es = str(err)
            if "iterable" in es or "TypeError" in es:
                type_err = True
        if isinstance(got, list) and isinstance(exp, list):
            if len(exp) > 1 and got == list(reversed(exp)):
                wrong_order = True
            if any(isinstance(x, list) for x in got):
                shallow = True
            try:
                if got != exp and got == sorted(exp):
                    sorted_like = True
            except Exception:
                pass
    if wrong_order:
        return ["pop_toggle", "rev_unwrap", "rev_wrap_extend", "list_rev",
                "iso_swap"]
    if sorted_like:
        return ["sorted_unwrap", "drop_sort_stmt", "iso_swap"]
    if type_err:
        return ["guard_extend", "wrap_arg", "toggle_ae", "iso_swap",
                "swap_branches", "toggle_not"]
    if shallow:
        return ["wrap_arg", "wrap_iter", "toggle_ae", "iso_swap",
                "if_to_while", "any_all"]
    return None


# --------------------------------------------------------------------------
# main entry point
# --------------------------------------------------------------------------

def _validate(gen, source, max_checks):
    try:
        fix = first_passing(gen, ENTRY, TESTS, source,
                            max_rps=MAX_RPS, max_checks=max_checks)
    except Exception:
        return None
    if fix is None:
        return None
    try:
        if rps(source, fix) > MAX_RPS:
            return None
    except Exception:
        pass
    return fix


def _repair_impl(source):
    if not isinstance(source, str):
        return None
    if _parse(source) is None:
        return None

    order = _dispatch_order(source)
    try:
        level1 = list(itertools.islice(_specific_candidates(source, order), 250))
    except Exception:
        level1 = []

    # stage 1: original (in case it already passes) + targeted rewrites
    try:
        stage1 = chain(iter([source]), iter(level1))
    except Exception:
        stage1 = itertools.chain(iter([source]), iter(level1))
    fix = _validate(stage1, source, 260)
    if fix is not None:
        return fix

    # stage 2: generic single-edit search
    def _gen1():
        try:
            for c in candidates_generic(source, max_edits=1, budget=800):
                yield c
        except Exception:
            return

    fix = _validate(_gen1(), source, 450)
    if fix is not None:
        return fix

    # stage 3: compositions of two targeted rewrites
    fix = _validate(_level2(source, level1), source, 260)
    if fix is not None:
        return fix

    # stage 4: generic two-edit search
    def _gen2():
        try:
            for c in candidates_generic(source, max_edits=2, budget=2000):
                yield c
        except Exception:
            return

    return _validate(_gen2(), source, 550)


def repair(source: str) -> str | None:
    try:
        return _repair_impl(source)
    except Exception:
        return None
