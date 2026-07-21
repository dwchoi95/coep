```python
"""Local, LLM-free automatic repair for the `sum_digits(n)` assignment.

Strategy
--------
1. Parse the submission; syntax errors -> None.
2. Run the visible tests once (failing_tests) and inspect the failure
   pattern to decide whether the submission looks "string-flavoured"
   (TypeError / string results, i.e. the str(n)-iteration approach went
   wrong) or "arithmetic-flavoured" (wrong numbers from a %/// loop).
3. Generate repair candidates, most-likely first:
     * problem-specific AST rewrites targeting the misconceptions this
       assignment provokes:
         - wrong constants (while n > 9, n % 9, n //= 9, base case
           `return 1`, `total = 1`, ...) -> retargeted to {0, 1, 9, 10},
           never producing a divisor of 0/1 (no infinite loops);
         - sign slips: `total -= ...` -> `total += ...`, and `/` -> `//`;
         - string-loop bugs: missing int(ch) around the loop variable,
           `total = ""` initialisation, missing `str(...)` on the iterable;
         - "counted instead of added": `total += 1` -> `total += int(ch)`
           in a for-loop, or `total += 1` -> `total += n % 10` in a
           while-loop that floor-divides n;
         - returning/printing the wrong thing: `print(x)` -> `return x`,
           returning the wrong variable, returning a constant instead of
           the parameter in a one-digit base case;
     * pairs of the above (fixes double mutants like `total -= n % 9`);
     * the generic 1-edit and 2-edit AST search from coep.repairlib.
4. Every candidate (including the untouched original) is validated by
   first_passing, which enforces the full test suite and rps <= 0.35,
   so the student's own approach is always preserved.
"""

import ast
import copy
import itertools

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

_DIV_OPS = (ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)


# ---------------------------------------------------------------- utilities

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


def _safe_iter(it):
    """Iterate a generator, swallowing any exception it raises."""
    try:
        for x in it:
            yield x
    except Exception:
        return


def _sources(tree_iter):
    for t in tree_iter:
        s = _unparse(t)
        if s:
            yield s


def _dedupe(str_iter):
    seen = set()
    for c in str_iter:
        if isinstance(c, str) and c not in seen:
            seen.add(c)
            yield c


def _parents(tree):
    p = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            p[child] = node
    return p


def _all_consts(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.Constant)]


def _op_nodes(tree):
    return [n for n in ast.walk(tree) if isinstance(n, (ast.BinOp, ast.AugAssign))]


def _fors(tree):
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.For) and isinstance(n.target, ast.Name)]


def _whiles(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.While)]


def _funcs(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


def _is_plain_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ------------------------------------------------- problem-specific rewrites

def _const_edit_trees(tree):
    """Retarget integer constants to the values that matter for this task.

    Covers `while n > 9` -> `n > 0`, `n % 9` -> `n % 10`, `n //= 9` ->
    `n //= 10`, wrong base cases (`return 1` -> `return 0`), wrong
    initialisations (`total = 1` -> `total = 0`, `total = ""` -> 0).
    Divisor positions only ever become 9 or 10, so no candidate can
    divide by 0 or 1 (which would loop forever).
    """
    parents = _parents(tree)
    consts = _all_consts(tree)
    for i, node in enumerate(consts):
        v = node.value
        if _is_plain_int(v):
            par = parents.get(node)
            divisor = (
                (isinstance(par, ast.BinOp) and par.right is node
                 and isinstance(par.op, _DIV_OPS))
                or (isinstance(par, ast.AugAssign) and par.value is node
                    and isinstance(par.op, _DIV_OPS))
            )
            allowed = (9, 10) if divisor else (0, 1, 9, 10)
            for r in allowed:
                if r != v:
                    t2 = copy.deepcopy(tree)
                    _all_consts(t2)[i].value = r
                    yield t2
        elif isinstance(v, str) and v == "":
            t2 = copy.deepcopy(tree)
            _all_consts(t2)[i].value = 0
            yield t2


def _op_fix_trees(tree):
    """`total -= ...` -> `total += ...` and `/` -> `//` (each site, then all)."""
    nodes = _op_nodes(tree)
    fixes = []
    for i, n in enumerate(nodes):
        if isinstance(n.op, ast.Sub):
            fixes.append((i, ast.Add))
        elif isinstance(n.op, ast.Div):
            fixes.append((i, ast.FloorDiv))
    for i, cls in fixes:
        t2 = copy.deepcopy(tree)
        _op_nodes(t2)[i].op = cls()
        yield t2
    if len(fixes) > 1:
        t2 = copy.deepcopy(tree)
        nodes2 = _op_nodes(t2)
        for i, cls in fixes:
            nodes2[i].op = cls()
        yield t2


class _WrapInt(ast.NodeTransformer):
    """Wrap every Load use of `var` in int(...), skipping existing int(...)."""

    def __init__(self, var):
        self.var = var

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == "int":
            return node
        self.generic_visit(node)
        return node

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id == self.var:
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id="int", ctx=ast.Load()),
                    args=[ast.Name(id=self.var, ctx=ast.Load())],
                    keywords=[],
                ),
                node,
            )
        return node


def _zero_empty_strings(tree):
    changed = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value == "":
            n.value = 0
            changed = True
    return changed


def _string_loop_fix_trees(tree):
    """Fixes for the str(n)-iteration approach.

    - loop variable used without int(): wrap it (with and without also
      turning a `total = ""` initialisation into `total = 0`);
    - iterable missing str(): wrap it (alone, plus combined with int()).
    """
    for i, f in enumerate(_fors(tree)):
        var = f.target.id

        t2 = copy.deepcopy(tree)
        f2 = _fors(t2)[i]
        w = _WrapInt(var)
        f2.body = [w.visit(s) for s in f2.body]
        t3 = copy.deepcopy(t2)
        if _zero_empty_strings(t3):
            yield t3
        yield t2

        it = f.iter
        already_str = (isinstance(it, ast.Call)
                       and isinstance(it.func, ast.Name)
                       and it.func.id == "str")
        if not already_str:
            t4 = copy.deepcopy(tree)
            f4 = _fors(t4)[i]
            f4.iter = ast.Call(func=ast.Name(id="str", ctx=ast.Load()),
                               args=[f4.iter], keywords=[])
            yield copy.deepcopy(t4)
            w4 = _WrapInt(var)
            f4.body = [w4.visit(s) for s in f4.body]
            yield t4
            t5 = copy.deepcopy(t4)
            if _zero_empty_strings(t5):
                yield t5


class _OneToIntVar(ast.NodeTransformer):
    """Replace the `which`-th literal 1 with int(var)."""

    def __init__(self, var, which):
        self.var = var
        self.which = which
        self.count = -1

    def visit_Constant(self, node):
        if _is_plain_int(node.value) and node.value == 1:
            self.count += 1
            if self.count == self.which:
                return ast.copy_location(
                    ast.Call(
                        func=ast.Name(id="int", ctx=ast.Load()),
                        args=[ast.Name(id=self.var, ctx=ast.Load())],
                        keywords=[],
                    ),
                    node,
                )
        return node


def _for_count_fix_trees(tree):
    """`total += 1` inside `for ch in str(n)` counted digits: use int(ch)."""
    for i, f in enumerate(_fors(tree)):
        var = f.target.id
        n_ones = 0
        for s in f.body:
            for n in ast.walk(s):
                if isinstance(n, ast.Constant) and _is_plain_int(n.value) and n.value == 1:
                    n_ones += 1
        for which in range(n_ones):
            t2 = copy.deepcopy(tree)
            f2 = _fors(t2)[i]
            tr = _OneToIntVar(var, which)
            f2.body = [tr.visit(s) for s in f2.body]
            yield t2


def _while_count_fix_trees(tree):
    """`total += 1` inside a while that floor-divides n: use n % 10."""
    for i, w in enumerate(_whiles(tree)):
        var = None
        for s in w.body:
            if (isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name)
                    and isinstance(s.op, (ast.FloorDiv, ast.Div))):
                var = s.target.id
            elif (isinstance(s, ast.Assign) and len(s.targets) == 1
                  and isinstance(s.targets[0], ast.Name)
                  and isinstance(s.value, ast.BinOp)
                  and isinstance(s.value.op, (ast.FloorDiv, ast.Div))):
                var = s.targets[0].id
        if var is None:
            continue
        repl = ast.BinOp(left=ast.Name(id=var, ctx=ast.Load()),
                         op=ast.Mod(), right=ast.Constant(value=10))
        for j, s in enumerate(w.body):
            if (isinstance(s, ast.AugAssign) and isinstance(s.op, ast.Add)
                    and isinstance(s.value, ast.Constant)
                    and _is_plain_int(s.value.value) and s.value.value == 1):
                t2 = copy.deepcopy(tree)
                _whiles(t2)[i].body[j].value = copy.deepcopy(repl)
                yield t2
            elif (isinstance(s, ast.Assign) and isinstance(s.value, ast.BinOp)
                  and isinstance(s.value.op, ast.Add)
                  and isinstance(s.value.right, ast.Constant)
                  and _is_plain_int(s.value.right.value)
                  and s.value.right.value == 1):
                t2 = copy.deepcopy(tree)
                _whiles(t2)[i].body[j].value.right = copy.deepcopy(repl)
                yield t2


def _return_fix_trees(tree):
    """Return the wrong name -> try each assigned name / the parameter."""
    for fi, fn in enumerate(_funcs(tree)):
        names = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id not in names:
                        names.append(t.id)
            elif (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
                  and n.target.id not in names):
                names.append(n.target.id)
        for a in fn.args.args:
            if a.arg not in names:
                names.append(a.arg)
        rets = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
        for ri, r in enumerate(rets):
            if isinstance(r.value, ast.Name):
                for name in names:
                    if name != r.value.id:
                        t2 = copy.deepcopy(tree)
                        fn2 = _funcs(t2)[fi]
                        rets2 = [n for n in ast.walk(fn2)
                                 if isinstance(n, ast.Return)]
                        rets2[ri].value.id = name
                        yield t2
            elif isinstance(r.value, ast.Constant) and fn.args.args:
                # e.g. base case `if n < 10: return 0` should return n
                t2 = copy.deepcopy(tree)
                fn2 = _funcs(t2)[fi]
                rets2 = [n for n in ast.walk(fn2) if isinstance(n, ast.Return)]
                rets2[ri].value = ast.Name(id=fn.args.args[0].arg,
                                           ctx=ast.Load())
                yield t2


def _print_to_return_trees(tree):
    """`print(x)` at function top level -> `return x`."""
    for fi, fn in enumerate(_funcs(tree)):
        for si, s in enumerate(fn.body):
            if (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                    and isinstance(s.value.func, ast.Name)
                    and s.value.func.id == "print"
                    and len(s.value.args) == 1):
                t2 = copy.deepcopy(tree)
                fn2 = _funcs(t2)[fi]
                old = fn2.body[si]
                fn2.body[si] = ast.copy_location(
                    ast.Return(value=old.value.args[0]), old)
                yield t2


def _specific_singles(tree, stringy):
    groups_str = [
        lambda: _string_loop_fix_trees(tree),
        lambda: _for_count_fix_trees(tree),
    ]
    groups_num = [
        lambda: _const_edit_trees(tree),
        lambda: _op_fix_trees(tree),
        lambda: _while_count_fix_trees(tree),
    ]
    groups_misc = [
        lambda: _return_fix_trees(tree),
        lambda: _print_to_return_trees(tree),
    ]
    order = (groups_str + groups_num + groups_misc if stringy
             else groups_num + groups_str + groups_misc)
    for g in order:
        yield from _safe_iter(g())


def _specific_pairs(tree):
    # sign/operator fix composed with a constant fix
    # (repairs double mutants like `total -= n % 9` or `total -= ...; n //= 9`)
    for t1 in itertools.islice(_safe_iter(_op_fix_trees(tree)), 12):
        yield from itertools.islice(_safe_iter(_const_edit_trees(t1)), 40)
    # two independent constant fixes
    for t1 in itertools.islice(_safe_iter(_const_edit_trees(tree)), 20):
        yield from itertools.islice(_safe_iter(_const_edit_trees(t1)), 20)


# --------------------------------------------------------------------- main

def _looks_stringy(source):
    """Dispatch on the observed failing-test pattern."""
    try:
        res = failing_tests(source, ENTRY, TESTS)
    except Exception:
        return False
    try:
        for f in getattr(res, "failures", None) or []:
            try:
                err = str(f.get("error") or "")
                got = f.get("got")
            except AttributeError:
                err, got = str(f), None
            if (isinstance(got, str) or "TypeError" in err
                    or "str" in err or "iterable" in err):
                return True
    except Exception:
        return False
    return False


def _repair(source):
    if not isinstance(source, str):
        return None
    tree = _parse(source)
    if tree is None:
        return None

    stringy = _looks_stringy(source)

    def originals():
        yield source

    candidates = itertools.chain(
        originals(),
        _sources(_safe_iter(_specific_singles(tree, stringy))),
        _sources(itertools.islice(_safe_iter(_specific_pairs(tree)), 400)),
        _safe_iter(candidates_generic(source, max_edits=1, budget=2000)),
        _safe_iter(candidates_generic(source, max_edits=2, budget=2000)),
    )
    return first_passing(
        _dedupe(candidates), ENTRY, TESTS, source,
        max_rps=0.35, max_checks=800,
    )


def repair(source: str) -> str | None:
    try:
        return _repair(source)
    except Exception:
        return None
```
