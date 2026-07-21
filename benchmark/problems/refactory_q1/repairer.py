"""Local, LLM-free automatic repair for the 'Sequential Search' assignment.

The correct behaviour: search(x, seq) returns the first index i with
x <= seq[i], or len(seq) if x is greater than every element (insertion
position keeping seq sorted).  Common student misconceptions handled here:

* falling off the end of the loop (returns None for empty seq / x > all)
  -> append ``return len(seq)``;
* wrong tail value (``return len(seq) - 1``, ``return i`` after the loop,
  sentinel returns like -1/None/False) -> rewrite to ``return len(seq)``
  or bump by one;
* missing empty-sequence guard before indexing seq[0]/seq[-1]
  -> prepend ``if not seq: return 0``;
* forgotten increment in a while loop -> append ``i += 1``;
* off-by-one / flipped comparison operators (< vs <=, >= vs >)
  -> generic single/double edit search.

All candidates are validated through ``first_passing`` which enforces the
full visible test suite and the relative-patch-size cap.
"""

import ast

from coep.repairlib import candidates_generic, first_passing

ENTRY = "search"
MAX_RPS = 0.35

TESTS = [
    {"args": [42, [-5, 1, 3, 5, 7, 10]], "expected": 6},
    {"args": [42, [1, 5, 10]], "expected": 3},
    {"args": [5, [1, 5, 10]], "expected": 1},
    {"args": [7, [1, 5, 10]], "expected": 2},
    {"args": [3, [1, 5, 10]], "expected": 1},
    {"args": [-5, [1, 5, 10]], "expected": 0},
    {"args": [10, [-5, -1, 3, 5, 7, 10]], "expected": 5},
    {"args": [-100, [-5, -1, 3, 5, 7, 10]], "expected": 0},
    {"args": [0, [-5, -1, 3, 5, 7, 10]], "expected": 2},
    {"args": [100, []], "expected": 0},
    {"args": [-100, []], "expected": 0},
]


# --------------------------------------------------------------------------
# AST helpers
# --------------------------------------------------------------------------

def _parse(source):
    try:
        return ast.parse(source)
    except Exception:
        return None


def _find_func(tree):
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for f in funcs:
        if f.name == ENTRY:
            return f
    return funcs[0] if funcs else None


def _seq_name(func):
    try:
        names = [a.arg for a in (list(getattr(func.args, "posonlyargs", []) or [])
                                 + list(func.args.args))]
    except Exception:
        names = []
    # The parameter passed to len(...) is almost certainly the sequence.
    for n in ast.walk(func):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "len" and n.args
                and isinstance(n.args[0], ast.Name) and n.args[0].id in names):
            return n.args[0].id
    # Otherwise, a subscripted parameter.
    for n in ast.walk(func):
        if (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
                and n.value.id in names):
            return n.value.id
    if len(names) >= 2:
        return names[1]
    if names:
        return names[-1]
    return "seq"


def _fresh(source):
    tree = _parse(source)
    if tree is None:
        return None, None, None
    func = _find_func(tree)
    if func is None:
        return None, None, None
    return tree, func, _seq_name(func)


def _len_call(seq):
    return ast.Call(func=ast.Name(id="len", ctx=ast.Load()),
                    args=[ast.Name(id=seq, ctx=ast.Load())], keywords=[])


def _finish(tree):
    try:
        ast.fix_missing_locations(tree)
        out = ast.unparse(tree)
        return [out] if out else []
    except Exception:
        return []


# --------------------------------------------------------------------------
# Problem-specific rewrite rules.  Each takes a source string and returns a
# (possibly empty) list of rewritten candidate sources.  All results are
# validated later; rules only need to be plausible, not certainly correct.
# --------------------------------------------------------------------------

def _rule_append_return_len(source):
    """Function may fall off the end (returns None) -> append return len(seq)."""
    tree, func, seq = _fresh(source)
    if func is None or not func.body:
        return []
    if isinstance(func.body[-1], ast.Return):
        return []
    func.body.append(ast.Return(value=_len_call(seq)))
    return _finish(tree)


def _rule_trailing_return_len(source):
    """Wrong fall-through value (return i+1 / len(seq)-1 / i / -1 ...)."""
    tree, func, seq = _fresh(source)
    if func is None or not func.body:
        return []
    last = func.body[-1]
    if not isinstance(last, ast.Return):
        return []
    new = ast.Return(value=_len_call(seq))
    try:
        if ast.dump(last) == ast.dump(new):
            return []
    except Exception:
        pass
    func.body[-1] = new
    return _finish(tree)


def _is_len_minus_one(node):
    return (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub)
            and isinstance(node.right, ast.Constant)
            and node.right.value == 1
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len")


def _rule_len_minus_one(source):
    """Replace one occurrence of len(seq) - 1 with len(seq) (per occurrence)."""
    tree0 = _parse(source)
    if tree0 is None:
        return []
    total = sum(1 for n in ast.walk(tree0) if _is_len_minus_one(n))
    outs = []
    for k in range(min(total, 6)):
        tree = _parse(source)
        if tree is None:
            break
        state = {"i": 0}

        class _T(ast.NodeTransformer):
            def visit_BinOp(self, node):
                self.generic_visit(node)
                if _is_len_minus_one(node):
                    i = state["i"]
                    state["i"] = i + 1
                    if i == k:
                        return node.left
                return node

        outs.extend(_finish(_T().visit(tree)))
    return outs


def _rule_sentinel_returns(source):
    """'Not found' sentinels (return -1 / None / False / bare return)
    become return len(seq)."""
    tree, func, seq = _fresh(source)
    if func is None:
        return []
    state = {"changed": False}

    class _T(ast.NodeTransformer):
        def visit_Return(self, node):
            v = node.value
            bad = v is None
            if (isinstance(v, ast.Constant)
                    and (v.value is None or v.value is False)):
                bad = True
            if (isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.USub)
                    and isinstance(v.operand, ast.Constant)
                    and v.operand.value == 1):
                bad = True
            if bad:
                state["changed"] = True
                return ast.Return(value=_len_call(seq))
            return node

    _T().visit(func)
    if not state["changed"]:
        return []
    return _finish(tree)


def _rule_guard_empty(source):
    """Prepend an empty-sequence guard: if not seq: return 0."""
    tree, func, seq = _fresh(source)
    if func is None:
        return []
    guard = ast.If(
        test=ast.UnaryOp(op=ast.Not(),
                         operand=ast.Name(id=seq, ctx=ast.Load())),
        body=[ast.Return(value=ast.Constant(value=0))],
        orelse=[])
    func.body.insert(0, guard)
    return _finish(tree)


def _rule_return_name_plus1(source):
    """Off-by-one on a bare variable return: return i -> return i + 1
    (per occurrence)."""
    tree0 = _parse(source)
    if tree0 is None:
        return []
    total = sum(1 for n in ast.walk(tree0)
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Name))
    outs = []
    for k in range(min(total, 6)):
        tree = _parse(source)
        if tree is None:
            break
        state = {"i": 0}

        class _T(ast.NodeTransformer):
            def visit_Return(self, node):
                self.generic_visit(node)
                if isinstance(node.value, ast.Name):
                    i = state["i"]
                    state["i"] = i + 1
                    if i == k:
                        node.value = ast.BinOp(left=node.value, op=ast.Add(),
                                               right=ast.Constant(value=1))
                return node

        outs.extend(_finish(_T().visit(tree)))
    return outs


def _rule_while_increment(source):
    """A while loop whose test variable is never updated in the body
    (infinite loop): append '<var> += 1' to the loop body."""
    tree0 = _parse(source)
    if tree0 is None:
        return []
    _, func0, seq = _fresh(source)
    pairs = []
    whiles = [n for n in ast.walk(tree0) if isinstance(n, ast.While)]
    for wi, w in enumerate(whiles):
        test_names = {n.id for n in ast.walk(w.test)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        stored = set()
        for st in w.body:
            for n in ast.walk(st):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    stored.add(n.id)
        for name in sorted(test_names - stored - {"len", seq, None}
                           if seq is not None else
                           test_names - stored - {"len"}):
            pairs.append((wi, name))
    outs = []
    for wi, name in pairs[:6]:
        tree = _parse(source)
        if tree is None:
            break
        ws = [n for n in ast.walk(tree) if isinstance(n, ast.While)]
        if wi >= len(ws):
            continue
        ws[wi].body.append(
            ast.AugAssign(target=ast.Name(id=name, ctx=ast.Store()),
                          op=ast.Add(), value=ast.Constant(value=1)))
        outs.extend(_finish(tree))
    return outs


_RULES = [
    _rule_append_return_len,
    _rule_trailing_return_len,
    _rule_len_minus_one,
    _rule_sentinel_returns,
    _rule_guard_empty,
    _rule_return_name_plus1,
    _rule_while_increment,
]


def _specific_variants(source):
    """Level-1 rule applications plus level-2 combinations (rule on top of a
    rule), deduplicated, in priority order."""
    seen = {source}
    out = []

    def add(items):
        for it in items:
            if it and it not in seen:
                seen.add(it)
                out.append(it)

    def apply_rules(src):
        got = []
        for rule in _RULES:
            try:
                got.extend(rule(src) or [])
            except Exception:
                pass
        return got

    add(apply_rules(source))
    for v in list(out)[:16]:
        if len(out) > 90:
            break
        add(apply_rules(v))
    return out[:120]


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------

def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None


def _repair(source):
    if not isinstance(source, str):
        return None
    if _parse(source) is None:
        return None

    def check(cands, max_checks):
        try:
            return first_passing(iter(cands), ENTRY, TESTS, source,
                                 max_rps=MAX_RPS, max_checks=max_checks)
        except Exception:
            return None

    def gen(src, edits, budget):
        try:
            return candidates_generic(src, max_edits=edits, budget=budget)
        except Exception:
            return iter(())

    # Stage 0: the submission might already pass everything.
    got = check([source], 5)
    if got is not None:
        return got

    variants = _specific_variants(source)

    # Stage 1: problem-specific rewrites (missing/wrong tail return, empty
    # guard, sentinel returns, missing increment, and their combinations).
    got = check(variants, 250)
    if got is not None:
        return got

    # Stage 2: generic single-edit search on the original.
    got = check(gen(source, 1, 2000), 800)
    if got is not None:
        return got

    # Stage 3: one generic edit on top of each specific rewrite
    # (e.g. drop the '- 1' in the tail return AND flip >= to >).
    for v in variants[:12]:
        got = check(gen(v, 1, 500), 150)
        if got is not None:
            return got

    # Stage 4: generic double-edit search on the original.
    got = check(gen(source, 2, 2500), 900)
    if got is not None:
        return got

    return None
