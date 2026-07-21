```python
"""Local, LLM-free automatic repair system for the `balanced_brackets` assignment.

Strategy: combine problem-specific AST rewrite rules that target the common
misconceptions for this assignment (missing final empty-stack check, missing
empty-stack guard before pop(), single-pass replace-reduction that needs a
loop, swapped bracket-pair dictionaries, comparing pop() against the raw
character instead of its mapped partner) with the generic mutation search
from coep.repairlib (1-edit, then specific+1-edit, then 2-edit).  Every
candidate is validated with first_passing, which enforces the full visible
test suite and the token-level patch-size cap (rps <= 0.35).
"""

import ast
import copy
import io
import tokenize

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain

ENTRY = "balanced_brackets"

TESTS = [
    {"args": ["()"], "expected": True},
    {"args": ["([)]"], "expected": False},
    {"args": [""], "expected": True},
    {"args": ["no brackets here!"], "expected": True},
    {"args": ["(a[b]{c})"], "expected": True},
    {"args": ["((("], "expected": False},
    {"args": [")("], "expected": False},
    {"args": ["{[()()]}"], "expected": True},
    {"args": ["([]"], "expected": False},
    {"args": ["())"], "expected": False},
    {"args": ["[(])"], "expected": False},
    {"args": ["{}[]()"], "expected": True},
    {"args": ["([{([{}])}])"], "expected": True},
    {"args": ["]"], "expected": False},
]

_BR = "()[]{}"


# ---------------------------------------------------------------------------
# Small AST helpers
# ---------------------------------------------------------------------------

def _func(tree):
    """The FunctionDef for the entry point (fallback: first function)."""
    fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    for n in fns:
        if n.name == ENTRY:
            return n
    return fns[0] if fns else None


def _requote(src):
    """Rewrite simple single-quoted strings as double-quoted.

    ast.unparse normalizes strings to single quotes; if the student used
    double quotes, that would inflate the token-level patch size.  Offering
    both quoting variants lets first_passing keep whichever fits the cap.
    """
    try:
        toks = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            val = tok.string
            if (tok.type == tokenize.STRING and val.startswith("'")
                    and val.endswith("'") and not val.startswith("'''")
                    and '"' not in val and "\\" not in val):
                val = '"' + val[1:-1] + '"'
            toks.append((tok.type, val, tok.start, tok.end, tok.line))
        return tokenize.untokenize(toks)
    except Exception:
        return None


def _variants(t2):
    """Unparse a mutated tree; yield both quoting styles."""
    try:
        src = ast.unparse(ast.fix_missing_locations(t2))
    except Exception:
        return []
    out = [src]
    rq = _requote(src)
    if rq and rq != src:
        out.append(rq)
    return out


def _empty_list_vars(func):
    names = []
    for n in ast.walk(func):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)):
            v = n.value
            empty = (isinstance(v, ast.List) and not v.elts) or (
                isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                and v.func.id == "list" and not v.args)
            if empty and n.targets[0].id not in names:
                names.append(n.targets[0].id)
    return names


def _dict_vars(func):
    names = []
    for n in ast.walk(func):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Dict)
                and n.targets[0].id not in names):
            names.append(n.targets[0].id)
    return names


def _is_pop_call(n):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "pop" and isinstance(n.func.value, ast.Name))


def _stack_access_name(test):
    """Name of a variable accessed via .pop() or [-1] inside an expression."""
    for n in ast.walk(test):
        if _is_pop_call(n):
            return n.func.value.id
    for n in ast.walk(test):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
            sl = n.slice
            if (isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub)
                    and isinstance(sl.operand, ast.Constant)
                    and sl.operand.value == 1):
                return n.value.id
    return None


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules.  Each takes the parsed original tree and
# returns a list of candidate source strings (validated later).
# ---------------------------------------------------------------------------

def _rule_return(tree):
    """Fix wrong final result: `return True` / `return stack` / `return
    len(stack)` should be `return not stack` (forgot leftover openers)."""
    out = []
    func = _func(tree)
    listvars = _empty_list_vars(func)

    def rets(f):
        return [n for n in ast.walk(f)
                if isinstance(n, ast.Return) and n.value is not None]

    for i, r in enumerate(rets(func)):
        v = r.value
        names = []
        if isinstance(v, ast.Constant) and v.value is True:
            names = list(listvars)
        elif isinstance(v, ast.Name):
            names = [v.id]
        elif (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
              and v.func.id == "len" and len(v.args) == 1
              and isinstance(v.args[0], ast.Name)):
            names = [v.args[0].id]
        for name in names:
            t2 = copy.deepcopy(tree)
            rets(_func(t2))[i].value = ast.UnaryOp(
                op=ast.Not(), operand=ast.Name(id=name, ctx=ast.Load()))
            out.extend(_variants(t2))
    return out


def _rule_guard(tree):
    """Add a missing `not stack or` guard to an if-test that pops/peeks."""
    out = []
    func = _func(tree)

    def ifs(f):
        return [n for n in ast.walk(f) if isinstance(n, ast.If)]

    for i, node in enumerate(ifs(func)):
        if isinstance(node.test, ast.BoolOp):
            continue
        name = _stack_access_name(node.test)
        if name is None:
            continue
        t2 = copy.deepcopy(tree)
        n2 = ifs(_func(t2))[i]
        n2.test = ast.BoolOp(op=ast.Or(), values=[
            ast.UnaryOp(op=ast.Not(),
                        operand=ast.Name(id=name, ctx=ast.Load())),
            n2.test])
        out.extend(_variants(t2))
    return out


def _rule_popguard(tree):
    """Insert `if not stack: return False` before a bare `x = stack.pop()`."""
    out = []
    func = _func(tree)

    def sites(f):
        return [n for n in ast.walk(f)
                if isinstance(n, (ast.Assign, ast.Expr))
                and _is_pop_call(n.value)]

    for i in range(len(sites(func))):
        t2 = copy.deepcopy(tree)
        f2 = _func(t2)
        node = sites(f2)[i]
        name = node.value.func.value.id
        pm = {}
        for p in ast.walk(f2):
            for ch in ast.iter_child_nodes(p):
                pm[ch] = p
        parent = pm.get(node)
        if parent is None:
            continue
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(parent, field, None)
            if isinstance(lst, list) and node in lst:
                guard = ast.If(
                    test=ast.UnaryOp(
                        op=ast.Not(),
                        operand=ast.Name(id=name, ctx=ast.Load())),
                    body=[ast.Return(value=ast.Constant(value=False))],
                    orelse=[])
                lst.insert(lst.index(node), guard)
                out.extend(_variants(t2))
                break
    return out


def _rule_loopwrap(tree):
    """Single-pass replace reduction: wrap the `.replace(...)` assignment(s)
    in `for _ in <param>:` so the reduction runs to a fixed point."""
    out = []
    func = _func(tree)
    args = func.args
    param = None
    if getattr(args, "args", None):
        param = args.args[0].arg
    elif getattr(args, "posonlyargs", None):
        param = args.posonlyargs[0].arg
    if param is None:
        return out

    def has_replace(v):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == "replace" for n in ast.walk(v))

    def is_site(st):
        return (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and has_replace(st.value))

    n_sites = len([n for n in ast.walk(func) if is_site(n)])
    for i in range(n_sites):
        t2 = copy.deepcopy(tree)
        f2 = _func(t2)
        node = [n for n in ast.walk(f2) if is_site(n)][i]
        pm = {}
        for p in ast.walk(f2):
            for ch in ast.iter_child_nodes(p):
                pm[ch] = p
        # Skip if already inside a loop.
        a, inloop = pm.get(node), False
        while a is not None:
            if isinstance(a, (ast.For, ast.While)):
                inloop = True
                break
            a = pm.get(a)
        if inloop:
            continue
        parent = pm.get(node, f2)
        for field in ("body", "orelse", "finalbody"):
            lst = getattr(parent, field, None)
            if isinstance(lst, list) and node in lst:
                j0 = j1 = lst.index(node)
                while j0 > 0 and is_site(lst[j0 - 1]):
                    j0 -= 1
                while j1 + 1 < len(lst) and is_site(lst[j1 + 1]):
                    j1 += 1
                loop = ast.For(
                    target=ast.Name(id="_", ctx=ast.Store()),
                    iter=ast.Name(id=param, ctx=ast.Load()),
                    body=lst[j0:j1 + 1], orelse=[])
                lst[j0:j1 + 1] = [loop]
                out.extend(_variants(t2))
                break
    return out


def _rule_dictswap(tree):
    """Swap keys/values of a bracket-pair dict (opener/closer confusion)."""
    out = []
    func = _func(tree)

    def ok(node):
        return (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and len(node.value) == 1 and node.value in _BR)

    def dicts(f):
        return [n for n in ast.walk(f)
                if isinstance(n, ast.Dict) and n.keys
                and all(ok(k) for k in n.keys)
                and all(ok(v) for v in n.values)]

    for i in range(len(dicts(func))):
        t2 = copy.deepcopy(tree)
        d = dicts(_func(t2))[i]
        d.keys, d.values = list(d.values), list(d.keys)
        out.extend(_variants(t2))
    return out


def _rule_popcmp(tree):
    """`stack.pop() != c` should be `stack.pop() != pairs[c]`."""
    out = []
    func = _func(tree)
    dictvars = _dict_vars(func)
    if not dictvars:
        return out

    def comps(f):
        return [n for n in ast.walk(f)
                if isinstance(n, ast.Compare) and len(n.comparators) == 1]

    for i, c in enumerate(comps(func)):
        left_pop = _is_pop_call(c.left) and isinstance(c.comparators[0], ast.Name)
        right_pop = _is_pop_call(c.comparators[0]) and isinstance(c.left, ast.Name)
        if not (left_pop or right_pop):
            continue
        for dv in dictvars:
            t2 = copy.deepcopy(tree)
            c2 = comps(_func(t2))[i]
            if left_pop:
                nm = c2.comparators[0].id
                c2.comparators[0] = ast.Subscript(
                    value=ast.Name(id=dv, ctx=ast.Load()),
                    slice=ast.Name(id=nm, ctx=ast.Load()), ctx=ast.Load())
            else:
                nm = c2.left.id
                c2.left = ast.Subscript(
                    value=ast.Name(id=dv, ctx=ast.Load()),
                    slice=ast.Name(id=nm, ctx=ast.Load()), ctx=ast.Load())
            out.extend(_variants(t2))
    return out


_RULES = (_rule_return, _rule_guard, _rule_popguard, _rule_loopwrap,
          _rule_dictswap, _rule_popcmp)


def _specific(source):
    """All problem-specific rewrite candidates (deduplicated), as a list."""
    try:
        tree = ast.parse(source)
    except Exception:
        return []
    if _func(tree) is None:
        return []
    seen = {source}
    cands = []
    for rule in _RULES:
        try:
            for c in rule(tree):
                if c not in seen:
                    seen.add(c)
                    cands.append(c)
        except Exception:
            pass
    return cands


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def repair(source):
    try:
        if not isinstance(source, str):
            return None
        try:
            ast.parse(source)
        except Exception:
            return None  # syntax error -> no repair

        # Already-correct submission: validate and return unchanged.
        try:
            ok = first_passing(iter([source]), ENTRY, TESTS, source,
                               max_rps=0.35, max_checks=2)
            if ok is not None:
                return ok
        except Exception:
            pass

        specs = _specific(source)

        def stage_specific():
            return iter(specs)

        def stage_generic1():
            return candidates_generic(source, max_edits=1, budget=1500)

        def stage_layered():
            # A specific rewrite plus one generic edit on top.
            def gen():
                for sp in specs[:10]:
                    try:
                        for c in candidates_generic(sp, max_edits=1,
                                                    budget=200):
                            yield c
                    except Exception:
                        continue
            return gen()

        def stage_generic2():
            return candidates_generic(source, max_edits=2, budget=8000)

        for maker, cap in ((stage_specific, 80),
                           (stage_generic1, 600),
                           (stage_layered, 500),
                           (stage_generic2, 1200)):
            try:
                res = first_passing(maker(), ENTRY, TESTS, source,
                                    max_rps=0.35, max_checks=cap)
            except Exception:
                res = None
            if res is not None:
                return res
        return None
    except Exception:
        return None
```
