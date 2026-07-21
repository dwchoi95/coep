You previously wrote the following per-assignment repair module for the assignment "balanced_brackets":

```python
import ast

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

_OPENERS = "([{"
_CLOSERS = ")]}"
_O2C = {"(": ")", "[": "]", "{": "}"}
_C2O = {")": "(", "]": "[", "}": "{"}


def _unparse(tree):
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _list_vars(tree):
    """Names assigned an empty list (candidate 'stack' variables)."""
    names = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            val = node.value
            if ((isinstance(val, ast.List) and not val.elts)
                    or (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                        and val.func.id == "list" and not val.args and not val.keywords)):
                if node.targets[0].id not in names:
                    names.append(node.targets[0].id)
    return names


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules (each: source -> list of variant sources).
# They target the classic misconceptions for balanced-bracket checkers:
#   * forgetting to require the stack to be empty at the end
#   * doing a single reduction pass instead of reducing to a fixpoint
#   * popping without an emptiness guard (crashes/ignores stray closers)
#   * using pop(0) (queue) instead of pop() (stack)
#   * swapped opener/closer tables or strings
# ---------------------------------------------------------------------------

def rw_return_true_tail(source):
    """Tail `return True` -> `return not <stackvar>` (forgot leftover openers)."""
    out = []
    for var in _list_vars(ast.parse(source)):
        tree = ast.parse(source)
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.body:
                last = node.body[-1]
                if (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                        and last.value.value is True):
                    node.body[-1] = ast.Return(value=ast.UnaryOp(
                        op=ast.Not(), operand=ast.Name(id=var, ctx=ast.Load())))
                    changed = True
        if changed:
            out.append(_unparse(tree))
    return out


def rw_return_truthiness(source):
    """Tail `return <stackvar>` -> `return not <stackvar>` (inverted truthiness)."""
    out = []
    for var in _list_vars(ast.parse(source)):
        tree = ast.parse(source)
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.body:
                last = node.body[-1]
                if (isinstance(last, ast.Return) and isinstance(last.value, ast.Name)
                        and last.value.id == var):
                    node.body[-1] = ast.Return(value=ast.UnaryOp(
                        op=ast.Not(), operand=ast.Name(id=var, ctx=ast.Load())))
                    changed = True
        if changed:
            out.append(_unparse(tree))
    return out


def rw_final_return(source):
    """Missing/None tail return -> append `return not <stackvar>`."""
    out = []
    for var in _list_vars(ast.parse(source)):
        tree = ast.parse(source)
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == ENTRY and node.body:
                last = node.body[-1]
                ret = ast.Return(value=ast.UnaryOp(
                    op=ast.Not(), operand=ast.Name(id=var, ctx=ast.Load())))
                if isinstance(last, ast.Return):
                    if last.value is None or (isinstance(last.value, ast.Constant)
                                              and last.value.value is None):
                        node.body[-1] = ret
                        changed = True
                else:
                    node.body.append(ret)
                    changed = True
        if changed:
            out.append(_unparse(tree))
    return out


def _pop_name(expr):
    for n in ast.walk(expr):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "pop" and isinstance(n.func.value, ast.Name)):
            return n.func.value.id
    return None


def rw_guard_pop(source):
    """Add/repair the emptiness guard around a pop-based mismatch test."""
    out = []
    # Variant A: `if <test using X.pop()>` -> `if not X or <test>`
    tree = ast.parse(source)
    changed = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            name = _pop_name(node.test)
            if name is None:
                continue
            if isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
                first = node.test.values[0]
                if (isinstance(first, ast.UnaryOp) and isinstance(first.op, ast.Not)
                        and isinstance(first.operand, ast.Name)
                        and first.operand.id == name):
                    continue  # already guarded correctly
            node.test = ast.BoolOp(op=ast.Or(), values=[
                ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=name, ctx=ast.Load())),
                node.test])
            changed = True
    if changed:
        out.append(_unparse(tree))
    # Variant B: `if X and <pop-test>` -> `if not X or <pop-test>`
    tree = ast.parse(source)
    changed = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            t = node.test
            if (isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And)
                    and len(t.values) >= 2 and isinstance(t.values[0], ast.Name)
                    and any(_pop_name(v) == t.values[0].id for v in t.values[1:])):
                node.test = ast.BoolOp(op=ast.Or(), values=[
                    ast.UnaryOp(op=ast.Not(),
                                operand=ast.Name(id=t.values[0].id, ctx=ast.Load()))
                ] + list(t.values[1:]))
                changed = True
    if changed:
        out.append(_unparse(tree))
    return out


def rw_pop_zero(source):
    """`X.pop(0)` (queue behaviour) -> `X.pop()` (stack behaviour)."""
    tree = ast.parse(source)
    changed = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop" and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0):
            node.args = []
            changed = True
    return [_unparse(tree)] if changed else []


def rw_dict_swap(source):
    """Swap keys/values of a bracket-pair dict written in the wrong direction."""
    tree = ast.parse(source)
    changed = False

    def _ok(xs):
        return all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                   and len(x.value) == 1 and x.value in "()[]{}" for x in xs)

    for node in ast.walk(tree):
        if (isinstance(node, ast.Dict) and node.keys
                and all(k is not None for k in node.keys)
                and _ok(node.keys) and _ok(node.values)):
            node.keys, node.values = list(node.values), list(node.keys)
            changed = True
    return [_unparse(tree)] if changed else []


def rw_bracket_string_swap(source):
    """Swap opener/closer 3-char membership strings written the wrong way round."""
    tree = ast.parse(source)
    changed = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) == 3:
            v = node.value
            if set(v) == set(_OPENERS):
                node.value = "".join(_O2C[c] for c in v)
                changed = True
            elif set(v) == set(_CLOSERS):
                node.value = "".join(_C2O[c] for c in v)
                changed = True
    return [_unparse(tree)] if changed else []


def _is_empty_replace_chain(value, target):
    """value is X.replace(a,'').replace(b,'')... rooted at Name(target)."""
    node = value
    seen = False
    while (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
           and node.func.attr == "replace" and len(node.args) == 2
           and not node.keywords
           and isinstance(node.args[1], ast.Constant) and node.args[1].value == ""):
        seen = True
        node = node.func.value
    return seen and isinstance(node, ast.Name) and node.id == target


def rw_fixpoint_replace(source):
    """Wrap a single reduction pass `t = t.replace('()','')...` in a fixpoint loop
    (single-pass reduction only removes innermost pairs once)."""
    tree = ast.parse(source)
    tmp = "_prev"
    while tmp in source:
        tmp = "_" + tmp
    done = False
    for parent in ast.walk(tree):
        if done:
            break
        if isinstance(parent, ast.While):
            continue  # already inside a loop
        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            continue
        i = 0
        while i < len(body):
            stmt = body[i]
            if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and _is_empty_replace_chain(stmt.value, stmt.targets[0].id)):
                x = stmt.targets[0].id
                j = i + 1
                while (j < len(body) and isinstance(body[j], ast.Assign)
                       and len(body[j].targets) == 1
                       and isinstance(body[j].targets[0], ast.Name)
                       and body[j].targets[0].id == x
                       and _is_empty_replace_chain(body[j].value, x)):
                    j += 1
                run = body[i:j]
                loop = ast.While(
                    test=ast.Constant(value=True),
                    body=([ast.Assign(targets=[ast.Name(id=tmp, ctx=ast.Store())],
                                      value=ast.Name(id=x, ctx=ast.Load()))]
                          + run
                          + [ast.If(test=ast.Compare(
                                        left=ast.Name(id=x, ctx=ast.Load()),
                                        ops=[ast.Eq()],
                                        comparators=[ast.Name(id=tmp, ctx=ast.Load())]),
                                    body=[ast.Break()], orelse=[])]),
                    orelse=[])
                body[i:j] = [loop]
                done = True
                break
            i += 1
    return [_unparse(tree)] if done else []


_REWRITES = [
    rw_return_true_tail,
    rw_fixpoint_replace,
    rw_return_truthiness,
    rw_guard_pop,
    rw_pop_zero,
    rw_dict_swap,
    rw_bracket_string_swap,
    rw_final_return,
]


def _specific_variants(source):
    seen = {source}
    first = []
    for rw in _REWRITES:
        try:
            for v in rw(source):
                if isinstance(v, str) and v not in seen:
                    seen.add(v)
                    first.append(v)
        except Exception:
            pass
    # second-order combinations of the specific rules (two independent slips)
    combos = []
    for v in first[:8]:
        for rw in _REWRITES:
            try:
                for w in rw(v):
                    if isinstance(w, str) and w not in seen:
                        seen.add(w)
                        combos.append(w)
            except Exception:
                pass
            if len(combos) >= 40:
                break
        if len(combos) >= 40:
            break
    return first + combos


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # Already correct? Validate (rps == 0) and return as-is.
    try:
        res = failing_tests(source, ENTRY, TESTS)
        if getattr(res, "compiled", False) and res.passed == res.total:
            got = first_passing([source], ENTRY, TESTS, source,
                                max_rps=0.35, max_checks=5)
            if got is not None:
                return got
    except Exception:
        pass

    spec = _specific_variants(source)

    # Stage 1: high-precision problem-specific rewrites.
    try:
        got = first_passing(spec, ENTRY, TESTS, source,
                            max_rps=0.35, max_checks=150)
        if got is not None:
            return got
    except Exception:
        pass

    # Stage 2: generic single-edit search.
    try:
        got = first_passing(candidates_generic(source, max_edits=1, budget=600),
                            ENTRY, TESTS, source, max_rps=0.35, max_checks=600)
        if got is not None:
            return got
    except Exception:
        pass

    # Stage 3: generic two-edit search (bounded).
    try:
        got = first_passing(candidates_generic(source, max_edits=2, budget=2000),
                            ENTRY, TESTS, source, max_rps=0.35, max_checks=2000)
        if got is not None:
            return got
    except Exception:
        pass

    # Stage 4: a specific rewrite plus one generic edit on top.
    pool = spec[:6]
    if pool:
        try:
            gen = chain(*[candidates_generic(v, max_edits=1, budget=150)
                          for v in pool])
            got = first_passing(gen, ENTRY, TESTS, source,
                                max_rps=0.35, max_checks=900)
            if got is not None:
                return got
        except Exception:
            pass

    return None


def repair(source: str):
    try:
        return _repair(source)
    except Exception:
        return None

```

Evaluated on the sample buggy submissions, the outcomes were:
- crafted_04.py: REPAIRED
- crafted_07.py: NOT REPAIRED — no_patch
- mutant_05.py: REPAIRED
- mutant_06.py: REPAIRED
- mutant_15.py: REPAIRED

For reference, the submissions the module failed on:

### Failed submission crafted_07.py
```python
def balanced_brackets(s):
    t = "".join(c for c in s if c in "()[]{}")
    t = t.replace("()", "").replace("[]", "").replace("{}", "")
    return t == ""

```

Revise the module to fix the failures while keeping all constraints from before (define `repair(source) -> str | None`; no LLM/network; validate with `first_passing`; patch-size cap 0.35; preserve the student's approach; generalize beyond these samples; never raise). Output ONLY the complete revised module in a single ```python code block, nothing else.
