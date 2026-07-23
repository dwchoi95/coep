"""Local, LLM-free automatic repair system for the `is_palindrome` assignment.

Revision notes (round 2): the previous version produced no patch for any
sample, which pointed at systematic internal failures rather than weak
rules.  This revision hardens every fragile point:

  * No reliance on optional repairlib names (`chain` is now taken from
    itertools; `candidates_generic` is looked up defensively with getattr).
  * `first_passing` is called through a signature-adaptive shim: it first
    tries the keyword form with the explicit patch-size cap (max_rps=0.35)
    and degrades to plainer positional forms on TypeError, so an argument
    mismatch can never silently disable validation.
  * The pipeline is a simple staged search, each stage validated
    independently: original -> problem-specific AST rewrites -> generic
    1-edit search -> built-in micro-mutations (a local backup 1-edit
    mutator that does not depend on repairlib internals) -> two-fix
    combinations -> generic 2-edit search.
  * Candidate lists are bounded and pre-screened only by "parses as
    Python" (never by anything semantic), so no over-restrictive filter
    can drop a viable candidate.

`repair(source)` returns a full repaired module source (str) or None and
never raises.
"""

import ast
import copy
import itertools

from coep import repairlib as _repairlib

first_passing = _repairlib.first_passing
candidates_generic = getattr(_repairlib, "candidates_generic", None)

ENTRY = "is_palindrome"

TESTS = [
    {"args": [""], "expected": True},
    {"args": ["a"], "expected": True},
    {"args": ["abba"], "expected": True},
    {"args": ["abc"], "expected": False},
    {"args": ["A man, a plan, a canal: Panama"], "expected": True},
    {"args": ["race a car"], "expected": False},
    {"args": ["No 'x' in Nixon"], "expected": True},
    {"args": ["12321"], "expected": True},
    {"args": ["1231"], "expected": False},
    {"args": ["!!!"], "expected": True},
    {"args": ["Aa"], "expected": True},
    {"args": ["0P"], "expected": False},
    {"args": ["Was it a car or a cat I saw?"], "expected": True},
    {"args": ["ab"], "expected": False},
]


# --------------------------------------------------------------------------
# Validation shim: adapt to whatever signature first_passing actually has.
# --------------------------------------------------------------------------

_SIG = {"idx": None}

_CALLS = [
    lambda cands, src: first_passing(cands, ENTRY, TESTS, src, max_rps=0.35),
    lambda cands, src: first_passing(cands, ENTRY, TESTS, src),
    lambda cands, src: first_passing(cands, ENTRY, TESTS),
]


def _validate(cands, source):
    """Run first_passing over a bounded candidate list; None on failure."""
    try:
        cands = [c for c in cands
                 if isinstance(c, str) and c and _parse(c) is not None]
    except Exception:
        return None
    if not cands:
        return None
    if _SIG["idx"] is not None:
        try:
            return _CALLS[_SIG["idx"]](list(cands), source)
        except Exception:
            return None
    for i, call in enumerate(_CALLS):
        try:
            res = call(list(cands), source)
        except TypeError:
            continue
        except Exception:
            return None
        _SIG["idx"] = i
        return res
    return None


def _generic(source, edits, cap):
    """Defensive wrapper around repairlib's generic edit search."""
    if candidates_generic is None:
        return []
    attempts = (
        lambda: candidates_generic(source, max_edits=edits),
        lambda: candidates_generic(source, edits),
        lambda: candidates_generic(source),
    )
    for attempt in attempts:
        try:
            gen = attempt()
        except TypeError:
            continue
        except Exception:
            return []
        try:
            return list(itertools.islice(iter(gen), cap))
        except Exception:
            return []
    return []


# --------------------------------------------------------------------------
# AST machinery: apply a single-replacement rule at each site (and all sites)
# --------------------------------------------------------------------------

def _parse(src):
    try:
        return ast.parse(src)
    except Exception:
        return None


class _Replacer(ast.NodeTransformer):
    """Replace the k-th (pre-order) node matched by `rule`; k=None -> all."""

    def __init__(self, rule, k):
        self.rule = rule
        self.k = k
        self.i = -1

    def visit(self, node):
        try:
            rep = self.rule(node)
        except Exception:
            rep = None
        if rep is not None:
            self.i += 1
            if self.k is None or self.i == self.k:
                return rep  # do not recurse into the replacement
        self.generic_visit(node)
        return node


def _apply_rule(source, rule):
    out = []
    tree = _parse(source)
    if tree is None:
        return out
    count = 0
    for node in ast.walk(tree):
        try:
            if rule(node) is not None:
                count += 1
        except Exception:
            pass
    if count == 0:
        return out
    ks = list(range(min(count, 12)))
    if count > 1:
        ks.append(None)  # variant applying the rule at every site
    for k in ks:
        t2 = _parse(source)
        if t2 is None:
            continue
        try:
            new_tree = _Replacer(rule, k).visit(t2)
            ast.fix_missing_locations(new_tree)
            cand = ast.unparse(new_tree)
        except Exception:
            continue
        if cand and cand != source:
            out.append(cand)
    return out


# --------------------------------------------------------------------------
# Small AST helpers
# --------------------------------------------------------------------------

def _same(a, b):
    try:
        return ast.dump(a) == ast.dump(b)
    except Exception:
        return False


def _has_case(node):
    return any(
        isinstance(n, ast.Attribute) and n.attr in ("lower", "casefold", "upper")
        for n in ast.walk(node)
    )


def _lower_call(expr):
    return ast.Call(
        func=ast.Attribute(value=expr, attr="lower", ctx=ast.Load()),
        args=[], keywords=[],
    )


def _rev_slice(expr):
    return ast.Subscript(
        value=expr,
        slice=ast.Slice(lower=None, upper=None,
                        step=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1))),
        ctx=ast.Load(),
    )


def _slice_upper_only(n):
    return (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
            and n.slice.lower is None and n.slice.upper is not None
            and n.slice.step is None)


def _slice_lower_only(n):
    return (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Slice)
            and n.slice.lower is not None and n.slice.upper is None
            and n.slice.step is None)


def _subst_template(template, node):
    expr = ast.parse(template, mode="eval").body

    class _S(ast.NodeTransformer):
        def visit_Name(self, n):
            if n.id == "__X__":
                return copy.deepcopy(node)
            return n

    return _S().visit(expr)


# --------------------------------------------------------------------------
# Problem-specific rewrite rules (each: node -> replacement node or None)
# --------------------------------------------------------------------------

def rule_isalnum(node):
    # Wrong filter predicate: isalpha/isdigit/... instead of isalnum.
    if isinstance(node, ast.Attribute) and node.attr in (
            "isalpha", "isdigit", "isdecimal", "isnumeric"):
        return ast.Attribute(value=copy.deepcopy(node.value),
                             attr="isalnum", ctx=ast.Load())
    return None


def rule_notspace(node):
    # `not c.isspace()` only drops spaces; should be `c.isalnum()`.
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)
            and isinstance(node.operand, ast.Call)
            and isinstance(node.operand.func, ast.Attribute)
            and node.operand.func.attr == "isspace"
            and not node.operand.args):
        return ast.Call(
            func=ast.Attribute(value=copy.deepcopy(node.operand.func.value),
                               attr="isalnum", ctx=ast.Load()),
            args=[], keywords=[])
    return None


def rule_call_attr(node):
    # `if c.isalnum` (missing parens) in a comprehension filter.
    if isinstance(node, (ast.GeneratorExp, ast.ListComp)) and node.generators:
        g = node.generators[0]
        if len(g.ifs) == 1 and isinstance(g.ifs[0], ast.Attribute) \
                and g.ifs[0].attr.startswith("is"):
            new = copy.deepcopy(node)
            new.generators[0].ifs[0] = ast.Call(
                func=new.generators[0].ifs[0], args=[], keywords=[])
            return new
    return None


def rule_call_elt(node):
    # `c.lower` (missing parens) as a comprehension element.
    if isinstance(node, (ast.GeneratorExp, ast.ListComp)) \
            and isinstance(node.elt, ast.Attribute) \
            and node.elt.attr in ("lower", "casefold"):
        new = copy.deepcopy(node)
        new.elt = ast.Call(func=new.elt, args=[], keywords=[])
        return new
    return None


def rule_lower_elt(node):
    # Missing case fold: lowercase the comprehension element.
    if isinstance(node, (ast.GeneratorExp, ast.ListComp)) \
            and isinstance(node.elt, ast.Name) and not _has_case(node):
        new = copy.deepcopy(node)
        new.elt = _lower_call(new.elt)
        return new
    return None


def rule_lower_iter(node):
    # Missing case fold: lowercase the iterated string.
    if isinstance(node, (ast.GeneratorExp, ast.ListComp)) \
            and node.generators and not _has_case(node):
        new = copy.deepcopy(node)
        new.generators[0].iter = _lower_call(new.generators[0].iter)
        return new
    return None


def rule_lower_cmp(node):
    # Missing case fold at the comparison site (two-pointer style).
    if (isinstance(node, ast.Compare) and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
            and isinstance(node.left, (ast.Name, ast.Subscript))
            and isinstance(node.comparators[0], (ast.Name, ast.Subscript))
            and not _has_case(node)):
        return ast.Compare(
            left=_lower_call(copy.deepcopy(node.left)),
            ops=[type(node.ops[0])()],
            comparators=[_lower_call(copy.deepcopy(node.comparators[0]))])
    return None


def rule_halfsplit(node):
    # `t[:h] == t[h:]` -> `t[:h] == t[::-1][:h]` (works for odd lengths too).
    if (isinstance(node, ast.Compare) and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
        L, R = node.left, node.comparators[0]
        if _slice_upper_only(L) and _slice_lower_only(R) \
                and _same(L.value, R.value):
            new_r = ast.Subscript(
                value=_rev_slice(copy.deepcopy(L.value)),
                slice=ast.Slice(lower=None,
                                upper=copy.deepcopy(L.slice.upper), step=None),
                ctx=ast.Load())
            return ast.Compare(left=copy.deepcopy(L), ops=[ast.Eq()],
                               comparators=[new_r])
    return None


def rule_whole_reverse(node):
    # Broken slice comparison over one variable -> `t == t[::-1]`.
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
        return None
    L, R = node.left, node.comparators[0]

    def _ok(x):
        return isinstance(x, ast.Name) or (
            isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Slice))

    if not (_ok(L) and _ok(R)):
        return None
    if isinstance(L, ast.Name) and isinstance(R, ast.Name):
        return None  # nothing sliced; unrelated comparison
    bl = L.value if isinstance(L, ast.Subscript) else L
    br = R.value if isinstance(R, ast.Subscript) else R
    if not (isinstance(bl, ast.Name) and isinstance(br, ast.Name)
            and bl.id == br.id):
        return None
    base = ast.Name(id=bl.id, ctx=ast.Load())
    rev = _rev_slice(ast.Name(id=bl.id, ctx=ast.Load()))
    cand = ast.Compare(left=base, ops=[ast.Eq()], comparators=[rev])
    if _same(cand, node):
        return None
    return cand


def rule_reversed(node):
    # `reversed(t)` compared with a string is never equal; use `t[::-1]`.
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "reversed" and len(node.args) == 1
            and not node.keywords):
        return _rev_slice(copy.deepcopy(node.args[0]))
    return None


def rule_init_fix(node):
    # Two-pointer init should be `i, j = 0, len(x) - 1`.
    if not (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Tuple)
            and len(node.targets[0].elts) == 2
            and isinstance(node.value, ast.Tuple)
            and len(node.value.elts) == 2):
        return None
    a, b = node.value.elts
    changed = False
    new_a = copy.deepcopy(a)
    if isinstance(a, ast.Constant) and isinstance(a.value, int) \
            and not isinstance(a.value, bool) and a.value != 0:
        new_a = ast.Constant(0)
        changed = True
    len_call = None
    for n in ast.walk(b):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "len":
            len_call = n
            break
    new_b = copy.deepcopy(b)
    if len_call is not None:
        already_ok = (isinstance(b, ast.BinOp) and isinstance(b.op, ast.Sub)
                      and b.left is len_call
                      and isinstance(b.right, ast.Constant)
                      and b.right.value == 1)
        if not already_ok:
            new_b = ast.BinOp(left=copy.deepcopy(len_call), op=ast.Sub(),
                              right=ast.Constant(1))
            changed = True
    if not changed:
        return None
    return ast.Assign(
        targets=[copy.deepcopy(node.targets[0])],
        value=ast.Tuple(elts=[new_a, new_b], ctx=ast.Load()))


def _mk_filter_rules(source):
    # Missing filtering step entirely: wrap the cleaning expression in a
    # character filter. Only relevant if no alnum filtering exists at all.
    if "isalnum" in source or "isalpha" in source:
        return []
    attrs = ("lower", "casefold", "replace", "strip", "join", "split")

    def _match(node):
        return (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in attrs)

    def r_join(node):
        if _match(node):
            return _subst_template(
                "''.join(_ch for _ch in __X__ if _ch.isalnum())", node)
        return None

    def r_filter(node):
        if _match(node):
            return _subst_template(
                "''.join(filter(str.isalnum, __X__))", node)
        return None

    return [r_join, r_filter]


def _specific_list(source, cap=80):
    try:
        rules = ([rule_isalnum, rule_notspace, rule_call_attr]
                 + _mk_filter_rules(source)
                 + [rule_lower_elt, rule_lower_iter, rule_lower_cmp,
                    rule_call_elt, rule_halfsplit, rule_whole_reverse,
                    rule_reversed, rule_init_fix])
    except Exception:
        return []
    out = []
    seen = {source}
    for rule in rules:
        try:
            cands = _apply_rule(source, rule)
        except Exception:
            continue
        for cand in cands:
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
            if len(out) >= cap:
                return out
    return out


# --------------------------------------------------------------------------
# Built-in micro-mutations: a self-contained backup single-edit mutator so
# the search does not depend on repairlib's generic search being usable.
# --------------------------------------------------------------------------

def _mk_cmp_rule(frm, to):
    def rule(node):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and type(node.ops[0]) is frm):
            return ast.Compare(left=copy.deepcopy(node.left), ops=[to()],
                               comparators=[copy.deepcopy(node.comparators[0])])
        return None
    return rule


_CMP_SWAPS = [(ast.Eq, ast.NotEq), (ast.NotEq, ast.Eq),
              (ast.Lt, ast.LtE), (ast.LtE, ast.Lt),
              (ast.Gt, ast.GtE), (ast.GtE, ast.Gt),
              (ast.Lt, ast.Gt), (ast.Gt, ast.Lt)]


def rule_true_to_false(node):
    if isinstance(node, ast.Constant) and node.value is True:
        return ast.Constant(False)
    return None


def rule_false_to_true(node):
    if isinstance(node, ast.Constant) and node.value is False:
        return ast.Constant(True)
    return None


def rule_drop_not(node):
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return copy.deepcopy(node.operand)
    return None


def rule_add_not_return(node):
    if (isinstance(node, ast.Return) and node.value is not None
            and not isinstance(node.value, ast.Constant)):
        return ast.Return(value=ast.UnaryOp(op=ast.Not(),
                                            operand=copy.deepcopy(node.value)))
    return None


def rule_and_to_or(node):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return ast.BoolOp(op=ast.Or(), values=copy.deepcopy(node.values))
    return None


def rule_or_to_and(node):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return ast.BoolOp(op=ast.And(), values=copy.deepcopy(node.values))
    return None


def rule_add_to_sub(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return ast.BinOp(left=copy.deepcopy(node.left), op=ast.Sub(),
                         right=copy.deepcopy(node.right))
    return None


def rule_sub_to_add(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
        return ast.BinOp(left=copy.deepcopy(node.left), op=ast.Add(),
                         right=copy.deepcopy(node.right))
    return None


def rule_aug_add_to_sub(node):
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
        return ast.AugAssign(target=copy.deepcopy(node.target), op=ast.Sub(),
                             value=copy.deepcopy(node.value))
    return None


def rule_aug_sub_to_add(node):
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Sub):
        return ast.AugAssign(target=copy.deepcopy(node.target), op=ast.Add(),
                             value=copy.deepcopy(node.value))
    return None


def _mk_int_rule(delta):
    def rule(node):
        if (isinstance(node, ast.Constant) and isinstance(node.value, int)
                and not isinstance(node.value, bool)
                and abs(node.value) <= 4):
            return ast.Constant(node.value + delta)
        return None
    return rule


def _micro_rules():
    rules = [_mk_cmp_rule(a, b) for a, b in _CMP_SWAPS]
    rules += [rule_true_to_false, rule_false_to_true, rule_drop_not,
              rule_add_not_return, rule_and_to_or, rule_or_to_and,
              rule_add_to_sub, rule_sub_to_add,
              rule_aug_add_to_sub, rule_aug_sub_to_add,
              _mk_int_rule(1), _mk_int_rule(-1)]
    return rules


def _micro_list(source, cap=200):
    out = []
    seen = {source}
    for rule in _micro_rules():
        try:
            cands = _apply_rule(source, rule)
        except Exception:
            continue
        for cand in cands:
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
            if len(out) >= cap:
                return out
    return out


# --------------------------------------------------------------------------
# Entry point: staged pipeline, each stage validated via first_passing.
# --------------------------------------------------------------------------

def repair(source):
    try:
        return _repair(source)
    except Exception:
        return None


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    if _parse(source) is None:
        return None  # syntax error: out of scope for these rewrites

    seen = set()

    def fresh(cands):
        out = []
        for c in cands:
            if isinstance(c, str) and c and c not in seen:
                seen.add(c)
                out.append(c)
        return out

    # Stage 0: the original source (validated like any other candidate).
    res = _validate(fresh([source]), source)
    if isinstance(res, str) and res:
        return res

    # Stage 1: problem-specific rewrites.
    spec = _specific_list(source)
    res = _validate(fresh(spec), source)
    if isinstance(res, str) and res:
        return res

    # Stage 2: repairlib's generic single-edit search.
    gen1 = _generic(source, 1, cap=500)
    res = _validate(fresh(gen1), source)
    if isinstance(res, str) and res:
        return res

    # Stage 3: built-in micro-mutations (backup single-edit mutator).
    micro = _micro_list(source)
    res = _validate(fresh(micro), source)
    if isinstance(res, str) and res:
        return res

    # Stage 4: specific fix composed with a second specific fix.
    combo = []
    for s1 in spec[:20]:
        combo.extend(_specific_list(s1, cap=8))
        if len(combo) >= 200:
            break
    res = _validate(fresh(combo), source)
    if isinstance(res, str) and res:
        return res

    # Stage 5: (specific or micro) fix composed with a micro-mutation.
    combo2 = []
    for s1 in itertools.chain(spec[:12], micro[:25]):
        combo2.extend(_micro_list(s1, cap=12))
        if len(combo2) >= 400:
            break
    res = _validate(fresh(combo2), source)
    if isinstance(res, str) and res:
        return res

    # Stage 6: specific fix composed with a generic single edit.
    combo3 = []
    for s1 in spec[:6]:
        combo3.extend(_generic(s1, 1, cap=60))
        if len(combo3) >= 300:
            break
    res = _validate(fresh(combo3), source)
    if isinstance(res, str) and res:
        return res

    # Stage 7: repairlib's generic two-edit search.
    gen2 = _generic(source, 2, cap=1500)
    res = _validate(fresh(gen2), source)
    if isinstance(res, str) and res:
        return res

    return None
