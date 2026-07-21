```python
"""Local, LLM-free automatic repair system for the `is_palindrome` assignment.

Strategy:
  1. Try the original source (it is validated like any other candidate).
  2. Apply problem-specific AST rewrite rules targeting the common
     misconceptions for this assignment (wrong filter predicate, missing
     case fold, half-split comparison, inverted result, bad two-pointer
     initialization, missing call parentheses, missing filtering step, ...),
     lightly dispatched on the observed failing-test pattern.
  3. Fall back to the generic single-edit search, then compositions
     (specific+specific, specific+generic, generic two-edit search).
All candidates are validated through `first_passing`, which enforces the
full visible test suite and the relative-patch-size cap (<= 0.35).
"""

import ast
import copy
import itertools

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain

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
    if not (isinstance(L, ast.Name) or isinstance(R, ast.Name)
            or isinstance(L, ast.Subscript) or isinstance(R, ast.Subscript)):
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


# --------------------------------------------------------------------------
# Candidate generation
# --------------------------------------------------------------------------

def _specific_list(source, prioritize_lower=False):
    rules_case = [rule_lower_elt, rule_lower_iter, rule_lower_cmp,
                  rule_call_elt]
    rules_filter = [rule_isalnum, rule_notspace, rule_call_attr] \
        + _mk_filter_rules(source)
    rules_struct = [rule_halfsplit, rule_whole_reverse, rule_reversed,
                    rule_init_fix]
    if prioritize_lower:
        ordered = rules_case + rules_filter + rules_struct
    else:
        ordered = rules_filter + rules_case + rules_struct
    out = []
    seen = {source}
    for rule in ordered:
        for cand in _apply_rule(source, rule):
            if cand not in seen:
                seen.add(cand)
                out.append(cand)
            if len(out) >= 80:
                return out
    return out


def _safe(gen):
    try:
        for c in gen:
            yield c
    except Exception:
        return


def _second_wave(spec, prioritize_lower):
    # Compositions of two specific fixes.
    n = 0
    for s1 in spec[:25]:
        try:
            more = _specific_list(s1, prioritize_lower)
        except Exception:
            continue
        for s2 in more[:10]:
            yield s2
            n += 1
            if n >= 120:
                return


def _spec_plus_generic(spec):
    # A specific fix plus one generic edit.
    for s1 in spec[:6]:
        try:
            gen = candidates_generic(s1, max_edits=1)
        except Exception:
            continue
        for s2 in _safe(itertools.islice(gen, 40)):
            yield s2


# --------------------------------------------------------------------------
# Entry point
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
        return None  # syntax error

    # Light dispatch on the observed failing-test pattern: if the pure
    # case-sensitivity probe "Aa" fails, the case fold is likely missing,
    # so try the lowercasing rules first.
    prioritize_lower = False
    try:
        res = failing_tests(source, ENTRY, TESTS)
        if getattr(res, "compiled", False):
            for f in getattr(res, "failures", []) or []:
                try:
                    if f["args"][0] == "Aa":
                        prioritize_lower = True
                        break
                except Exception:
                    pass
    except Exception:
        pass

    try:
        spec = _specific_list(source, prioritize_lower)
    except Exception:
        spec = []

    generators = [iter([source]), iter(spec)]
    try:
        generators.append(_safe(candidates_generic(source, max_edits=1)))
    except Exception:
        pass
    generators.append(_second_wave(spec, prioritize_lower))
    generators.append(_spec_plus_generic(spec))
    try:
        generators.append(_safe(candidates_generic(source, max_edits=2,
                                                   budget=2500)))
    except Exception:
        pass

    try:
        return first_passing(chain(*generators), ENTRY, TESTS, source,
                             max_rps=0.35, max_checks=800)
    except Exception:
        return None
```
