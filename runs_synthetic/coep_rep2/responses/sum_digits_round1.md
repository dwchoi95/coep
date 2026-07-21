```python
import ast
import copy
import itertools
import sys
import time

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "sum_digits"

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [5], "expected": 5},
    {"args": [9], "expected": 9},
    {"args": [10], "expected": 1},
    {"args": [99], "expected": 18},
    {"args": [100], "expected": 1},
    {"args": [123], "expected": 6},
    {"args": [1000], "expected": 1},
    {"args": [4444], "expected": 16},
    {"args": [7], "expected": 7},
    {"args": [10001], "expected": 2},
    {"args": [55555], "expected": 25},
    {"args": [987654321], "expected": 45},
    {"args": [999999999], "expected": 81},
]

_TRACE_LIMIT = 20000
_TIME_BUDGET = 8.0
_MAX_SINGLE_ACTIONS = 150
_MAX_PAIRS = 4000


class _StepLimit(Exception):
    pass


def _run_limited(func, args, limit=_TRACE_LIMIT):
    """Run func(*args) with a hard cap on interpreter trace events.

    Protects the pre-filter against candidates that loop forever
    (e.g. `while n >= 0: n //= 10`) or recurse without a base case.
    """
    state = {"n": 0}

    def tracer(frame, event, arg):
        state["n"] += 1
        if state["n"] > limit:
            raise _StepLimit()
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return func(*args)
    finally:
        sys.settrace(old)


def _quick_passes(src):
    """Cheap, loop-safe check that src defines sum_digits and passes all TESTS."""
    try:
        code = compile(src, "<candidate>", "exec")
    except Exception:
        return False
    ns = {"input": lambda *a, **k: "", "print": lambda *a, **k: None}
    try:
        _run_limited(exec, (code, ns))
    except Exception:
        return False
    fn = ns.get(ENTRY)
    if not callable(fn):
        return False
    for t in TESTS:
        try:
            got = _run_limited(fn, tuple(t["args"]))
        except Exception:
            return False
        if got != t["expected"]:
            return False
    return True


def _unparse(tree):
    return ast.unparse(ast.fix_missing_locations(tree))


# ---------------------------------------------------------------------------
# Problem-specific single/pair edit enumeration
# ---------------------------------------------------------------------------

def _collect_sites(tree):
    consts, bins, augs, cmps = [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            consts.append(node)
        elif isinstance(node, ast.BinOp):
            bins.append(node)
        elif isinstance(node, ast.AugAssign):
            augs.append(node)
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            cmps.append(node)
    return consts, bins, augs, cmps


_ARITH = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)
_CMPOPS = (ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq)


def _edit_actions(tree):
    """Enumerate targeted micro-edits for this assignment.

    Typical bugs: wrong loop boundary (n > 9 instead of n > 0), wrong
    radix constant (% 9 / // 9 instead of 10), subtraction instead of
    addition, / instead of //, swapped % and //, wrong init constant.
    """
    consts, bins, augs, cmps = _collect_sites(tree)
    actions = []
    for i, c in enumerate(consts):
        vals = {0, 1, 2, 9, 10, c.value - 1, c.value + 1}
        for v in sorted(vals):
            if v != c.value and v >= 0:
                actions.append(("const", i, v))
    for i, b in enumerate(bins):
        for op in _ARITH:
            if not isinstance(b.op, op):
                actions.append(("binop", i, op))
    for i, a in enumerate(augs):
        for op in _ARITH:
            if not isinstance(a.op, op):
                actions.append(("augop", i, op))
    for i, c in enumerate(cmps):
        for op in _CMPOPS:
            if not isinstance(c.ops[0], op):
                actions.append(("cmpop", i, op))

    def prio(a):
        kind, _idx, val = a
        if kind in ("augop", "binop"):
            return 0 if val is ast.Add else 2
        if kind == "const":
            return 1 if val in (0, 10) else 3
        return 2

    actions.sort(key=prio)
    return actions[:_MAX_SINGLE_ACTIONS]


def _apply(tree, actions):
    t = copy.deepcopy(tree)
    consts, bins, augs, cmps = _collect_sites(t)
    pools = {"const": consts, "binop": bins, "augop": augs, "cmpop": cmps}
    for kind, idx, val in actions:
        node = pools[kind][idx]
        if kind == "const":
            node.value = val
        elif kind in ("binop", "augop"):
            node.op = val()
        else:
            node.ops = [val()]
    return _unparse(t)


# ---------------------------------------------------------------------------
# Problem-specific structural rewrites
# ---------------------------------------------------------------------------

def _int_call(node):
    return ast.Call(func=ast.Name(id="int", ctx=ast.Load()), args=[node], keywords=[])


def _loop_target_names(tree):
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
    return names


def _string_acc_variants(tree):
    """Fix string-concatenation accumulators and digit-counting loops.

    - total = "" ... total = total + d  ->  total = 0 ... total + int(d)
    - total += d (d a str char)          ->  total += int(d)
    - total += 1 (counting digits)       ->  total += int(d)
    """
    targets = _loop_target_names(tree)
    if not targets:
        return []
    variants = []
    for fix_init, wrap_int, count_to_sum in (
        (True, True, False),
        (False, True, False),
        (True, False, False),
        (False, False, True),
    ):
        t = copy.deepcopy(tree)
        state = {"changed": False}

        class T(ast.NodeTransformer):
            def visit_Constant(self, node):
                if fix_init and node.value == "":
                    state["changed"] = True
                    return ast.copy_location(ast.Constant(value=0), node)
                return node

            def visit_BinOp(self, node):
                self.generic_visit(node)
                if wrap_int and isinstance(node.op, ast.Add):
                    if isinstance(node.left, ast.Name) and node.left.id in targets:
                        node.left = _int_call(node.left)
                        state["changed"] = True
                    if isinstance(node.right, ast.Name) and node.right.id in targets:
                        node.right = _int_call(node.right)
                        state["changed"] = True
                return node

            def visit_AugAssign(self, node):
                self.generic_visit(node)
                if isinstance(node.op, ast.Add):
                    if (wrap_int and isinstance(node.value, ast.Name)
                            and node.value.id in targets):
                        node.value = _int_call(node.value)
                        state["changed"] = True
                    if (count_to_sum and isinstance(node.value, ast.Constant)
                            and node.value.value == 1):
                        state["changed"] = True
                        node.value = _int_call(
                            ast.Name(id=sorted(targets)[0], ctx=ast.Load()))
                return node

        t = T().visit(t)
        if state["changed"]:
            try:
                variants.append(_unparse(t))
            except Exception:
                pass
    return variants


def _iter_str_variants(tree):
    """`for d in n:` over an int -> `for d in str(n):` (plus int() wrapping)."""
    out = []
    t = copy.deepcopy(tree)
    changed = False
    for n in ast.walk(t):
        if isinstance(n, ast.For) and isinstance(n.iter, ast.Name):
            n.iter = ast.Call(func=ast.Name(id="str", ctx=ast.Load()),
                              args=[ast.Name(id=n.iter.id, ctx=ast.Load())],
                              keywords=[])
            changed = True
    if changed:
        try:
            src = _unparse(t)
            out.append(src)
            out.extend(_string_acc_variants(ast.parse(src)))
        except Exception:
            pass
    return out


def _move_return_variants(tree):
    """Move a return that was mistakenly indented into a loop out of it."""
    t = copy.deepcopy(tree)
    state = {"changed": False}

    def fix_body(body):
        new = []
        for stmt in body:
            if (isinstance(stmt, (ast.While, ast.For)) and stmt.body
                    and isinstance(stmt.body[-1], ast.Return)):
                ret = stmt.body.pop()
                if not stmt.body:
                    stmt.body.append(ast.Pass())
                new.append(stmt)
                new.append(ret)
                state["changed"] = True
            else:
                for attr in ("body", "orelse", "finalbody"):
                    sub = getattr(stmt, attr, None)
                    if sub:
                        setattr(stmt, attr, fix_body(sub))
                new.append(stmt)
        return new

    t.body = fix_body(t.body)
    if state["changed"]:
        try:
            return [_unparse(t)]
        except Exception:
            return []
    return []


def _print_return_variants(tree):
    """print(total) instead of return total -> return total."""
    t = copy.deepcopy(tree)
    changed = False
    fns = [n for n in ast.walk(t)
           if isinstance(n, ast.FunctionDef) and n.name == ENTRY]
    for fn in fns:
        for i, stmt in enumerate(fn.body):
            if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Name)
                    and stmt.value.func.id == "print"
                    and len(stmt.value.args) == 1):
                fn.body[i] = ast.copy_location(
                    ast.Return(value=stmt.value.args[0]), stmt)
                changed = True
    if changed:
        try:
            return [_unparse(t)]
        except Exception:
            return []
    return []


def _assign_to_aug_variants(tree):
    """Inside a loop, `total = n % 10` (overwrite) -> `total += n % 10`."""
    out = []
    total = sum(1 for n in ast.walk(tree)
                if isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name))
    for target_idx in range(min(total, 8)):
        t = copy.deepcopy(tree)
        state = {"k": -1, "changed": False, "depth": 0}

        class T(ast.NodeTransformer):
            def visit_While(self, node):
                state["depth"] += 1
                self.generic_visit(node)
                state["depth"] -= 1
                return node

            def visit_For(self, node):
                state["depth"] += 1
                self.generic_visit(node)
                state["depth"] -= 1
                return node

            def visit_Assign(self, node):
                self.generic_visit(node)
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    state["k"] += 1
                    if state["k"] == target_idx and state["depth"] > 0:
                        tgt = node.targets[0].id
                        if not any(isinstance(x, ast.Name) and x.id == tgt
                                   for x in ast.walk(node.value)):
                            state["changed"] = True
                            return ast.copy_location(
                                ast.AugAssign(
                                    target=ast.Name(id=tgt, ctx=ast.Store()),
                                    op=ast.Add(), value=node.value),
                                node)
                return node

        t = T().visit(t)
        if state["changed"]:
            try:
                out.append(_unparse(t))
            except Exception:
                pass
    return out


def _recursion_base_variants(tree):
    """Add a missing base case to a recursive solution."""
    out = []
    t = copy.deepcopy(tree)
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name == ENTRY and n.args.args:
            calls_self = any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id == ENTRY for c in ast.walk(n))
            if calls_self:
                p = n.args.args[0].arg
                try:
                    guard = ast.parse(
                        "if {0} < 10:\n    return {0}".format(p)).body[0]
                    n.body.insert(0, guard)
                    out.append(_unparse(t))
                except Exception:
                    pass
            break
    return out


def _special_variants(tree):
    out = []
    for fn in (_string_acc_variants, _iter_str_variants, _move_return_variants,
               _print_return_variants, _assign_to_aug_variants,
               _recursion_base_variants):
        try:
            out.extend(fn(tree))
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Candidate stream and entry point
# ---------------------------------------------------------------------------

def _candidate_stream(source, tree, deadline):
    # 0. the source itself (it may already pass)
    yield source
    # 1. precise structural rewrites for known misconceptions
    for v in _special_variants(tree):
        yield v
    # 2. targeted single micro-edits (boundary constants, op flips, radix)
    actions = _edit_actions(tree)
    for a in actions:
        if time.monotonic() > deadline:
            return
        try:
            s = _apply(tree, [a])
        except Exception:
            continue
        yield s
    # 3. pairs of micro-edits (e.g. `total -= n % 9` needs Sub->Add and 9->10)
    npairs = 0
    for a, b in itertools.combinations(actions, 2):
        if time.monotonic() > deadline or npairs >= _MAX_PAIRS:
            break
        if a[0] == b[0] and a[1] == b[1]:
            continue
        npairs += 1
        try:
            s = _apply(tree, [a, b])
        except Exception:
            continue
        yield s
    # 4. generic AST edit search as a fallback
    for kwargs in ({"max_edits": 1, "budget": 2000},
                   {"max_edits": 2, "budget": 2000}):
        if time.monotonic() > deadline:
            return
        try:
            gen = iter(candidates_generic(source, **kwargs))
        except Exception:
            continue
        while True:
            if time.monotonic() > deadline:
                return
            try:
                c = next(gen)
            except StopIteration:
                break
            except Exception:
                break
            yield c


def repair(source: str):
    try:
        if not isinstance(source, str):
            return None
        try:
            tree = ast.parse(source)
        except Exception:
            return None
        deadline = time.monotonic() + _TIME_BUDGET

        def filtered():
            seen = set()
            for cand in _candidate_stream(source, tree, deadline):
                if not isinstance(cand, str) or cand in seen:
                    continue
                seen.add(cand)
                try:
                    ok = _quick_passes(cand)
                except Exception:
                    ok = False
                if ok:
                    yield cand

        # Final authority: first_passing enforces the full test suite and
        # the relative-patch-size cap against the original submission.
        return first_passing(filtered(), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=800)
    except Exception:
        return None
```
