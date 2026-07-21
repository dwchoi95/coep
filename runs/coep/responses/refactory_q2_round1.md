```python
"""Local, LLM-free automatic repairer for the "Unique dates and months" assignment.

Strategy:
  1. Parse the submission; on syntax error return None.
  2. Run the visible tests (through a small appended dispatcher so that the
     multi-function suite can be driven via a single entry point) to see which
     of unique_day / unique_month / contains_unique_day are failing.
  3. Generate candidates, highest-priority first:
       - the submission itself,
       - problem-specific AST rewrites targeting the classic misconceptions
         for this assignment ("count < 2 / >= 2 means unique" forgetting the
         zero case, trailing `return True` after a counting loop, inconsistent
         counter variable names / shadowed parameters, comparing an element
         against the counter instead of the parameter, undefined-name typos,
         mis-nested if/else inside contains_unique_day, and an empty/broken
         contains_unique_day rebuilt around the student's own unique_day),
       - compositions of two such rewrites (bugs usually appear copy-pasted
         in several functions at once, and rewrites fix all sites together),
       - the generic 1-edit search on the original and on rewritten variants,
       - the generic 2-edit search.
  4. Every candidate is validated with first_passing (which enforces the test
     suite and the patch-size cap); additionally the plain (dispatcher-free)
     candidate is pre-filtered and post-checked with rps(src, cand) <= 0.35.
"""

import ast
import difflib
import time
import builtins as _builtins

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps

ENTRY = "unique_day"

# The visible test suite, copied exactly (with the function each test calls).
TESTS = [
    {"func": "unique_day", "args": ["1", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "unique_month", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": False},
    {"func": "unique_month", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": True},
    {"func": "contains_unique_day", "args": ["January", [["January", "1"], ["January", "2"]]], "expected": True},
    {"func": "contains_unique_day", "args": ["January", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "contains_unique_day", "args": ["February", [["January", "10"], ["February", "1"], ["February", "10"]]], "expected": True},
    {"func": "unique_day", "args": ["3", [["January", "1"], ["January", "2"]]], "expected": False},
    {"func": "unique_month", "args": ["March", [["January", "1"], ["February", "1"]]], "expected": False},
    {"func": "unique_day", "args": ["1", [["January", "1"], ["January", "2"]]], "expected": True},
]

# The suite exercises three different functions, but first_passing drives a
# single entry point.  We therefore append a tiny dispatcher to every candidate
# (and to the original, so relative patch size is computed fairly), route each
# test through it, and strip it again before returning the repaired program.
_DISPATCH = "_coep_dispatch"
_SUFFIX = (
    "\n\ndef _coep_dispatch(_coep_fname, *_coep_args):\n"
    "    return globals()[_coep_fname](*_coep_args)\n"
)
DTESTS = [{"args": [t["func"]] + list(t["args"]), "expected": t["expected"]} for t in TESTS]

_MAX_RPS = 0.35
_TIME_BUDGET = 8.0


# --------------------------------------------------------------------------- #
# small AST helpers
# --------------------------------------------------------------------------- #

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


def _unparse(tree):
    try:
        ast.fix_missing_locations(tree)
        return ast.unparse(tree)
    except Exception:
        return None


def _fn_defs(tree):
    return [n for n in tree.body if isinstance(n, ast.FunctionDef)]


def _params(fn):
    a = fn.args
    out = [x.arg for x in getattr(a, "posonlyargs", []) or []]
    out += [x.arg for x in a.args]
    out += [x.arg for x in a.kwonlyargs]
    if a.vararg:
        out.append(a.vararg.arg)
    if a.kwarg:
        out.append(a.kwarg.arg)
    return out


def _is_int(c, val=None):
    if not (isinstance(c, ast.Constant) and isinstance(c.value, int)
            and not isinstance(c.value, bool)):
        return False
    return val is None or c.value == val


def _inc_name(node):
    """`x += 1` or `x = x + 1` (also mismatched `x = y + 1`) -> target name."""
    if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
            and isinstance(node.op, ast.Add) and _is_int(node.value, 1)):
        return node.target.id
    if (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)):
        v = node.value
        if (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add)
                and isinstance(v.left, ast.Name) and _is_int(v.right, 1)):
            return node.targets[0].id
    return None


def _inc_any(node):
    """Numeric increment or tuple/list append counting."""
    n = _inc_name(node)
    if n:
        return n
    if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
            and isinstance(node.op, ast.Add)
            and isinstance(node.value, (ast.Tuple, ast.List))):
        return node.target.id
    if (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)):
        v = node.value
        if (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add)
                and isinstance(v.left, ast.Name)
                and isinstance(v.right, (ast.Tuple, ast.List))):
            return node.targets[0].id
    return None


# --------------------------------------------------------------------------- #
# problem-specific rewrite rules (each: source -> list of rewritten sources)
# --------------------------------------------------------------------------- #

def _rule_typo(src):
    """Repair undefined names by renaming them to the closest defined name."""
    tree = _parse(src)
    if tree is None:
        return []
    modnames = {f.name for f in _fn_defs(tree)}
    bset = set(dir(_builtins))
    fixes = []
    for fn in _fn_defs(tree):
        stored = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                stored.add(node.id)
        known = set(_params(fn)) | stored | modnames
        pool = sorted(known)
        seen = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                nid = node.id
                if nid in known or nid in bset or nid in seen:
                    continue
                seen.add(nid)
                matches = difflib.get_close_matches(nid, pool, n=2, cutoff=0.5)
                if matches:
                    fixes.append((fn.name, nid, matches))
    if not fixes:
        return []

    def build(mapping):
        t2 = _parse(src)
        if t2 is None:
            return None
        for fn in _fn_defs(t2):
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and (fn.name, node.id) in mapping:
                    node.id = mapping[(fn.name, node.id)]
        return _unparse(t2)

    out = []
    best = {(f, b): ms[0] for f, b, ms in fixes}
    v = build(best)
    if v:
        out.append(v)
    for f, b, ms in fixes:
        for alt in ms[1:]:
            m2 = dict(best)
            m2[(f, b)] = alt
            v = build(m2)
            if v:
                out.append(v)
    return out


def _rule_unique_cmp(src):
    """'not more than one occurrence' misconception: in unique_day/unique_month
    rewrite  x >= 2 / x > 1  ->  x != 1   and   x < 2 / x <= 1  ->  x == 1,
    so that a count of zero is no longer treated as unique."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = [False]

    class T(ast.NodeTransformer):
        def visit_Compare(self, node):
            self.generic_visit(node)
            if len(node.ops) == 1 and len(node.comparators) == 1:
                c = node.comparators[0]
                if _is_int(c):
                    op, v = node.ops[0], c.value
                    if (isinstance(op, ast.GtE) and v == 2) or (isinstance(op, ast.Gt) and v == 1):
                        node.ops = [ast.NotEq()]
                        node.comparators = [ast.Constant(1)]
                        changed[0] = True
                    elif (isinstance(op, ast.Lt) and v == 2) or (isinstance(op, ast.LtE) and v == 1):
                        node.ops = [ast.Eq()]
                        node.comparators = [ast.Constant(1)]
                        changed[0] = True
            return node

    for fn in _fn_defs(tree):
        if fn.name in ("unique_day", "unique_month"):
            T().visit(fn)
    if not changed[0]:
        return []
    v = _unparse(tree)
    return [v] if v else []


def _rule_tail_return(src):
    """Counting loop that early-returns False on a duplicate but ends with a
    blanket `return True` (zero occurrences wrongly count as unique):
    replace the trailing `return True` with `return <counter> == 1`."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for fn in _fn_defs(tree):
        if fn.name not in ("unique_day", "unique_month") or not fn.body:
            continue
        counters = []
        for node in ast.walk(fn):
            n = _inc_name(node)
            if n:
                counters.append(n)
        last = fn.body[-1]
        if (counters and isinstance(last, ast.Return)
                and isinstance(last.value, ast.Constant) and last.value.value is True):
            fn.body[-1] = ast.Return(value=ast.Compare(
                left=ast.Name(id=counters[0], ctx=ast.Load()),
                ops=[ast.Eq()], comparators=[ast.Constant(1)]))
            changed = True
    if not changed:
        return []
    v = _unparse(tree)
    return [v] if v else []


def _rule_counter(src):
    """Unify inconsistent counter names (init `x = 0`/`x = ()`, increment,
    `x == 1` test all using different names, or the init shadowing a
    parameter), and fix comparisons of an element against the counter
    instead of against the function's first parameter."""
    tree = _parse(src)
    if tree is None:
        return []
    changed = False
    for fn in _fn_defs(tree):
        params = _params(fn)
        pset = set(params)
        inits, incs, conds = [], [], []
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                v = node.value
                if _is_int(v, 0) or (isinstance(v, (ast.Tuple, ast.List)) and not v.elts):
                    inits.append((node, node.targets[0].id))
                    continue
            n = _inc_any(node)
            if n:
                incs.append((node, n))
                continue
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                c = node.comparators[0]
                if _is_int(c) and c.value in (1, 2):
                    left, nm = node.left, None
                    if isinstance(left, ast.Name):
                        nm = left
                    elif (isinstance(left, ast.Call) and isinstance(left.func, ast.Name)
                          and left.func.id == "len" and len(left.args) == 1
                          and isinstance(left.args[0], ast.Name)):
                        nm = left.args[0]
                    if nm is not None:
                        conds.append(nm)
        if not incs:
            continue
        init_names = [n for _, n in inits]
        inc_names = [n for _, n in incs]
        cond_names = [n.id for n in conds]
        distinct = set(init_names + inc_names + cond_names)
        bad_init = any(n in pset for n in init_names)
        canonical = None
        if len(distinct) > 1 or bad_init:
            canonical = (next((n for n in init_names if n not in pset), None)
                         or next((n for n in inc_names if n not in pset), None)
                         or next((n for n in cond_names if n not in pset), None)
                         or "_count")
            for node, _ in inits:
                if node.targets[0].id != canonical:
                    node.targets[0].id = canonical
                    changed = True
            for node, _ in incs:
                if isinstance(node, ast.AugAssign):
                    if node.target.id != canonical:
                        node.target.id = canonical
                        changed = True
                else:
                    if node.targets[0].id != canonical:
                        node.targets[0].id = canonical
                        changed = True
                    v = node.value
                    if (isinstance(v, ast.BinOp) and isinstance(v.left, ast.Name)
                            and v.left.id != canonical):
                        v.left.id = canonical
                        changed = True
            for nm in conds:
                if nm.id != canonical:
                    nm.id = canonical
                    changed = True
        if fn.name in ("unique_day", "unique_month") and params:
            first = params[0]
            counter_names = set(init_names + inc_names)
            if canonical:
                counter_names.add(canonical)
            counter_names.discard(first)
            for node in ast.walk(fn):
                if (isinstance(node, ast.Compare) and len(node.ops) == 1
                        and isinstance(node.ops[0], ast.Eq) and len(node.comparators) == 1):
                    l, r = node.left, node.comparators[0]
                    if isinstance(l, ast.Subscript) and isinstance(r, ast.Name) and r.id in counter_names:
                        r.id = first
                        changed = True
                    elif isinstance(r, ast.Subscript) and isinstance(l, ast.Name) and l.id in counter_names:
                        l.id = first
                        changed = True
    if not changed:
        return []
    v = _unparse(tree)
    return [v] if v else []


def _rule_merge_if(src):
    """contains_unique_day mis-nesting: a loop whose body is
    `if <match>: ...` followed by a second trailing `if/else` that should
    live inside the match branch -> move it inside."""
    tree = _parse(src)
    if tree is None:
        return []
    nsites = 0
    for fn in _fn_defs(tree):
        if fn.name != "contains_unique_day":
            continue
        for node in ast.walk(fn):
            if isinstance(node, (ast.For, ast.While)):
                b = node.body
                if (len(b) >= 2 and isinstance(b[-1], ast.If)
                        and isinstance(b[-2], ast.If) and not b[-2].orelse):
                    nsites += 1
    out = []
    for k in range(nsites):
        t2 = _parse(src)
        if t2 is None:
            break
        idx, done = -1, False
        for fn in _fn_defs(t2):
            if fn.name != "contains_unique_day" or done:
                continue
            for node in ast.walk(fn):
                if done:
                    break
                if isinstance(node, (ast.For, ast.While)):
                    b = node.body
                    if (len(b) >= 2 and isinstance(b[-1], ast.If)
                            and isinstance(b[-2], ast.If) and not b[-2].orelse):
                        idx += 1
                        if idx == k:
                            b[-2].body.append(b[-1])
                            del b[-1]
                            done = True
        v = _unparse(t2)
        if v:
            out.append(v)
    return out


def _rule_contains_rebuild(src):
    """Empty / hopeless contains_unique_day: rebuild its body as the minimal
    loop over the student's own possible_birthdays parameter, reusing the
    student's own unique_day (their approach for the hard part is kept)."""
    tree = _parse(src)
    if tree is None:
        return []
    fns = {f.name: f for f in _fn_defs(tree)}
    fn = fns.get("contains_unique_day")
    if fn is not None:
        params = _params(fn)
        if len(params) >= 2:
            m, pb = params[0], params[1]
        else:
            try:
                fn.args = ast.parse("def _f(month, possible_birthdays): pass").body[0].args
            except Exception:
                return []
            m, pb = "month", "possible_birthdays"
        loopvar = "_bd" if "_bd" not in (m, pb) else "_coep_bd"
        body_src = ("for {lv} in {pb}:\n"
                    "    if {lv}[0] == {m} and unique_day({lv}[1], {pb}):\n"
                    "        return True\n"
                    "return False").format(lv=loopvar, m=m, pb=pb)
        try:
            fn.body = ast.parse(body_src).body
        except Exception:
            return []
    else:
        try:
            newfn = ast.parse(
                "def contains_unique_day(month, possible_birthdays):\n"
                "    for _bd in possible_birthdays:\n"
                "        if _bd[0] == month and unique_day(_bd[1], possible_birthdays):\n"
                "            return True\n"
                "    return False").body[0]
        except Exception:
            return []
        tree.body.append(newfn)
    v = _unparse(tree)
    return [v] if v else []


# --------------------------------------------------------------------------- #
# main driver
# --------------------------------------------------------------------------- #

def _repair(src):
    if not isinstance(src, str) or _parse(src) is None:
        return None
    deadline = time.monotonic() + _TIME_BUDGET
    aug_orig = src + _SUFFIX

    # Which functions are currently failing?  (used only to prioritise rules)
    fail_funcs = set()
    try:
        res = failing_tests(aug_orig, _DISPATCH, DTESTS)
        if res is not None and getattr(res, "compiled", True):
            for f in (getattr(res, "failures", None) or []):
                idx = f.get("index") if isinstance(f, dict) else getattr(f, "index", None)
                if isinstance(idx, int) and 0 <= idx < len(TESTS):
                    fail_funcs.add(TESTS[idx]["func"])
    except Exception:
        pass

    rules = [_rule_unique_cmp, _rule_tail_return, _rule_counter,
             _rule_merge_if, _rule_contains_rebuild]
    if fail_funcs and fail_funcs <= {"contains_unique_day"}:
        rules = [_rule_merge_if, _rule_contains_rebuild, _rule_counter,
                 _rule_unique_cmp, _rule_tail_return]

    # Typo repair acts as a base transformation (other bugs sit on top of it).
    bases = [src]
    try:
        for t in _rule_typo(src)[:3]:
            if t and t not in bases:
                bases.append(t)
    except Exception:
        pass

    def rewrite_candidates():
        for base in bases:
            yield base
            level1 = []
            for r in rules:
                try:
                    outs = r(base)
                except Exception:
                    outs = []
                for o in outs[:4]:
                    if o:
                        level1.append((r, o))
                        yield o
            for r1, x in level1[:10]:
                for r2 in rules:
                    if r2 is r1:
                        continue
                    try:
                        outs = r2(x)
                    except Exception:
                        outs = []
                    for o in outs[:2]:
                        if o:
                            yield o

    def generic_candidates():
        seeds = list(bases)
        for r in rules:
            try:
                for o in r(src)[:2]:
                    if o and o not in seeds:
                        seeds.append(o)
            except Exception:
                pass
        for s in seeds[:6]:
            if time.monotonic() > deadline:
                return
            try:
                for c in candidates_generic(s, max_edits=1):
                    yield c
                    if time.monotonic() > deadline:
                        return
            except Exception:
                pass
        try:
            for c in candidates_generic(src, max_edits=2, budget=2000):
                yield c
                if time.monotonic() > deadline:
                    return
        except Exception:
            pass

    seen = set()

    def pipeline():
        for c in chain(rewrite_candidates(), generic_candidates()):
            if time.monotonic() > deadline:
                return
            if not isinstance(c, str) or c in seen:
                continue
            seen.add(c)
            try:
                if rps(src, c) > _MAX_RPS:
                    continue
            except Exception:
                continue
            yield c + _SUFFIX

    try:
        winner = first_passing(pipeline(), _DISPATCH, DTESTS, aug_orig,
                               max_rps=_MAX_RPS, max_checks=800)
    except Exception:
        winner = None
    if not winner or not isinstance(winner, str) or not winner.endswith(_SUFFIX):
        return None
    plain = winner[: len(winner) - len(_SUFFIX)]
    try:
        if rps(src, plain) > _MAX_RPS:
            return None
    except Exception:
        return None
    return plain


def repair(source: str) -> str | None:
    try:
        return _repair(source)
    except Exception:
        return None
```
