```python
"""Local, LLM-free automatic repair for the `fibonacci` assignment.

Round-2 revision.  Root cause of the round-1 across-the-board `no_patch`
results: the module was fragile around its helper-library usage.  It
imported `chain` / `failing_tests` from `coep.repairlib` and `rps` from
`coep.evaluate` unconditionally, and called `candidates_generic` /
`first_passing` with keyword arguments in code paths whose exceptions were
ultimately swallowed by the blanket `try/except` in `repair()`.  Any import
error or signature mismatch therefore silently turned EVERY repair attempt
into `None` -- including trivially fixable submissions such as
`return b` -> `return a` (crafted_02), which the very first targeted rule
already generated.

Fixes:
  * Every helper import is now individually guarded with a fallback
    (itertools.chain replaces repairlib.chain; missing `failing_tests` or
    `rps` just degrade gracefully -- `first_passing` still enforces the
    rps <= 0.35 cap).
  * Helper calls retry with progressively simpler signatures on TypeError
    and are isolated per stage, so one broken stage cannot abort the rest.
  * New targeted rules for the failure modes the samples exposed:
      - wrong offsets in recursive calls, e.g. fibonacci(n-0)+fibonacci(n-2)
        or fibonacci(n-1)+fibonacci(n-3)  (mutant_02, mutant_14);
      - wrong subscripts inside `seq.append(seq[i] + seq[j])`  (mutant_06).
  * A new stage tries PAIRS of targeted rewrites (one rule applied on top
    of another rule's output), covering multi-edit bugs such as
    `while len(seq) < n` + `return seq[-1]` (crafted_09) and
    `seq = [-1, 1]` + `seq[-1 + 1]` (mutant_06) without relying on the
    generic edit search.
All candidates are still validated with `first_passing` against the full
test suite and the rps <= 0.35 patch-size cap versus the original source.
"""

import ast
import copy
import itertools

try:
    from coep.repairlib import first_passing
except Exception:
    first_passing = None
try:
    from coep.repairlib import candidates_generic
except Exception:
    candidates_generic = None
try:
    from coep.repairlib import failing_tests
except Exception:
    failing_tests = None
try:
    from coep.evaluate import rps
except Exception:
    rps = None

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


def _rule_rec_calls(source):
    # Recursive form with wrong offsets: fibonacci(n-0)+fibonacci(n-2),
    # fibonacci(n-1)+fibonacci(n-3), fibonacci(n)+fibonacci(n-1), ...
    tree, func, param = _parse_func(source)
    calls = [node for node in ast.walk(func)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == ENTRY and len(node.args) == 1]
    for call in calls:
        old = call.args[0]
        for k in (1, 2):
            call.args[0] = _n_plus(param, -k)
            yield "rec", ast.unparse(tree)
        call.args[0] = old
    if len(calls) == 2:
        olds = [c.args[0] for c in calls]
        for ka, kb in ((1, 2), (2, 1)):
            calls[0].args[0] = _n_plus(param, -ka)
            calls[1].args[0] = _n_plus(param, -kb)
            yield "rec", ast.unparse(tree)
        calls[0].args[0], calls[1].args[0] = olds


def _rule_append_args(source):
    # Wrong subscripts inside the list-building step, e.g.
    # `seq.append(seq[-1 + 1] + seq[-2])` -> `seq.append(seq[-1] + seq[-2])`.
    tree, func, param = _parse_func(source)
    for node in ast.walk(func):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append" and len(node.args) == 1
                and isinstance(node.args[0], ast.BinOp)
                and isinstance(node.args[0].op, ast.Add)):
            binop = node.args[0]
            if (isinstance(binop.left, ast.Subscript)
                    and isinstance(binop.right, ast.Subscript)):
                old_l, old_r = binop.left.slice, binop.right.slice
                for a, b in ((-1, -2), (-2, -1)):
                    binop.left.slice = ast.Constant(a)
                    binop.right.slice = ast.Constant(b)
                    yield "app", ast.unparse(tree)
                binop.left.slice, binop.right.slice = old_l, old_r


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
    _rule_rec_calls,
    _rule_while,
    _rule_range,
    _rule_init,
    _rule_append_args,
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
    if failing_tests is None:
        return None
    try:
        r = failing_tests(source, ENTRY, TESTS)
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
                if (x.get("error") or not isinstance(n, int)
                        or not isinstance(got, int)):
                    return False
                if not f(n, got):
                    return False
            return True

        # Off-by-one shift up: every wrong answer equals fib(n+1).
        if all_match(lambda n, g: 0 <= n + 1 < len(FIB) and g == FIB[n + 1]):
            return ["ret", "range", "sub", "while", "rec", "init",
                    "base", "guard", "app", "merge"]
        # Off-by-one shift down: every wrong answer equals fib(n-1).
        if all_match(lambda n, g: 0 <= n - 1 and g == FIB[n - 1]):
            return ["ret", "range", "sub", "while", "rec", "init",
                    "base", "guard", "app", "merge"]
        # Crashes (IndexError / RecursionError / ...): boundary/offset bugs.
        if any(x.get("error") for x in fails):
            return ["rec", "while", "sub", "range", "guard", "init",
                    "app", "base", "ret", "merge"]
    except Exception:
        return None
    return None


def _order(spec_tagged, source):
    try:
        pri = _priority(source)
    except Exception:
        pri = None
    if not pri:
        return [s for _, s in spec_tagged]
    rank = {t: i for i, t in enumerate(pri)}
    default = len(pri)
    return [s for _, s in sorted(spec_tagged, key=lambda ts: rank.get(ts[0], default))]


# --------------------------------------------------------------------------
# Defensive wrappers around the helper library
# --------------------------------------------------------------------------

def _first_passing(cands, source, max_checks):
    """Validate candidates with first_passing, tolerating signature drift.

    The candidate stream is materialised (bounded by max_checks) so that a
    TypeError from an unexpected keyword can be retried with simpler calls
    without losing candidates.
    """
    if first_passing is None:
        return None
    try:
        pool = list(itertools.islice(cands, max_checks))
    except Exception:
        return None
    if not pool:
        return None
    for kwargs in ({"max_rps": MAX_RPS, "max_checks": max_checks},
                   {"max_rps": MAX_RPS},
                   {}):
        try:
            return first_passing(iter(pool), ENTRY, TESTS, source, **kwargs)
        except TypeError:
            continue
        except Exception:
            return None
    return None


def _gen_generic(src, edits, budget):
    """Bounded list of generic-edit candidates; empty on any failure."""
    if candidates_generic is None:
        return []
    for kwargs in ({"max_edits": edits, "budget": budget},
                   {"max_edits": edits},
                   {}):
        try:
            return list(itertools.islice(candidates_generic(src, **kwargs), budget))
        except TypeError:
            continue
        except Exception:
            return []
    return []


def _checked(original, fixed):
    if fixed is None:
        return None
    if rps is not None:
        try:
            if rps(original, fixed) > MAX_RPS:
                return None
        except Exception:
            pass  # first_passing already enforced the cap
    return fixed


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------

def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # Stage 0: the submission may already be correct (still validated).
    fixed = _first_passing(iter([source]), source, 5)
    if fixed is not None:
        return _checked(source, fixed)

    try:
        spec_tagged = _specific_variants(source)
    except Exception:
        spec_tagged = []
    try:
        spec = _order(spec_tagged, source)
    except Exception:
        spec = [s for _, s in spec_tagged]

    # Stage 1: targeted single rewrites.
    fixed = _first_passing(iter(spec), source, 200)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 2: pairs of targeted rewrites -- one rule applied on top of
    # another rule's output.  Covers e.g. wrong while-bound + wrong return
    # subscript, or wrong seed pair + wrong append subscripts.
    def stage_pairs():
        seen = set(spec)
        seen.add(source)
        for base in spec[:60]:
            try:
                for _, src in _specific_variants(base):
                    if src not in seen:
                        seen.add(src)
                        yield src
            except Exception:
                continue

    fixed = _first_passing(stage_pairs(), source, 800)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 3: generic single edits on the original.
    fixed = _first_passing(iter(_gen_generic(source, 1, 2000)), source, 500)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 4: one generic edit stacked on top of each targeted rewrite.
    def stage4():
        for s in spec[:40]:
            for cand in _gen_generic(s, 1, 200):
                yield cand

    fixed = _first_passing(stage4(), source, 700)
    if fixed is not None:
        return _checked(source, fixed)

    # Stage 5: pairs of generic edits on the original.
    fixed = _first_passing(iter(_gen_generic(source, 2, 2500)), source, 900)
    return _checked(source, fixed)


def repair(source: str):
    try:
        return _repair(source)
    except Exception:
        return None
```
