You previously wrote the following per-assignment repair module for the assignment "fibonacci":

```python
"""Local, LLM-free automatic repair for the `fibonacci` assignment.

Strategy:
  1. Validate the submission as-is (it might already pass).
  2. Generate problem-specific rewrites targeting the misconceptions common
     for THIS assignment (wrong returned variable, off-by-one loop bounds,
     wrong seed values, `seq[-1]` vs `seq[n]`, sequential instead of
     simultaneous updates, 1-based base cases), ordered by the observed
     failing-test pattern.
  3. Fall back to the generic single-edit search, then to one generic edit
     stacked on top of each targeted rewrite, then to generic edit pairs.
All candidates are validated with `first_passing`, which enforces the full
test suite and the rps <= 0.35 patch-size cap against the original source.
"""

import ast
import copy

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "fibonacci"

TESTS = [
    {"args": [0], "expected": 0},
    {"args": [1], "expected": 1},
    {"args": [2], "expected": 1},
    {"args": [3], "expected": 2},
    {"args": [4], "expected": 3},
    {"args": [5], "expected": 5},
    {"args": [6], "expected": 8},
    {"args": [7], "expected": 13},
    {"args": [8], "expected": 21},
    {"args": [10], "expected": 55},
    {"args": [12], "expected": 144},
    {"args": [15], "expected": 610},
    {"args": [20], "expected": 6765},
    {"args": [24], "expected": 46368},
]

MAX_RPS = 0.35

FIB = [0, 1]
while len(FIB) < 30:
    FIB.append(FIB[-1] + FIB[-2])


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------

def _parse_func(source):
    tree = ast.parse(source)
    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            func = node
            break
    if func is None:
        raise ValueError("no fibonacci definition")
    param = func.args.args[0].arg if func.args.args else "n"
    return tree, func, param


def _name(param):
    return ast.Name(id=param, ctx=ast.Load())


def _n_plus(param, k):
    if k == 0:
        return _name(param)
    op = ast.Add() if k > 0 else ast.Sub()
    return ast.BinOp(left=_name(param), op=op, right=ast.Constant(abs(k)))


# --------------------------------------------------------------------------
# Problem-specific rewrite rules.  Each yields (tag, candidate_source).
# All rules mutate a private tree in place and restore it after unparsing.
# --------------------------------------------------------------------------

def _rule_return_name(source):
    # `return b` instead of `return a` after the update loop (n+1 shift).
    tree, func, param = _parse_func(source)
    assigned = set()
    for node in ast.walk(func):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.For)):
            targets = [node.target]
        for t in targets:
            for x in ast.walk(t):
                if isinstance(x, ast.Name):
                    assigned.add(x.id)
    names = sorted(assigned | {param})
    for ret in ast.walk(func):
        if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Name):
            old = ret.value.id
            for name in names:
                if name != old:
                    ret.value.id = name
                    yield "ret", ast.unparse(tree)
            ret.value.id = old


def _rule_return_subscript(source):
    # `return seq[-1]` / `seq[n-1]` etc. -> try seq[n], seq[n-1], seq[n+1], ...
    tree, func, param = _parse_func(source)
    for ret in ast.walk(func):
        if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Subscript):
            sub = ret.value
            old = sub.slice
            repls = [
                _name(param),
                _n_plus(param, -1),
                _n_plus(param, 1),
                ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
                ast.Constant(0),
            ]
            for new in repls:
                sub.slice = new
                yield "sub", ast.unparse(tree)
            sub.slice = old


def _rule_init(source):
    # Wrong seed pair: [1, 1], [-1, 1], (1, 0), ... -> try (0,1), (1,0), (1,1).
    tree, func, param = _parse_func(source)
    for node in ast.walk(func):
        if (isinstance(node, ast.Assign)
                and isinstance(node.value, (ast.List, ast.Tuple))
                and len(node.value.elts) == 2):
            val = node.value
            old = val.elts
            for combo in ((0, 1), (1, 0), (1, 1)):
                val.elts = [ast.Constant(combo[0]), ast.Constant(combo[1])]
                yield "init", ast.unparse(tree)
            val.elts = old


def _rule_range(source):
    # Wrong loop bound: range(n-1), range(n+1), range(1, n), ...
    tree, func, param = _parse_func(source)
    for node in ast.walk(func):
        if (isinstance(node, ast.For) and isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"):
            call = node.iter
            old = call.args
            options = [
                [_n_plus(param, 0)],
                [_n_plus(param, -1)],
                [_n_plus(param, 1)],
            ]
            if len(old) == 2:
                for k in (0, 1, -1):
                    options.append([copy.deepcopy(old[0]), _n_plus(param, k)])
            for args in options:
                call.args = args
                yield "range", ast.unparse(tree)
            call.args = old


def _rule_while(source):
    # Wrong while bound: `while len(seq) < n` -> vs n+1/n-1; hard-coded consts.
    tree, func, param = _parse_func(source)
    for node in ast.walk(func):
        if (isinstance(node, ast.While) and isinstance(node.test, ast.Compare)
                and len(node.test.comparators) == 1):
            cmpnode = node.test
            for side_key in ("left", "right"):
                side = cmpnode.left if side_key == "left" else cmpnode.comparators[0]
                if isinstance(side, ast.Name) and side.id == param:
                    repls = [_n_plus(param, 1), _n_plus(param, -1)]
                elif isinstance(side, ast.Constant) and isinstance(side.value, int):
                    repls = [_n_plus(param, 0), _n_plus(param, 1), _n_plus(param, -1)]
                else:
                    repls = []
                for new in repls:
                    if side_key == "left":
                        cmpnode.left = new
                        yield "while", ast.unparse(tree)
                        cmpnode.left = side
                    else:
                        cmpnode.comparators[0] = new
                        yield "while", ast.unparse(tree)
                        cmpnode.comparators[0] = side


def _rule_merge_assign(source):
    # Sequential update `a = b; b = a + b` -> simultaneous `a, b = b, a + b`.
    tree, func, param = _parse_func(source)
    bodies = [func.body]
    for node in ast.walk(func):
        if isinstance(node, (ast.For, ast.While, ast.If)):
            bodies.append(node.body)
            if node.orelse:
                bodies.append(node.orelse)
    for body in bodies:
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            if not (isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign)):
                continue
            if not (len(s1.targets) == 1 and len(s2.targets) == 1):
                continue
            if not (isinstance(s1.targets[0], ast.Name)
                    and isinstance(s2.targets[0], ast.Name)):
                continue
            t1, t2 = s1.targets[0].id, s2.targets[0].id
            if t1 == t2:
                continue
            names2 = {x.id for x in ast.walk(s2.value) if isinstance(x, ast.Name)}
            if t1 not in names2:
                continue
            merged = ast.Assign(
                targets=[ast.Tuple(
                    elts=[ast.Name(id=t1, ctx=ast.Store()),
                          ast.Name(id=t2, ctx=ast.Store())],
                    ctx=ast.Store())],
                value=ast.Tuple(
                    elts=[copy.deepcopy(s1.value), copy.deepcopy(s2.value)],
                    ctx=ast.Load()),
            )
            saved = body[i:i + 2]
            body[i:i + 2] = [merged]
            yield "merge", ast.unparse(tree)
            body[i:i + 2] = saved


def _rule_base_return(source):
    # Base-case returns: `return 1` <-> `return n`, `return n` -> 0/1.
    tree, func, param = _parse_func(source)
    for ret in ast.walk(func):
        if not isinstance(ret, ast.Return) or ret.value is None:
            continue
        if isinstance(ret.value, ast.Constant) and isinstance(ret.value.value, int):
            old = ret.value
            ret.value = _name(param)
            yield "base", ast.unparse(tree)
            ret.value = old
        elif isinstance(ret.value, ast.Name) and ret.value.id == param:
            old = ret.value
            for c in (0, 1):
                ret.value = ast.Constant(c)
                yield "base", ast.unparse(tree)
            ret.value = old


def _rule_guard(source):
    # 1-based base case (`if n == 1 or n == 2: return 1`) -> `if n < 2: return n`.
    tree, func, param = _parse_func(source)
    for node in ast.walk(func):
        if (isinstance(node, ast.If) and len(node.body) == 1
                and isinstance(node.body[0], ast.Return)
                and node.body[0].value is not None):
            old_test = node.test
            old_val = node.body[0].value
            node.test = ast.Compare(left=_name(param), ops=[ast.Lt()],
                                    comparators=[ast.Constant(2)])
            node.body[0].value = _name(param)
            yield "guard", ast.unparse(tree)
            node.test = old_test
            node.body[0].value = old_val


RULES = [
    _rule_return_name,
    _rule_return_subscript,
    _rule_while,
    _rule_range,
    _rule_init,
    _rule_merge_assign,
    _rule_base_return,
    _rule_guard,
]


def _specific_variants(source):
    out = []
    seen = {source}
    for rule in RULES:
        try:
            for tag, src in rule(source):
                if isinstance(src, str) and src not in seen:
                    seen.add(src)
                    out.append((tag, src))
        except Exception:
            continue
    return out


# --------------------------------------------------------------------------
# Failure-pattern dispatch: reorder targeted rewrites by observed behaviour.
# --------------------------------------------------------------------------

def _priority(source):
    try:
        r = failing_tests(source, ENTRY, TESTS)
    except Exception:
        return None
    if not getattr(r, "compiled", False):
        return None
    fails = getattr(r, "failures", None) or []
    if not fails:
        return None

    def all_match(f):
        for x in fails:
            args = x.get("args") or []
            n = args[0] if args else None
            got = x.get("got")
            if x.get("error") or not isinstance(n, int) or not isinstance(got, int):
                return False
            if not f(n, got):
                return False
        return True

    # Off-by-one shift up: every wrong answer equals fib(n+1).
    if all_match(lambda n, g: 0 <= n + 1 < len(FIB) and g == FIB[n + 1]):
        return ["ret", "range", "sub", "while", "init", "base", "guard", "merge"]
    # Off-by-one shift down: every wrong answer equals fib(n-1).
    if all_match(lambda n, g: 0 <= n - 1 and g == FIB[n - 1]):
        return ["ret", "range", "sub", "while", "init", "base", "guard", "merge"]
    # Crashes (IndexError / RecursionError / ...): boundary or slice problems.
    if any(x.get("error") for x in fails):
        return ["while", "sub", "range", "guard", "init", "base", "ret", "merge"]
    return None


def _order(spec_tagged, source):
    pri = _priority(source)
    if not pri:
        return [s for _, s in spec_tagged]
    rank = {t: i for i, t in enumerate(pri)}
    default = len(pri)
    return [s for _, s in sorted(spec_tagged, key=lambda ts: rank.get(ts[0], default))]


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------

def _checked(original, fixed):
    if fixed is None:
        return None
    try:
        if rps(original, fixed) > MAX_RPS:
            return None
    except Exception:
        pass  # first_passing already enforced the cap
    return fixed


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # Stage 0: the submission may already be correct (still validated).
    fixed = first_passing(iter([source]), ENTRY, TESTS, source,
                          max_rps=MAX_RPS, max_checks=5)
    if fixed is not None:
        return _checked(source, fixed)

    spec_tagged = _specific_variants(source)
    spec = _order(spec_tagged, source)

    # Stage 1: targeted rewrites first, then all single generic edits.
    stage1 = chain(iter(spec), candidates_generic(source, max_edits=1, budget=2000))
    fixed = first_passing(stage1, ENTRY, TESTS, source,
                          max_rps=MAX_RPS, max_checks=500)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 2: one generic edit stacked on top of each targeted rewrite
    # (covers e.g. wrong seed + wrong index, or wrong bound + wrong return).
    def stage2():
        for s in spec[:40]:
            try:
                for cand in candidates_generic(s, max_edits=1, budget=200):
                    yield cand
            except Exception:
                continue

    fixed = first_passing(stage2(), ENTRY, TESTS, source,
                          max_rps=MAX_RPS, max_checks=700)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 3: pairs of generic edits on the original.
    fixed = first_passing(candidates_generic(source, max_edits=2, budget=2500),
                          ENTRY, TESTS, source,
                          max_rps=MAX_RPS, max_checks=900)
    return _checked(source, fixed)


def repair(source: str):
    try:
        return _repair(source)
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_02.py: NOT REPAIRED — no_patch
- crafted_09.py: NOT REPAIRED — no_patch
- mutant_02.py: NOT REPAIRED — no_patch
- mutant_06.py: NOT REPAIRED — no_patch
- mutant_14.py: NOT REPAIRED — no_patch

For reference, the submissions the module failed on:

### Failed submission crafted_02.py
```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b

```

### Failed submission crafted_09.py
```python
def fibonacci(n):
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[-1]

```

### Failed submission mutant_02.py
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 0) + fibonacci(n - 2)

```

### Failed submission mutant_06.py
```python
def fibonacci(n):
    seq = [-1, 1]
    while len(seq) <= n:
        seq.append(seq[-1 + 1] + seq[-2])
    return seq[n]

```

### Failed submission mutant_14.py
```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 3)

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
