```python
"""Local, LLM-free automatic repair for the `unique_in_order` assignment.

Round-3 revision.  Round 2 fixed the plumbing (defensive imports, local
sandboxed verification, signature-tolerant `first_passing` calls) and now
repairs every sampled mutant, but still misses `crafted_02.py`:

    def unique_in_order(lst):
        return list(set(lst))

Hand-trace of the round-2 pipeline on that source: the function has no
assignments (so no accumulator rules fire), no `if` statements (so no guard
rules fire), no membership tests, no comparisons, no numeric constants and
no `range` calls (so the generic single-edit mutator produces *zero*
variants).  The only candidate ever generated is the empty-input guard,
which cannot help.  The failure is therefore not the RPS cap or a guard
rejecting a good patch -- the required edit is simply never produced,
because no rule covers the "global dedup" anti-pattern in which `set()`
(or `frozenset()` / `dict.fromkeys()`) removes *all* duplicates and
destroys order, instead of collapsing only *adjacent* duplicates.

New in this revision (Rule E): when such a dedup call is found, rewrite it
in place -- and, as a coarser fallback, rewrite the enclosing `return`
expression -- into an order-preserving, adjacency-only comprehension over
the same sequence:

    [v for i, v in enumerate(seq) if not i or v != seq[i - 1]]

This keeps the student's single-expression style, handles the empty input
for free, and works for unhashable-free and mixed-type inputs alike.  The
locally verified candidates are still handed to `first_passing` (with the
0.35 patch-size cap) for the official verdict, exactly as before; nothing
that already works has been changed.
"""

import ast
import copy
import difflib
import io
import sys
import tokenize

try:
    from coep.repairlib import first_passing as _lib_first_passing
except Exception:
    _lib_first_passing = None

try:
    from coep.repairlib import candidates_generic as _lib_candidates_generic
except Exception:
    _lib_candidates_generic = None

try:
    from coep.evaluate import rps as _lib_rps
except Exception:
    _lib_rps = None

ENTRY = "unique_in_order"
MAX_RPS = 0.35

TESTS = [
    {"args": [[]], "expected": []},
    {"args": [[1]], "expected": [1]},
    {"args": [[1, 1]], "expected": [1]},
    {"args": [[1, 1, 2, 1]], "expected": [1, 2, 1]},
    {"args": [[1, 2, 3]], "expected": [1, 2, 3]},
    {"args": [[1, 1, 1, 1]], "expected": [1]},
    {"args": [["a", "a", "b", "b", "a"]], "expected": ["a", "b", "a"]},
    {"args": [[1, "1", 1]], "expected": [1, "1", 1]},
    {"args": [[2, 2, 2, 3, 3, 1, 1, 2]], "expected": [2, 3, 1, 2]},
    {"args": [["A", "a", "A"]], "expected": ["A", "a", "A"]},
    {"args": [[0, 0, 0]], "expected": [0]},
    {"args": [[5, 4, 4, 5, 5, 4]], "expected": [5, 4, 5, 4]},
    {"args": [["x"]], "expected": ["x"]},
    {"args": [[1, 2, 2, 3, 3, 3, 4]], "expected": [1, 2, 3, 4]},
]


# ---------------------------------------------------------------------------
# Sandboxed local test runner (deep-copied inputs, step-limited execution)
# ---------------------------------------------------------------------------

_STEP_LIMIT = 120000


def _load_entry(source):
    ns = {"__name__": "__candidate__"}
    exec(compile(source, "<candidate>", "exec"), ns)
    fn = ns.get(ENTRY)
    if not callable(fn):
        raise ValueError("entry point missing")
    return fn


def _call_limited(fn, args):
    steps = [0]

    def tracer(frame, event, arg):
        steps[0] += 1
        if steps[0] > _STEP_LIMIT:
            raise RuntimeError("step budget exceeded")
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        return fn(*copy.deepcopy(args))
    finally:
        sys.settrace(old)


def _passes_locally(source):
    try:
        fn = _load_entry(source)
    except Exception:
        return False
    for t in TESTS:
        try:
            out = _call_limited(fn, t["args"])
        except Exception:
            return False
        if out != t["expected"]:
            return False
    return True


def _failure_kinds(source):
    kinds = set()
    try:
        fn = _load_entry(source)
    except Exception:
        return {"compile"}
    for t in TESTS:
        try:
            out = _call_limited(fn, t["args"])
        except Exception as exc:
            kinds.add(type(exc).__name__)
        else:
            if out != t["expected"]:
                kinds.add("wrong-answer")
    return kinds


# ---------------------------------------------------------------------------
# Patch-size estimation (uses coep.evaluate.rps when available)
# ---------------------------------------------------------------------------

def _tokens(src):
    try:
        skip = {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                tokenize.DEDENT, tokenize.COMMENT, tokenize.ENDMARKER}
        enc = getattr(tokenize, "ENCODING", None)
        if enc is not None:
            skip.add(enc)
        out = []
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in skip:
                continue
            out.append(tok.string)
        return out
    except Exception:
        return src.split()


def _patch_size(orig, cand):
    if _lib_rps is not None:
        vals = []
        for args in ((orig, cand), (cand, orig)):
            try:
                v = _lib_rps(*args)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if vals:
            return max(vals)
    a, b = _tokens(orig), _tokens(cand)
    sm = difflib.SequenceMatcher(None, a, b)
    same = sum(m.size for m in sm.get_matching_blocks())
    return ((len(a) - same) + (len(b) - same)) / max(len(a), 1)


# ---------------------------------------------------------------------------
# Official validation via first_passing, tolerant of signature differences
# ---------------------------------------------------------------------------

def _call_first_passing(cands, source):
    """Return (result, completed).  `completed` is True when at least one
    call convention executed without raising, i.e. the verdict is real."""
    cands = [c for c in cands if isinstance(c, str)]
    if not cands or _lib_first_passing is None:
        return None, False
    attempts = [
        ((cands, ENTRY, copy.deepcopy(TESTS), source),
         {"max_rps": MAX_RPS, "max_checks": 2000}),
        ((cands, ENTRY, copy.deepcopy(TESTS), source), {"max_rps": MAX_RPS}),
        ((cands, ENTRY, copy.deepcopy(TESTS), source), {}),
        ((cands, ENTRY, copy.deepcopy(TESTS)), {"max_rps": MAX_RPS}),
        ((cands, ENTRY, copy.deepcopy(TESTS)), {}),
    ]
    completed = False
    for args, kwargs in attempts:
        try:
            res = _lib_first_passing(*args, **kwargs)
        except Exception:
            continue
        completed = True
        if isinstance(res, str):
            return res, True
    return None, completed


# ---------------------------------------------------------------------------
# Small AST helpers
# ---------------------------------------------------------------------------

def _name(n):
    return ast.Name(id=n, ctx=ast.Load())


def _last(n):
    return ast.Subscript(
        value=_name(n),
        slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
        ctx=ast.Load(),
    )


def _is_empty_list_value(v):
    if isinstance(v, ast.List) and not v.elts:
        return True
    if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
            and v.func.id == "list" and not v.args and not v.keywords):
        return True
    return False


def _is_listish_value(v):
    if isinstance(v, ast.List):
        return True
    if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
            and v.func.id == "list"):
        return True
    if isinstance(v, ast.Subscript) and isinstance(v.slice, ast.Slice):
        return True
    return False


def _is_global_dedup_call(node):
    """`set(x)`, `frozenset(x)`, `dict.fromkeys(x)`, `OrderedDict.fromkeys(x)`
    with exactly one positional argument: removes ALL duplicates (and, for
    the set forms, destroys order) instead of collapsing adjacent runs."""
    if (not isinstance(node, ast.Call) or node.keywords
            or len(node.args) != 1):
        return False
    f = node.func
    if isinstance(f, ast.Name) and f.id in ("set", "frozenset"):
        return True
    if (isinstance(f, ast.Attribute) and f.attr == "fromkeys"
            and isinstance(f.value, ast.Name)
            and f.value.id in ("dict", "OrderedDict")):
        return True
    return False


def _dedup_comp(seq):
    """[v for i, v in enumerate(seq) if not i or v != seq[i - 1]]"""
    return ast.ListComp(
        elt=ast.Name(id="v", ctx=ast.Load()),
        generators=[ast.comprehension(
            target=ast.Tuple(
                elts=[ast.Name(id="i", ctx=ast.Store()),
                      ast.Name(id="v", ctx=ast.Store())],
                ctx=ast.Store()),
            iter=ast.Call(func=_name("enumerate"), args=[_name(seq)],
                          keywords=[]),
            ifs=[ast.BoolOp(op=ast.Or(), values=[
                ast.UnaryOp(op=ast.Not(), operand=_name("i")),
                ast.Compare(
                    left=_name("v"), ops=[ast.NotEq()],
                    comparators=[ast.Subscript(
                        value=_name(seq),
                        slice=ast.BinOp(left=_name("i"), op=ast.Sub(),
                                        right=ast.Constant(1)),
                        ctx=ast.Load())])])],
            is_async=0)])


def _nth_variant(source, predicate, replace, n):
    """Re-parse `source`, apply `replace` to the n-th node matching
    `predicate` (in traversal order), return the new source string."""
    tree = ast.parse(source)
    counter = [0]

    class T(ast.NodeTransformer):
        def visit(self, node):
            node = self.generic_visit(node)
            try:
                hit = predicate(node)
            except Exception:
                hit = False
            if hit:
                idx = counter[0]
                counter[0] += 1
                if idx == n:
                    try:
                        new = replace(node)
                    except Exception:
                        new = None
                    if new is not None:
                        return new
            return node

    new_tree = T().visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


# ---------------------------------------------------------------------------
# Problem-specific rewrite rules
# ---------------------------------------------------------------------------

def _specific_variants(source, prioritize_guards=False):
    try:
        tree = ast.parse(source)
    except Exception:
        return []

    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == ENTRY:
            func = node
            break
    if func is None:
        return []

    all_args = list(getattr(func.args, "posonlyargs", [])) + list(func.args.args)
    param = all_args[0].arg if all_args else None

    # Accumulator variables: names assigned a list-like value in the function.
    accs = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and _is_listish_value(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    accs.append(t.id)
    accs = [a for a in dict.fromkeys(accs) if a != param]

    # Loop-index names: `for i in ...` and `for i, v in enumerate(...)`.
    idx_names = []
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                idx_names.append(node.target.id)
            elif (isinstance(node.target, ast.Tuple) and node.target.elts
                  and isinstance(node.target.elts[0], ast.Name)
                  and isinstance(node.iter, ast.Call)
                  and isinstance(node.iter.func, ast.Name)
                  and node.iter.func.id == "enumerate"):
                idx_names.append(node.target.elts[0].id)
    idx_names = list(dict.fromkeys(idx_names))

    list_names = list(dict.fromkeys(accs + ([param] if param else [])))

    guards, others = [], []

    def _safe(pred, x):
        try:
            return bool(pred(x))
        except Exception:
            return False

    def add(bucket, pred, rep, max_sites=8):
        try:
            n_sites = sum(1 for x in ast.walk(tree) if _safe(pred, x))
        except Exception:
            return
        for i in range(min(n_sites, max_sites)):
            try:
                src = _nth_variant(source, pred, rep, i)
            except Exception:
                continue
            if isinstance(src, str) and src != source:
                bucket.append(src)

    def pred_func(node):
        return isinstance(node, ast.FunctionDef) and node.name == ENTRY

    # --- Rule A: insert an empty-input guard at the top of the function.
    if param:
        def rep_guard(node, p=param):
            g = ast.If(
                test=ast.UnaryOp(op=ast.Not(), operand=_name(p)),
                body=[ast.Return(value=ast.List(elts=[], ctx=ast.Load()))],
                orelse=[])
            node.body = [g] + node.body
            return node

        add(guards, pred_func, rep_guard)

    # --- Rule 1: wrong initialization `acc = []` -> `acc = param[:1]`
    if param:
        def pred_init(node):
            return isinstance(node, ast.Assign) and _is_empty_list_value(node.value)

        def rep_init(node, p=param):
            node.value = ast.Subscript(
                value=_name(p),
                slice=ast.Slice(lower=None, upper=ast.Constant(1), step=None),
                ctx=ast.Load(),
            )
            return node

        add(others, pred_init, rep_init)

    # --- Rule B: `[param[0]]` -> `param[:1]` (empty-input crash fix).
    if param:
        def pred_first(node, p=param):
            return (isinstance(node, ast.List) and len(node.elts) == 1
                    and isinstance(node.elts[0], ast.Subscript)
                    and isinstance(node.elts[0].value, ast.Name)
                    and node.elts[0].value.id == p
                    and isinstance(node.elts[0].slice, ast.Constant)
                    and node.elts[0].slice.value == 0)

        def rep_first(node, p=param):
            return ast.Subscript(
                value=_name(p),
                slice=ast.Slice(lower=None, upper=ast.Constant(1), step=None),
                ctx=ast.Load())

        add(others, pred_first, rep_first)

    # --- Rule 2: missing emptiness / first-iteration guards on `if` tests.
    def pred_if(node):
        return isinstance(node, ast.If)

    for acc in accs:
        def rep_or_not(node, a=acc):
            node.test = ast.BoolOp(
                op=ast.Or(),
                values=[ast.UnaryOp(op=ast.Not(), operand=_name(a)), node.test])
            return node

        def rep_and(node, a=acc):
            node.test = ast.BoolOp(op=ast.And(), values=[_name(a), node.test])
            return node

        add(guards, pred_if, rep_or_not)
        add(guards, pred_if, rep_and)

    for iname in idx_names:
        def rep_or_zero(node, i=iname):
            node.test = ast.BoolOp(
                op=ast.Or(),
                values=[ast.Compare(left=_name(i), ops=[ast.Eq()],
                                    comparators=[ast.Constant(0)]),
                        node.test])
            return node

        def rep_and_idx(node, i=iname):
            node.test = ast.BoolOp(op=ast.And(), values=[_name(i), node.test])
            return node

        add(guards, pred_if, rep_or_zero)
        add(guards, pred_if, rep_and_idx)

    # --- Rule 3: missing `i == 0 or` guard in a comprehension filter.
    def pred_comp(node):
        return (isinstance(node, ast.comprehension) and node.ifs
                and isinstance(node.target, ast.Name))

    def rep_comp(node):
        tgt = node.target.id
        node.ifs = [ast.BoolOp(
            op=ast.Or(),
            values=[ast.Compare(left=_name(tgt), ops=[ast.Eq()],
                                comparators=[ast.Constant(0)]),
                    node.ifs[0]])] + node.ifs[1:]
        return node

    add(others, pred_comp, rep_comp)

    # --- Rule 4: membership test (removes ALL duplicates) -> adjacency test.
    if accs:
        def pred_member(node):
            return (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], (ast.In, ast.NotIn))
                    and isinstance(node.comparators[0], ast.Name)
                    and node.comparators[0].id in accs)

        def rep_member(node):
            a = node.comparators[0].id
            if isinstance(node.ops[0], ast.NotIn):
                return ast.BoolOp(
                    op=ast.Or(),
                    values=[ast.UnaryOp(op=ast.Not(), operand=_name(a)),
                            ast.Compare(left=_last(a), ops=[ast.NotEq()],
                                        comparators=[node.left])])
            return ast.BoolOp(
                op=ast.And(),
                values=[_name(a),
                        ast.Compare(left=_last(a), ops=[ast.Eq()],
                                    comparators=[node.left])])

        add(others, pred_member, rep_member)

    # --- Rule E (new): global dedup via set()/frozenset()/dict.fromkeys()
    # removes non-adjacent duplicates and (for sets) destroys order.  E1
    # rewrites the dedup call itself, in place, into an order-preserving
    # adjacency-only comprehension over the same named sequence, keeping
    # every surrounding construct the student wrote (e.g. the outer
    # `list(...)` wrapper).  E2, coarser, rewrites the whole `return`
    # expression that contains such a call (covers wrappers like
    # `sorted(set(x))` whose outer call would still break the order).
    def pred_dedup(node):
        return (_is_global_dedup_call(node)
                and isinstance(node.args[0], ast.Name))

    def rep_dedup(node):
        return _dedup_comp(node.args[0].id)

    add(others, pred_dedup, rep_dedup)

    if param:
        def pred_ret_dedup(node):
            return (isinstance(node, ast.Return) and node.value is not None
                    and any(_is_global_dedup_call(x)
                            for x in ast.walk(node.value)))

        def rep_ret_dedup(node, p=param):
            node.value = _dedup_comp(p)
            return node

        add(others, pred_ret_dedup, rep_ret_dedup)

    # --- Rules 5/6: wrong list variable in a subscript / return.
    if len(list_names) >= 2:
        def pred_sub(node):
            return (isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in list_names)

        for other in list_names:
            def rep_sub(node, o=other):
                if node.value.id == o:
                    return None
                node.value = _name(o)
                return node

            add(others, pred_sub, rep_sub)

        def pred_ret(node):
            return (isinstance(node, ast.Return)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in list_names)

        for other in list_names:
            def rep_ret(node, o=other):
                if node.value.id == o:
                    return None
                node.value = _name(o)
                return node

            add(others, pred_ret, rep_ret)

    # --- Rule C: `acc = acc.append(v)` misuse -> plain `acc.append(v)`.
    def pred_appassign(node):
        return (isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "append")

    def rep_appassign(node):
        return ast.Expr(value=node.value)

    add(others, pred_appassign, rep_appassign)

    # --- Rule D: missing return statement -> append `return <acc>`.
    has_return = any(isinstance(n, ast.Return) and n.value is not None
                     for n in ast.walk(func))
    if not has_return:
        for nm in list_names:
            def rep_addret(node, nm=nm):
                node.body = list(node.body) + [ast.Return(value=_name(nm))]
                return node

            add(others, pred_func, rep_addret)

    ordered = (guards + others) if prioritize_guards else (others + guards)
    return list(dict.fromkeys(ordered))


# ---------------------------------------------------------------------------
# Local generic mutation engine (no library dependency)
# ---------------------------------------------------------------------------

_CMP_SWAPS = {
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
    ast.Lt: (ast.LtE, ast.Gt),
    ast.LtE: (ast.Lt, ast.GtE),
    ast.Gt: (ast.GtE, ast.Lt),
    ast.GtE: (ast.Gt, ast.LtE),
    ast.In: (ast.NotIn,),
    ast.NotIn: (ast.In,),
    ast.Is: (ast.IsNot,),
    ast.IsNot: (ast.Is,),
}


def _variants_for(node):
    vs = []
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        for alt in _CMP_SWAPS.get(type(node.ops[0]), ()):
            def f(n=node, a=alt):
                n.ops = [a()]
                return n
            vs.append(f)
    if isinstance(node, ast.BoolOp):
        def f_bool(n=node):
            n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
            return n
        vs.append(f_bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        vs.append(lambda n=node: n.operand)
    if isinstance(node, ast.If):
        def f_neg(n=node):
            n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
            return n
        vs.append(f_neg)
    if (isinstance(node, ast.Constant) and type(node.value) is int
            and abs(node.value) <= 4):
        for d in (1, -1):
            def f_c(n=node, d=d):
                return ast.Constant(n.value + d)
            vs.append(f_c)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        def f_pm(n=node):
            n.op = ast.Sub() if isinstance(n.op, ast.Add) else ast.Add()
            return n
        vs.append(f_pm)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "range"):
        if len(node.args) == 1:
            def f_r1(n=node):
                n.args = [ast.Constant(1), n.args[0]]
                return n
            vs.append(f_r1)
        elif len(node.args) == 2:
            def f_r2(n=node):
                n.args = [n.args[1]]
                return n
            vs.append(f_r2)
        if node.args:
            for op in (ast.Sub, ast.Add):
                def f_r3(n=node, op=op):
                    n.args = list(n.args[:-1]) + [
                        ast.BinOp(left=n.args[-1], op=op(),
                                  right=ast.Constant(1))]
                    return n
                vs.append(f_r3)
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Name):
        for op in (ast.Sub, ast.Add):
            def f_s(n=node, op=op):
                n.slice = ast.BinOp(left=n.slice, op=op(),
                                    right=ast.Constant(1))
                return n
            vs.append(f_s)
    return vs


class _Mutator(ast.NodeTransformer):
    def __init__(self, target, banned):
        self.target = target
        self.banned = banned
        self.count = 0
        self.applied = False

    def visit(self, node):
        node = self.generic_visit(node)
        if id(node) in self.banned:
            return node
        try:
            vs = _variants_for(node)
        except Exception:
            vs = []
        for v in vs:
            idx = self.count
            self.count += 1
            if (self.target is not None and idx == self.target
                    and not self.applied):
                try:
                    new = v()
                except Exception:
                    new = None
                if new is not None:
                    self.applied = True
                    return new
        return node


def _apply_generic(source, target):
    """target=None: return the number of available single mutations.
    Otherwise apply the target-th mutation and return the new source."""
    tree = ast.parse(source)
    banned = set()
    for w in ast.walk(tree):
        if isinstance(w, ast.While):  # avoid manufacturing infinite loops
            for sub in ast.walk(w.test):
                banned.add(id(sub))
    m = _Mutator(target, banned)
    new_tree = m.visit(tree)
    if target is None:
        return m.count
    if not m.applied:
        return None
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


def _generic_singles(source, cap=500):
    try:
        total = _apply_generic(source, None)
    except Exception:
        return []
    out = []
    for t in range(min(int(total), cap)):
        try:
            s = _apply_generic(source, t)
        except Exception:
            continue
        if isinstance(s, str) and s != source:
            out.append(s)
    return out


def _one_more_edit(bases, base_cap, per_base, cap_total):
    out = []
    for b in bases[:base_cap]:
        for s in _generic_singles(b, cap=per_base):
            out.append(s)
            if len(out) >= cap_total:
                return out
    return out


def _lib_generic_stream(source, cap=400):
    if _lib_candidates_generic is None:
        return []
    out = []
    for kw in ({"max_edits": 2, "budget": 800}, {"max_edits": 2}, {}):
        try:
            it = _lib_candidates_generic(source, **kw)
        except TypeError:
            continue
        except Exception:
            return out
        try:
            for c in it:
                if isinstance(c, str):
                    out.append(c)
                if len(out) >= cap:
                    break
        except Exception:
            pass
        return out
    return out


# ---------------------------------------------------------------------------
# Repair entry point
# ---------------------------------------------------------------------------

def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    # Light dispatch: runtime IndexErrors usually mean a missing
    # emptiness/first-iteration guard, so try guard rewrites first then.
    try:
        prioritize_guards = "IndexError" in _failure_kinds(source)
    except Exception:
        prioritize_guards = False

    spec = _specific_variants(source, prioritize_guards)
    singles = _generic_singles(source, cap=500)
    lib_gen = _lib_generic_stream(source, cap=400)
    combos = _one_more_edit(spec, base_cap=15, per_base=80, cap_total=800)
    pairs = _one_more_edit(singles, base_cap=30, per_base=40, cap_total=800)

    ordered, seen = [], set()
    for c in [source] + spec + singles + lib_gen + combos + pairs:
        if isinstance(c, str) and c not in seen:
            seen.add(c)
            ordered.append(c)
        if len(ordered) >= 3000:
            break

    # Verify candidates locally (safe runner), smallest patch first.
    found = []
    for c in ordered:
        try:
            ok = _passes_locally(c)
        except Exception:
            ok = False
        if ok:
            found.append(c)
            if len(found) >= 8:
                break
    try:
        found.sort(key=lambda c: _patch_size(source, c))
    except Exception:
        pass

    if found:
        res, completed = _call_first_passing(found, source)
        if isinstance(res, str):
            return res
        # first_passing missing/unusable, or its verdict could not be
        # obtained: fall back to the best locally verified candidate that
        # respects the patch-size cap.
        for c in found:
            try:
                if _patch_size(source, c) <= MAX_RPS:
                    return c
            except Exception:
                continue
        return None

    # The local runner found nothing.  As a safety net (in case the local
    # sandbox itself is what is broken in this environment), let the
    # library validator scan the full candidate list.
    res, _completed = _call_first_passing(ordered[:800], source)
    return res if isinstance(res, str) else None


def repair(source: str) -> "str | None":
    try:
        return _repair(source)
    except Exception:
        return None
```
