```python
"""Local, LLM-free automatic repair for the `remove_extras` (duplicate
elimination) assignment.

Strategy: combine problem-specific AST rewrite rules targeting the common
misconceptions for this task (mutating the list while iterating over it,
`list.reverse()`/`list.sort()` returning None, tuple accumulators, missing
or mis-indented final `return`, `set()` destroying order, off-by-one slices,
missing `break` in pair-counting loops, ...) with the generic semantic-edit
search from `coep.repairlib`.  Every candidate is pre-screened locally under
a step-limited sandbox and finally validated with `first_passing`, which
enforces the visible test suite and the 0.35 relative-patch-size cap.
"""

import ast
import contextlib
import copy
import io
import re
import sys
import textwrap
import time
from itertools import islice

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "remove_extras"

TESTS = [
    {"args": [[1, 1, 1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 5, 1, 1, 3, 2]], "expected": [1, 5, 3, 2]},
    {"args": [[]], "expected": []},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
    {"args": [[3, 4, 5, 1, 3]], "expected": [3, 4, 5, 1]},
]

MAX_RPS = 0.35
_STEP_LIMIT = 30000
_TIME_BUDGET = 8.0


# --------------------------------------------------------------------------
# Sandboxed pre-screening (protects against infinite loops / input() / etc.)
# --------------------------------------------------------------------------

class _StepLimit(Exception):
    pass


def _fake_input(*_args, **_kwargs):
    raise EOFError("input() is not available")


def _run_limited(thunk, max_steps=_STEP_LIMIT):
    steps = [0]

    def tracer(frame, event, arg):
        steps[0] += 1
        if steps[0] > max_steps:
            raise _StepLimit()
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return thunk()
    finally:
        sys.settrace(old)


def _passes_all(src):
    """Run the candidate against all TESTS in a step-limited sandbox."""
    try:
        code = compile(src, "<candidate>", "exec")
    except BaseException:
        return False
    glb = {"__name__": "__candidate__", "input": _fake_input}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            _run_limited(lambda: exec(code, glb))
            fn = glb.get(ENTRY)
            if not callable(fn):
                return False
            for t in TESTS:
                args = copy.deepcopy(t["args"])
                res = _run_limited(lambda: fn(*args))
                if res != t["expected"]:
                    return False
    except BaseException:
        return False
    return True


def _rps_ok(original, cand):
    try:
        return rps(original, cand) <= MAX_RPS
    except Exception:
        return True  # let first_passing be the judge


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _unparse(tree):
    try:
        ast.fix_missing_locations(tree)
        out = ast.unparse(tree)
        ast.parse(out)  # sanity check
        return out
    except Exception:
        return None


def _func(tree):
    if tree is None:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            return node
    return None


def _stmt_sites(root, pred):
    """Deterministically enumerate (block, index, loop_depth) statement sites."""
    sites = []

    def rec(node, depth):
        for field in ("body", "orelse", "finalbody"):
            blk = getattr(node, field, None)
            if isinstance(blk, list):
                for i, st in enumerate(blk):
                    if not isinstance(st, ast.stmt):
                        continue
                    if pred(st, depth):
                        sites.append((blk, i, depth))
                    rec(st, depth + (1 if isinstance(st, (ast.For, ast.While)) else 0))

    rec(root, 0)
    return sites


# --------------------------------------------------------------------------
# Problem-specific rewrite rules.  Each rule: source -> list of variant sources.
# --------------------------------------------------------------------------

def r_strip_toplevel(src):
    """Drop stray top-level statements (test calls, input(), prints...)."""
    tree = _parse(src)
    if tree is None:
        return []
    keep = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
            ast.Import, ast.ImportFrom)
    kept = [s for s in tree.body if isinstance(s, keep)]
    if len(kept) == len(tree.body) or not kept:
        return []
    tree.body = kept
    s = _unparse(tree)
    return [s] if s else []


def r_return_missing(src):
    """Append `return <var>` when the function can fall off the end."""
    tree = _parse(src)
    f = _func(tree)
    if f is None or not f.body:
        return []
    if isinstance(f.body[-1], ast.Return):
        return []
    names = []
    for node in ast.walk(f):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id not in names:
                    names.append(t.id)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            if node.target.id not in names:
                names.append(node.target.id)
    for a in f.args.args:
        if a.arg not in names:
            names.append(a.arg)
    out = []
    for n in names[:5]:
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        f2.body.append(ast.Return(value=ast.Name(id=n, ctx=ast.Load())))
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_return_move(src):
    """Move a `return` that sits inside a loop down to the end of the function
    (classic mis-indentation bug)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    pred = lambda st, d: isinstance(st, ast.Return) and d >= 1
    n = len(_stmt_sites(f, pred))
    out = []
    for k in range(min(n, 6)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        sites = _stmt_sites(f2, pred)
        if k >= len(sites):
            continue
        blk, i, _d = sites[k]
        ret = blk.pop(i)
        if not blk:
            blk.append(ast.Pass())
        if f2.body and isinstance(f2.body[-1], ast.Return):
            continue
        f2.body.append(ret)
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_print_to_return(src):
    """Replace a trailing `print(x)` with `return x`."""
    tree = _parse(src)
    f = _func(tree)
    if f is None or not f.body:
        return []
    last = f.body[-1]
    if (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name)
            and last.value.func.id == "print" and len(last.value.args) == 1):
        f.body[-1] = ast.Return(value=last.value.args[0])
        s = _unparse(tree)
        return [s] if s else []
    return []


def r_reverse_none_fix(src):
    """`x = y.reverse()` -> `x = y[::-1]`, `return y.reverse()` -> `return y[::-1]`,
    `x = y.sort()` -> `x = sorted(y)` (list methods return None)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    changed = [False]

    def fix_call(call):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and not call.args and not call.keywords):
            base = call.func.value
            if call.func.attr == "reverse":
                changed[0] = True
                return ast.Subscript(
                    value=base,
                    slice=ast.Slice(lower=None, upper=None,
                                    step=ast.UnaryOp(op=ast.USub(),
                                                     operand=ast.Constant(1))),
                    ctx=ast.Load())
            if call.func.attr == "sort":
                changed[0] = True
                return ast.Call(func=ast.Name(id="sorted", ctx=ast.Load()),
                                args=[base], keywords=[])
        return None

    class T(ast.NodeTransformer):
        def visit_Assign(self, node):
            self.generic_visit(node)
            new = fix_call(node.value)
            if new is not None:
                node.value = new
            return node

        def visit_Return(self, node):
            self.generic_visit(node)
            if node.value is not None:
                new = fix_call(node.value)
                if new is not None:
                    node.value = new
            return node

    T().visit(f)
    if not changed[0]:
        return []
    s = _unparse(tree)
    return [s] if s else []


def r_tuple_acc(src):
    """Turn a tuple accumulator (`a = ()`, `a += (x,)` / `a += x`) into a list
    accumulator (`a = []`, `a += [x]`)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    tuple_vars = set()
    for node in ast.walk(f):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple)
                and not node.value.elts):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    tuple_vars.add(t.id)
    if not tuple_vars:
        return []

    def as_list(v):
        if isinstance(v, ast.Tuple):
            return ast.List(elts=list(v.elts), ctx=ast.Load())
        if isinstance(v, ast.List):
            return v
        return ast.List(elts=[v], ctx=ast.Load())

    for node in ast.walk(f):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple)
                and not node.value.elts):
            node.value = ast.List(elts=[], ctx=ast.Load())
        elif (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                and node.target.id in tuple_vars and isinstance(node.op, ast.Add)):
            node.value = as_list(node.value)
        elif (isinstance(node, ast.Assign) and node.targets
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in tuple_vars
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.Add)):
            node.value.right = as_list(node.value.right)
    s = _unparse(tree)
    return [s] if s else []


def r_set_fix(src):
    """`set(x)` -> `dict.fromkeys(x)` (order-preserving dedup)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    changed = [False]

    class T(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if (isinstance(node.func, ast.Name) and node.func.id == "set"
                    and len(node.args) == 1 and not node.keywords):
                changed[0] = True
                return ast.Call(
                    func=ast.Attribute(value=ast.Name(id="dict", ctx=ast.Load()),
                                       attr="fromkeys", ctx=ast.Load()),
                    args=node.args, keywords=[])
            return node

    T().visit(f)
    if not changed[0]:
        return []
    s = _unparse(tree)
    return [s] if s else []


def r_reverse_wrap(src):
    """For remove/pop-based approaches that keep the LAST occurrence: reverse
    the list first and reverse back before returning, so the FIRST occurrence
    is kept."""
    tree = _parse(src)
    f = _func(tree)
    if f is None or not f.args.args or not f.body:
        return []
    p = f.args.args[0].arg
    has_mut = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in ("remove", "pop")
                  for n in ast.walk(f))
    if not has_mut:
        return []

    def rev_stmt(name):
        return ast.Expr(value=ast.Call(
            func=ast.Attribute(value=ast.Name(id=name, ctx=ast.Load()),
                               attr="reverse", ctx=ast.Load()),
            args=[], keywords=[]))

    class T(ast.NodeTransformer):
        def visit_Return(self, node):
            if isinstance(node.value, ast.Name):
                return [rev_stmt(node.value.id), node]
            return node

    T().visit(f)
    f.body.insert(0, rev_stmt(p))
    s = _unparse(tree)
    return [s] if s else []


def r_iter_copy(src):
    """`for x in lst:` -> `for x in lst[:]:` (iterating a list being mutated)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def fors(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)]

    n = len(fors(f))
    out = []
    for k in range(min(n, 6)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        sites = fors(f2)
        if k >= len(sites):
            continue
        node = sites[k]
        name = node.iter.id
        node.iter = ast.Subscript(
            value=ast.Name(id=name, ctx=ast.Load()),
            slice=ast.Slice(lower=None, upper=None, step=None),
            ctx=ast.Load())
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def _swap_loops(src, from_if):
    """Swap a single `if` <-> `while` (e.g. `if lst.count(x)>1` should loop)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    kind = ast.If if from_if else ast.While
    n = sum(1 for x in ast.walk(f) if isinstance(x, kind))
    out = []
    for k in range(min(n, 6)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        cnt = [-1]

        class T(ast.NodeTransformer):
            def visit_If(self, node):
                self.generic_visit(node)
                if from_if:
                    cnt[0] += 1
                    if cnt[0] == k:
                        return ast.While(test=node.test, body=node.body,
                                         orelse=node.orelse)
                return node

            def visit_While(self, node):
                self.generic_visit(node)
                if not from_if:
                    cnt[0] += 1
                    if cnt[0] == k:
                        return ast.If(test=node.test, body=node.body,
                                      orelse=node.orelse)
                return node

        T().visit(f2)
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_if_to_while(src):
    return _swap_loops(src, True)


def r_while_to_if(src):
    return _swap_loops(src, False)


def r_slice_variants(src):
    """Slice boundary fixes: drop the slice (`a[:-1]` -> `a`), drop the upper
    bound, drop the lower bound."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def subs(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
                and isinstance(getattr(n, "ctx", None), ast.Load)
                and (n.slice.lower is not None or n.slice.upper is not None)]

    n = len(subs(f))
    out = []
    for k in range(min(n, 8)):
        for mode in ("drop", "noupper", "nolower"):
            t2 = _parse(src)
            f2 = _func(t2)
            if f2 is None:
                continue
            sites = subs(f2)
            if k >= len(sites):
                continue
            node = sites[k]
            if mode == "drop":
                repl = node.value

                class T(ast.NodeTransformer):
                    def visit_Subscript(self, nd):
                        self.generic_visit(nd)
                        if nd is node:
                            return repl
                        return nd

                T().visit(t2)
            elif mode == "noupper":
                if node.slice.upper is None:
                    continue
                node.slice.upper = None
            else:
                if node.slice.lower is None:
                    continue
                node.slice.lower = None
            s = _unparse(t2)
            if s:
                out.append(s)
    return out


def r_break_after(src):
    """Insert `break` after an accumulation statement inside a nested loop
    (avoids counting the same duplicate multiple times)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def pred(st, d):
        if d < 1:
            return False
        if isinstance(st, ast.AugAssign):
            return True
        if (isinstance(st, ast.Expr) and isinstance(st.value, ast.Call)
                and isinstance(st.value.func, ast.Attribute)
                and st.value.func.attr in ("append", "add", "remove", "pop",
                                           "insert", "extend")):
            return True
        return False

    n = len(_stmt_sites(f, pred))
    out = []
    for k in range(min(n, 8)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        sites = _stmt_sites(f2, pred)
        if k >= len(sites):
            continue
        blk, i, _d = sites[k]
        blk.insert(i + 1, ast.Break())
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_augassign_listwrap(src):
    """`acc += x` / `acc += (x,)` -> `acc += [x]`."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def sites(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add)
                and not isinstance(n.value, ast.List)]

    n = len(sites(f))
    out = []
    for k in range(min(n, 6)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        ss = sites(f2)
        if k >= len(ss):
            continue
        node = ss[k]
        v = node.value
        if isinstance(v, ast.Tuple):
            node.value = ast.List(elts=list(v.elts), ctx=ast.Load())
        else:
            node.value = ast.List(elts=[v], ctx=ast.Load())
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_membership_target(src):
    """Fix membership check against the wrong list: `if x not in WRONG` ->
    `if x not in acc` where `acc` is the accumulator being appended to."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    accs = []
    for n in ast.walk(f):
        if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == "append"
                and isinstance(n.value.func.value, ast.Name)):
            a = n.value.func.value.id
            if a not in accs:
                accs.append(a)
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            a = n.target.id
            if a not in accs:
                accs.append(a)
    if not accs:
        return []

    def comps(fn):
        return [c for c in ast.walk(fn)
                if isinstance(c, ast.Compare) and len(c.ops) == 1
                and isinstance(c.ops[0], (ast.In, ast.NotIn))
                and isinstance(c.comparators[0], ast.Name)]

    n = len(comps(f))
    out = []
    for k in range(min(n, 4)):
        for a in accs[:2]:
            t2 = _parse(src)
            f2 = _func(t2)
            if f2 is None:
                continue
            sites = comps(f2)
            if k >= len(sites):
                continue
            c = sites[k]
            if c.comparators[0].id == a:
                continue
            c.comparators[0] = ast.Name(id=a, ctx=ast.Load())
            s = _unparse(t2)
            if s:
                out.append(s)
    return out


def r_assign_param_copy(src):
    """`x = lst` -> `x = lst[:]` (aliasing bug) or `x = []`."""
    tree = _parse(src)
    f = _func(tree)
    if f is None or not f.args.args:
        return []
    p = f.args.args[0].arg

    def sites(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.Assign) and isinstance(n.value, ast.Name)
                and n.value.id == p]

    n = len(sites(f))
    out = []
    for k in range(min(n, 3)):
        for mode in ("copy", "empty"):
            t2 = _parse(src)
            f2 = _func(t2)
            if f2 is None:
                continue
            ss = sites(f2)
            if k >= len(ss):
                continue
            node = ss[k]
            if mode == "copy":
                node.value = ast.Subscript(
                    value=ast.Name(id=p, ctx=ast.Load()),
                    slice=ast.Slice(lower=None, upper=None, step=None),
                    ctx=ast.Load())
            else:
                node.value = ast.List(elts=[], ctx=ast.Load())
            s = _unparse(t2)
            if s:
                out.append(s)
    return out


def r_extend_append_swap(src):
    """Swap `.append` <-> `.extend`."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def sites(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.Attribute) and n.attr in ("append", "extend")]

    n = len(sites(f))
    out = []
    for k in range(min(n, 5)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        ss = sites(f2)
        if k >= len(ss):
            continue
        node = ss[k]
        node.attr = "extend" if node.attr == "append" else "append"
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_return_listwrap(src):
    """`return x` -> `return list(x)` (result must be a real list)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []

    def rets(fn):
        return [n for n in ast.walk(fn)
                if isinstance(n, ast.Return) and n.value is not None]

    n = len(rets(f))
    out = []
    for k in range(min(n, 4)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        rr = rets(f2)
        if k >= len(rr):
            continue
        r = rr[k]
        if (isinstance(r.value, ast.Call) and isinstance(r.value.func, ast.Name)
                and r.value.func.id == "list"):
            continue
        r.value = ast.Call(func=ast.Name(id="list", ctx=ast.Load()),
                           args=[r.value], keywords=[])
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


def r_eq_assign(src):
    """`x == []` as a statement -> `x = []` (typo: == instead of =)."""
    tree = _parse(src)
    f = _func(tree)
    if f is None:
        return []
    pred = lambda st, d: (isinstance(st, ast.Expr)
                          and isinstance(st.value, ast.Compare)
                          and len(st.value.ops) == 1
                          and isinstance(st.value.ops[0], ast.Eq)
                          and isinstance(st.value.left, ast.Name))
    n = len(_stmt_sites(f, pred))
    out = []
    for k in range(min(n, 4)):
        t2 = _parse(src)
        f2 = _func(t2)
        if f2 is None:
            continue
        sites = _stmt_sites(f2, pred)
        if k >= len(sites):
            continue
        blk, i, _d = sites[k]
        st = blk[i]
        blk[i] = ast.Assign(
            targets=[ast.Name(id=st.value.left.id, ctx=ast.Store())],
            value=st.value.comparators[0])
        s = _unparse(t2)
        if s:
            out.append(s)
    return out


_RULES = [
    r_strip_toplevel,
    r_return_missing,
    r_return_move,
    r_print_to_return,
    r_reverse_none_fix,
    r_tuple_acc,
    r_set_fix,
    r_reverse_wrap,
    r_iter_copy,
    r_if_to_while,
    r_while_to_if,
    r_slice_variants,
    r_break_after,
    r_augassign_listwrap,
    r_membership_target,
    r_assign_param_copy,
    r_extend_append_swap,
    r_return_listwrap,
    r_eq_assign,
]


def _rule_variants(src):
    out = []
    seen = set()
    for rule in _RULES:
        try:
            for v in rule(src):
                if isinstance(v, str) and v != src and v not in seen:
                    seen.add(v)
                    out.append(v)
        except Exception:
            continue
    return out


def _base_sources(source):
    """The original source plus, if it does not parse, light syntax repairs."""
    bases = []

    def add(s):
        if isinstance(s, str) and s not in bases and _parse(s) is not None:
            bases.append(s)

    add(source)
    if not bases:
        try:
            add(source.replace("\t", "    "))
            add(re.sub(r"(?m)^(\s*)print\s+([^\s(].*?)\s*$",
                       r"\1print(\2)", source))
            add(textwrap.dedent(source))
            add(source.replace("\t", "    ").rstrip() + "\n")
        except Exception:
            pass
    return bases


def _all_candidates(source, deadline):
    yield source
    bases = _base_sources(source)
    for b in bases:
        yield b

    # Round 1: problem-specific rules on each parseable base.
    round1 = []
    for b in bases[:2]:
        for v in _rule_variants(b):
            round1.append(v)
            yield v

    # Round 2: pairwise rule compositions (e.g. break-insert + slice fix).
    emitted = 0
    for v in round1[:60]:
        if time.monotonic() > deadline:
            return
        for w in _rule_variants(v):
            yield w
            emitted += 1
            if emitted >= 1000:
                break
        if emitted >= 1000:
            break

    # Generic single-edit search on the original.
    if bases:
        try:
            for c in candidates_generic(bases[0], max_edits=1, budget=2000):
                if time.monotonic() > deadline:
                    return
                yield c
        except Exception:
            pass

    # Rule variant + one generic edit.
    for v in round1[:8]:
        if time.monotonic() > deadline:
            return
        try:
            for c in islice(candidates_generic(v, max_edits=1, budget=300), 300):
                yield c
        except Exception:
            pass

    # Generic pair-edit search on the original.
    if bases:
        try:
            for c in candidates_generic(bases[0], max_edits=2, budget=1500):
                if time.monotonic() > deadline:
                    return
                yield c
        except Exception:
            pass


def repair(source):
    try:
        if not isinstance(source, str) or not source.strip():
            return None
        deadline = time.monotonic() + _TIME_BUDGET

        def stream():
            seen = set()
            for cand in _all_candidates(source, deadline):
                if time.monotonic() > deadline:
                    return
                if not isinstance(cand, str) or cand in seen:
                    continue
                seen.add(cand)
                if not _passes_all(cand):
                    continue
                if not _rps_ok(source, cand):
                    continue
                yield cand

        result = first_passing(stream(), ENTRY, TESTS, source,
                               max_rps=MAX_RPS, max_checks=800)
        if isinstance(result, str):
            return result
        return None
    except BaseException:
        return None
```
