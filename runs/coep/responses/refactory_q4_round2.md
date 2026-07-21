```python
"""Local, LLM-free automatic repair system for the 'Sorting Tuples' assignment.

The target function is `sort_age(lst)`: sort people [gender, age] by age,
oldest first.  We combine problem-specific rewrite rules (targeting the
misconceptions seen in real submissions: missing/wrong returns, printing
instead of returning, ascending instead of descending order, min/max mixups,
tracking the age value instead of the person element, broken pop/insert
insertion sorts, `return lst.reverse()` returning None, sorted()/sort()
without key/reverse, single-pass "keep only new maxima" tuple accumulation
like real_344) with the generic mutation search from coep.repairlib.
Every returned candidate is validated by `first_passing`, which enforces the
full visible test suite and the 0.35 relative-patch-size cap.
"""

import ast
import copy
import itertools
import re

from coep.repairlib import candidates_generic, first_passing, failing_tests, chain
from coep.evaluate import rps  # noqa: F401

ENTRY = "sort_age"
MAX_RPS = 0.35

TESTS = [
    {"args": [[["F", 19]]], "expected": [["F", 19]]},
    {"args": [[["M", 35], ["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]],
     "expected": [["M", 35], ["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30], ["M", 17]]],
     "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18], ["M", 17]]},
    {"args": [[["F", 18], ["M", 23], ["F", 19], ["M", 30]]],
     "expected": [["M", 30], ["M", 23], ["F", 19], ["F", 18]]},
    {"args": [[["M", 23], ["F", 19], ["M", 30]]],
     "expected": [["M", 30], ["M", 23], ["F", 19]]},
    {"args": [[]], "expected": []},
]


def _tests():
    """Fresh deep copy of the test list (defensive against mutation)."""
    return copy.deepcopy(TESTS)


def _compiles(s):
    try:
        ast.parse(s)
        return True
    except Exception:
        return False


def _slice_const(sl):
    if isinstance(sl, ast.Constant):
        return sl.value
    if sl.__class__.__name__ == "Index":  # very old ASTs
        v = getattr(sl, "value", None)
        if isinstance(v, ast.Constant):
            return v.value
    return None


def _find_fn(tree, name=None):
    """First FunctionDef, preferring one called `name` (or ENTRY)."""
    want = name or ENTRY
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if fn is None:
                fn = node
            if node.name == want:
                return node
    return fn


# --------------------------------------------------------------------------
# Problem-specific rewrite rules.  Each takes a source string and returns a
# (possibly empty) list of candidate source strings.  They must never raise
# outward (callers wrap them anyway).
# --------------------------------------------------------------------------

def rule_print_to_return(src):
    """`print(x)` used instead of `return x` (very common here)."""
    outs = []
    pat = re.compile(r"^([ \t]+)print\s*\((.*)\)\s*(#.*)?$", re.M)
    if pat.search(src):
        outs.append(pat.sub(lambda m: m.group(1) + "return " + m.group(2), src))
    return outs


def rule_add_return(src):
    """Function never returns: append `return <accumulator>` / `return <param>`."""
    outs = []
    if re.search(r"^\s*return\b", src, re.M):
        return outs
    names = []
    m = re.search(r"def\s+sort_age\s*\(\s*([A-Za-z_]\w*)", src)
    param = m.group(1) if m else None
    for am in re.finditer(r"^[ \t]+([A-Za-z_]\w*)\s*=\s*\[\]\s*(#.*)?$", src, re.M):
        names.append(am.group(1))
    if param:
        names.append(param)
    im = re.search(r"^([ \t]+)\S", src, re.M)
    indent = im.group(1) if im else "    "
    body = src if src.endswith("\n") else src + "\n"
    for n in dict.fromkeys(names):
        outs.append(body + indent + "return " + n + "\n")
    return outs


def rule_fix_return_inplace(src):
    """`return lst.reverse()` / `return lst.sort(...)` returns None."""
    outs = []
    pat = re.compile(
        r"^([ \t]*)return\s+([A-Za-z_]\w*)\.(reverse|sort)\s*\(([^()\n]*)\)\s*(#.*)?$",
        re.M)
    m = pat.search(src)
    if not m:
        return outs

    def repl(mm):
        return "{0}{1}.{2}({3})\n{0}return {1}".format(
            mm.group(1), mm.group(2), mm.group(3), mm.group(4))

    outs.append(pat.sub(repl, src))
    if m.group(3) == "sort":
        def repl2(mm):
            a = mm.group(4).strip()
            a2 = (a + ", " if a else "") + "reverse=True"
            return "{0}{1}.sort({2})\n{0}return {1}".format(
                mm.group(1), mm.group(2), a2)
        outs.append(pat.sub(repl2, src))
    return outs


def rule_minmax(src):
    """min/max confusion (selection by min gives ascending order)."""
    outs = []
    has_min = re.search(r"\bmin\b", src)
    has_max = re.search(r"\bmax\b", src)
    if has_min:
        outs.append(re.sub(r"\bmin\b", "max", src))
        for mm in re.finditer(r"\bmin\b", src):
            outs.append(src[:mm.start()] + "max" + src[mm.end():])
    if has_max:
        outs.append(re.sub(r"\bmax\b", "min", src))
        for mm in re.finditer(r"\bmax\b", src):
            outs.append(src[:mm.start()] + "min" + src[mm.end():])
    if has_min and has_max:
        tmp = re.sub(r"\bmin\b", "\x00", src)
        tmp = re.sub(r"\bmax\b", "min", tmp)
        outs.append(tmp.replace("\x00", "max"))
    return outs


def rule_flip_comparisons(src):
    """Flip every < / > (and <= / >=): wrong sort direction."""
    try:
        tree = ast.parse(src)
    except Exception:
        return []
    mapping = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
    hit = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            new_ops = []
            for op in n.ops:
                t = type(op)
                if t in mapping:
                    new_ops.append(mapping[t]())
                    hit = True
                else:
                    new_ops.append(op)
            n.ops = new_ops
    if not hit:
        return []
    try:
        ast.fix_missing_locations(tree)
        return [ast.unparse(tree)]
    except Exception:
        return []


def rule_return_reversed(src):
    """Result built ascending: reverse it on return (or drop a bogus reversal)."""
    outs = []
    pat = re.compile(r"^([ \t]+)return\s+([A-Za-z_]\w*)\s*(#.*)?$", re.M)
    if pat.search(src):
        outs.append(pat.sub(
            lambda m: m.group(1) + "return " + m.group(2) + "[::-1]", src))
    if "[::-1]" in src:
        outs.append(src.replace("[::-1]", ""))
    return outs


def rule_return_other_name(src):
    """`return lst` where the sorted result lives in another accumulator."""
    outs = []
    accs = re.findall(r"^[ \t]+([A-Za-z_]\w*)\s*=\s*\[\]\s*(?:#.*)?$", src, re.M)
    pat = re.compile(r"^([ \t]+)return\s+([A-Za-z_]\w*)\s*(#.*)?$", re.M)
    m = pat.search(src)
    if not m:
        return outs
    for a in dict.fromkeys(accs):
        if a != m.group(2):
            outs.append(src[:m.start()] + m.group(1) + "return " + a
                        + src[m.end():])
    return outs


def rule_append_insert0(src):
    """Accumulating ascending via append: build descending with insert(0, .)."""
    if ".append(" in src:
        return [src.replace(".append(", ".insert(0, ")]
    return []


def rule_sort_reverse(src):
    """sorted()/.sort() without reverse=True, wrong reverse flag, or no key."""
    outs = []
    try:
        ast.parse(src)
    except Exception:
        return outs

    def target_calls(tree):
        res = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                if (isinstance(f, ast.Name) and f.id == "sorted") or \
                   (isinstance(f, ast.Attribute) and f.attr == "sort"):
                    res.append(n)
        return res

    # Variant 1: add reverse=True (or toggle an existing constant flag).
    try:
        t = ast.parse(src)
        calls = target_calls(t)
        if calls:
            for c in calls:
                kw = None
                for k in c.keywords:
                    if k.arg == "reverse":
                        kw = k
                        break
                if kw is None:
                    c.keywords.append(
                        ast.keyword(arg="reverse", value=ast.Constant(value=True)))
                elif isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
                    kw.value = ast.Constant(value=not kw.value.value)
            ast.fix_missing_locations(t)
            outs.append(ast.unparse(t))
    except Exception:
        pass

    # Variant 2: negate the key lambda (key=lambda x: x[1] -> -x[1]).
    try:
        t = ast.parse(src)
        hit = False
        for c in target_calls(t):
            for k in c.keywords:
                if k.arg == "key" and isinstance(k.value, ast.Lambda):
                    k.value.body = ast.UnaryOp(op=ast.USub(), operand=k.value.body)
                    hit = True
        if hit:
            ast.fix_missing_locations(t)
            outs.append(ast.unparse(t))
    except Exception:
        pass

    # Variant 3: bare sorted(lst)/lst.sort(): add key=lambda x: x[1], reverse=True.
    try:
        t = ast.parse(src)
        hit = False
        for c in target_calls(t):
            if not c.keywords:
                lam = ast.Lambda(
                    args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="x")],
                                       vararg=None, kwonlyargs=[], kw_defaults=[],
                                       kwarg=None, defaults=[]),
                    body=ast.Subscript(value=ast.Name(id="x", ctx=ast.Load()),
                                       slice=ast.Constant(value=1),
                                       ctx=ast.Load()))
                c.keywords.append(ast.keyword(arg="key", value=lam))
                c.keywords.append(
                    ast.keyword(arg="reverse", value=ast.Constant(value=True)))
                hit = True
        if hit:
            ast.fix_missing_locations(t)
            outs.append(ast.unparse(t))
    except Exception:
        pass
    return outs


def rule_track_element(src):
    """Selection sort tracking the age *value* instead of the person *element*
    (`v = lst[0][1]` ... `v = elem[1]` ... `lst.remove(v)`), and/or the tracker
    initialized once before the `while` instead of once per pass.  Rewrites to
    element tracking and moves the initializer inside the while loop."""
    outs = []
    try:
        tree = ast.parse(src)
    except Exception:
        return outs
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            fn = node
            if node.name == ENTRY:
                break
    if fn is None:
        return outs
    for idx, st in enumerate(list(fn.body)):
        if not (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, ast.Subscript)):
            continue
        v = st.targets[0].id
        val = st.value
        double = (isinstance(val.value, ast.Subscript)
                  and isinstance(val.value.value, ast.Name)
                  and _slice_const(val.slice) == 1
                  and _slice_const(val.value.slice) == 0)
        single = (isinstance(val.value, ast.Name)
                  and _slice_const(val.slice) == 0)
        if not (double or single):
            continue
        wpos = None
        for j in range(idx + 1, len(fn.body)):
            if isinstance(fn.body[j], ast.While):
                wpos = j
                break
        if single and wpos is None:
            continue
        try:
            t2 = ast.parse(src)
        except Exception:
            continue
        fn2 = None
        for node in ast.walk(t2):
            if isinstance(node, ast.FunctionDef) and node.name == fn.name:
                fn2 = node
                break
        if fn2 is None or idx >= len(fn2.body):
            continue
        st2 = fn2.body[idx]
        if double:
            st2.value = st2.value.value  # v = L[0][1]  ->  v = L[0]

            class _Fix(ast.NodeTransformer):
                def visit_Compare(self, node):
                    self.generic_visit(node)

                    def wrap(x):
                        if isinstance(x, ast.Name) and x.id == v:
                            return ast.Subscript(
                                value=ast.Name(id=v, ctx=ast.Load()),
                                slice=ast.Constant(value=1), ctx=ast.Load())
                        return x

                    node.left = wrap(node.left)
                    node.comparators = [wrap(c) for c in node.comparators]
                    return node

                def visit_Assign(self, node):
                    self.generic_visit(node)
                    if (len(node.targets) == 1
                            and isinstance(node.targets[0], ast.Name)
                            and node.targets[0].id == v
                            and isinstance(node.value, ast.Subscript)
                            and isinstance(node.value.value, ast.Name)
                            and _slice_const(node.value.slice) == 1):
                        node.value = node.value.value  # v = e[1] -> v = e
                    return node

            fn2.body = [_Fix().visit(s) for s in fn2.body]
        if wpos is not None:
            init = fn2.body.pop(idx)
            tw = fn2.body[wpos - 1]
            if isinstance(tw, ast.While):
                tw.body.insert(0, init)
            else:
                fn2.body.insert(idx, init)
        try:
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
        except Exception:
            pass
        if len(outs) >= 3:
            break
    return outs


def _find_pop_insert(tree, while_only):
    for node in ast.walk(tree):
        if while_only and not isinstance(node, ast.While):
            continue
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for k in range(len(body) - 1):
            a, b = body[k], body[k + 1]
            if (isinstance(a, ast.Expr) and isinstance(a.value, ast.Call)
                    and isinstance(a.value.func, ast.Attribute)
                    and a.value.func.attr == "pop"
                    and isinstance(b, ast.Expr) and isinstance(b.value, ast.Call)
                    and isinstance(b.value.func, ast.Attribute)
                    and b.value.func.attr == "insert"
                    and len(b.value.args) == 2):
                return node, k
    return None, None


def rule_pop_insert(src):
    """Broken insertion sort: `x.pop(i)` then `x.insert(i-1, x[i])` loses the
    element.  Fuse into `x.insert(i-1, x.pop(i))`; guarded variant also adds
    `i -= 1` and an `i > 0` bound so the element bubbles all the way left."""
    outs = []
    for guarded in (False, True):
        try:
            tree = ast.parse(src)
        except Exception:
            return outs
        node, k = _find_pop_insert(tree, while_only=guarded)
        if node is None:
            continue
        body = node.body
        a, b = body[k], body[k + 1]
        b.value.args[1] = a.value  # insert(j, <pop call>)
        if guarded:
            ivar = None
            if len(a.value.args) == 1 and isinstance(a.value.args[0], ast.Name):
                ivar = a.value.args[0].id
            if ivar is None:
                node.body = body[:k] + body[k + 1:]
            else:
                aug = ast.AugAssign(target=ast.Name(id=ivar, ctx=ast.Store()),
                                    op=ast.Sub(), value=ast.Constant(value=1))
                node.body = body[:k] + [b, aug] + body[k + 2:]
                node.test = ast.BoolOp(op=ast.And(), values=[
                    ast.Compare(left=ast.Name(id=ivar, ctx=ast.Load()),
                                ops=[ast.Gt()],
                                comparators=[ast.Constant(value=0)]),
                    node.test])
        else:
            node.body = body[:k] + body[k + 1:]
        try:
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
        except Exception:
            pass
    return outs


def rule_balance_compare(src):
    """Comparisons mixing an age subscript with a bare element/tracker name
    (`elem[1] > largest` or `element > largest`): add the missing `[1]`."""
    outs = []

    def wrapped(name):
        return ast.Subscript(value=ast.Name(id=name, ctx=ast.Load()),
                             slice=ast.Constant(value=1), ctx=ast.Load())

    # Variant A: one side already has [1], the other is a bare name.
    try:
        tree = ast.parse(src)
        hit = False
        for n in ast.walk(tree):
            if isinstance(n, ast.Compare) and len(n.comparators) == 1:
                left, right = n.left, n.comparators[0]
                left_sub = isinstance(left, ast.Subscript) and _slice_const(left.slice) == 1
                right_sub = isinstance(right, ast.Subscript) and _slice_const(right.slice) == 1
                if left_sub and isinstance(right, ast.Name):
                    n.comparators[0] = wrapped(right.id)
                    hit = True
                elif right_sub and isinstance(left, ast.Name):
                    n.left = wrapped(left.id)
                    hit = True
        if hit:
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
    except Exception:
        pass

    # Variant B: both sides bare names (whole-element comparison).
    try:
        tree = ast.parse(src)
        hit = False
        for n in ast.walk(tree):
            if isinstance(n, ast.Compare) and len(n.comparators) == 1:
                left, right = n.left, n.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Name):
                    n.left = wrapped(left.id)
                    n.comparators[0] = wrapped(right.id)
                    hit = True
        if hit:
            ast.fix_missing_locations(tree)
            outs.append(ast.unparse(tree))
    except Exception:
        pass
    return outs


def rule_tuple_accumulate(src):
    """Single-pass accumulation that only keeps new maxima (real_344 shape):

        tup = ()
        for i in lst:
            if i[1] > current:
                tup += tuple(i)      # flattens, and only on new maxima
                current = i[1]
            else:
                tuple(i) + tup       # dead expression, element dropped

    Rewrite to a list accumulator with positional insertion, keeping the
    student's loop (and, in the surgical variants, the max-tracking `if`):
    new maxima are prepended, everything else is inserted at its sorted
    position.  Three variants of increasing patch size are produced:
    A) pure text surgery preserving the original formatting,
    B) the same surgery done on the AST, and
    C) replacing the whole loop body with a canonical insertion."""
    outs = []
    try:
        tree = ast.parse(src)
    except Exception:
        return outs
    fn = _find_fn(tree)
    if fn is None or not getattr(fn.args, "args", None):
        return outs

    acc = None
    for st in fn.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, (ast.Tuple, ast.List))
                and not st.value.elts):
            acc = st.targets[0].id
    loop = None
    for node in ast.walk(fn):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loop = node
            break
    if acc is None or loop is None:
        return outs
    it = loop.target.id
    if acc == it:
        return outs

    jn = "j"
    while re.search(r"\b" + jn + r"\b", src):
        jn += "j"

    ins_src = ("{j} = 0\n"
               "while {j} < len({a}) and {a}[{j}][1] >= {i}[1]:\n"
               "    {j} += 1\n"
               "{a}.insert({j}, {i})\n").format(j=jn, a=acc, i=it)

    # Variant A: regex surgery, preserves the student's formatting exactly.
    try:
        ea, ei = re.escape(acc), re.escape(it)
        elem = r"(?:tuple\(\s*" + ei + r"\s*\)|\(\s*" + ei + r"\s*,?\s*\)|" + ei + r")"
        s1 = re.sub(r"^([ \t]*)(" + ea + r")\s*=\s*\(\s*\)[ \t]*$",
                    lambda m: m.group(1) + m.group(2) + "=[]", src, flags=re.M)
        s2 = re.sub(r"^([ \t]*)" + ea + r"\s*\+=\s*" + elem + r"[ \t]*$",
                    lambda m: m.group(1) + acc + ".insert(0, " + it + ")",
                    s1, flags=re.M)
        s2 = re.sub(r"^([ \t]*)" + ea + r"\s*=\s*(?:" + ea + r"\s*\+\s*" + elem
                    + r"|" + elem + r"\s*\+\s*" + ea + r")[ \t]*$",
                    lambda m: m.group(1) + acc + ".insert(0, " + it + ")",
                    s2, flags=re.M)
        dead = re.compile(r"^([ \t]*)(?:" + elem + r"\s*\+\s*" + ea
                          + r"|" + ea + r"\s*\+\s*" + elem + r")[ \t]*$", re.M)
        m = dead.search(s2)
        if m is not None:
            ind = m.group(1)
            block = (ind + jn + "=0\n"
                     + ind + "while " + jn + "<len(" + acc + ") and "
                     + acc + "[" + jn + "][1]>=" + it + "[1]:\n"
                     + ind + "    " + jn + "+=1\n"
                     + ind + acc + ".insert(" + jn + "," + it + ")")
            s3 = s2[:m.start()] + block + s2[m.end():]
            if s3 != src:
                outs.append(s3)
    except Exception:
        pass

    # Variant B: same surgery on the AST (robust to formatting differences).
    try:
        t2 = ast.parse(src)
        changed = {"add": False, "dead": False}
        prepend_call = "{a}.insert(0, {i})".format(a=acc, i=it)

        class _T(ast.NodeTransformer):
            def visit_Assign(self, node):
                self.generic_visit(node)
                if (len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == acc):
                    v = node.value
                    if isinstance(v, (ast.Tuple, ast.List)) and not v.elts:
                        node.value = ast.List(elts=[], ctx=ast.Load())
                    elif isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add):
                        changed["add"] = True
                        return ast.parse(prepend_call).body[0]
                return node

            def visit_AugAssign(self, node):
                if (isinstance(node.target, ast.Name)
                        and node.target.id == acc
                        and isinstance(node.op, ast.Add)):
                    changed["add"] = True
                    return ast.parse(prepend_call).body[0]
                return node

            def visit_Expr(self, node):
                v = node.value
                if isinstance(v, ast.BinOp) and any(
                        isinstance(x, ast.Name) and x.id == acc
                        for x in ast.walk(v)):
                    changed["dead"] = True
                    return ast.parse(ins_src).body
                return node

        t2 = _T().visit(t2)
        if changed["add"] or changed["dead"]:
            ast.fix_missing_locations(t2)
            outs.append(ast.unparse(t2))
    except Exception:
        pass

    # Variant C: replace the whole loop body with a canonical insertion.
    try:
        t3 = ast.parse(src)
        f3 = _find_fn(t3, fn.name)
        if f3 is not None:
            for st in f3.body:
                if (isinstance(st, ast.Assign) and len(st.targets) == 1
                        and isinstance(st.targets[0], ast.Name)
                        and st.targets[0].id == acc
                        and isinstance(st.value, (ast.Tuple, ast.List))
                        and not st.value.elts):
                    st.value = ast.List(elts=[], ctx=ast.Load())
            l3 = None
            for node in ast.walk(f3):
                if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    l3 = node
                    break
            if l3 is not None:
                l3.body = ast.parse(ins_src).body
                if not any(isinstance(n, ast.Return) for n in ast.walk(f3)):
                    f3.body.append(ast.parse("return " + acc).body[0])
                ast.fix_missing_locations(t3)
                outs.append(ast.unparse(t3))
    except Exception:
        pass
    return outs


def rule_return_sorted(src):
    """Last resort when the accumulation logic is unfixably lossy: keep the
    student's code in place but return the correctly ordered result, e.g.
    `return sorted(lst, key=lambda x: x[1], reverse=True)`.  Small patch,
    validated (like everything) against the tests and the size cap."""
    outs = []
    m = re.search(r"def\s+" + re.escape(ENTRY) + r"\s*\(\s*([A-Za-z_]\w*)", src)
    if m is None:
        m = re.search(r"def\s+[A-Za-z_]\w*\s*\(\s*([A-Za-z_]\w*)", src)
    param = m.group(1) if m else None
    call = "sorted({0}, key=lambda x: x[1], reverse=True)"

    pat = re.compile(r"^([ \t]+)return\s+(.+?)[ \t]*(#.*)?$", re.M)
    ms = list(pat.finditer(src))
    if ms:
        last = ms[-1]

        def sub_last(expr):
            return (src[:last.start()] + last.group(1) + "return "
                    + call.format(expr) + src[last.end():])

        if param:
            outs.append(sub_last(param))
        expr = (last.group(2) or "").strip()
        if expr and expr != param:
            outs.append(sub_last(expr))
            outs.append(sub_last("list(" + expr + ")"))
    elif param:
        im = re.search(r"^([ \t]+)\S", src, re.M)
        indent = im.group(1) if im else "    "
        body = src if src.endswith("\n") else src + "\n"
        outs.append(body + indent + "return " + call.format(param) + "\n")

    # If there are several simple `return name` statements, fix them all.
    pat2 = re.compile(r"^([ \t]+)return\s+([A-Za-z_]\w*)[ \t]*(#.*)?$", re.M)
    if param and len(pat2.findall(src)) > 1:
        outs.append(pat2.sub(
            lambda mm: mm.group(1) + "return " + call.format(param), src))
    return outs


ALL_RULES = [
    rule_print_to_return,
    rule_add_return,
    rule_fix_return_inplace,
    rule_minmax,
    rule_track_element,
    rule_pop_insert,
    rule_flip_comparisons,
    rule_return_reversed,
    rule_return_other_name,
    rule_sort_reverse,
    rule_balance_compare,
    rule_append_insert0,
    rule_tuple_accumulate,
    rule_return_sorted,
]


def _ordered_rules(fr):
    """Reorder rules according to the observed failing-test pattern."""
    rules = list(ALL_RULES)
    try:
        if fr is None or not getattr(fr, "compiled", False):
            return rules
        failures = list(getattr(fr, "failures", []) or [])
        if not failures:
            return rules
        gots_none = all((f.get("got") is None and not f.get("error"))
                        for f in failures)
        reversed_out = True
        for f in failures:
            exp = f.get("expected")
            got = f.get("got")
            if not isinstance(got, (list, tuple)) or exp is None or \
                    list(got) != list(reversed(exp)):
                reversed_out = False
                break
        if reversed_out:
            pri = [rule_flip_comparisons, rule_return_reversed,
                   rule_sort_reverse, rule_minmax, rule_append_insert0]
            rules = pri + [r for r in rules if r not in pri]
        elif gots_none:
            pri = [rule_print_to_return, rule_add_return,
                   rule_fix_return_inplace]
            rules = pri + [r for r in rules if r not in pri]
    except Exception:
        return list(ALL_RULES)
    return rules


def _apply(rule, src):
    try:
        res = rule(src)
        return [r for r in res if isinstance(r, str) and r][:10]
    except Exception:
        return []


def _repair(source):
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        ast.parse(source)
    except Exception:
        return None

    try:
        fr = failing_tests(source, ENTRY, _tests())
    except Exception:
        fr = None

    # Already correct?  (Still validated through first_passing.)
    if fr is not None and getattr(fr, "compiled", False) and \
            getattr(fr, "passed", -1) == getattr(fr, "total", -2):
        try:
            ok = first_passing(iter([source]), ENTRY, _tests(), source,
                               max_rps=MAX_RPS, max_checks=4)
            if ok is not None:
                return ok
        except Exception:
            pass

    rules = _ordered_rules(fr)

    # Level 1: single problem-specific rewrites.
    seen = {source}
    lvl1 = []
    for r in rules:
        for v in _apply(r, source):
            if v not in seen and _compiles(v):
                seen.add(v)
                lvl1.append(v)
        if len(lvl1) >= 48:
            break

    # Level 2: pairs of rewrites (e.g. element-tracking fix + comparison flip,
    # pop/insert fusion + return fix).
    lvl2 = []
    for v in lvl1:
        if len(lvl2) >= 240:
            break
        for r in rules:
            for w in _apply(r, v):
                if w not in seen and _compiles(w):
                    seen.add(w)
                    lvl2.append(w)
            if len(lvl2) >= 240:
                break

    specific = lvl1 + lvl2

    # Stage 1: specific rewrites.
    if specific:
        try:
            res = first_passing(iter(specific), ENTRY, _tests(), source,
                                max_rps=MAX_RPS, max_checks=len(specific) + 1)
            if res is not None:
                return res
        except Exception:
            pass

    # Stage 2: generic single-edit search on the original.
    try:
        res = first_passing(candidates_generic(source, max_edits=1), ENTRY,
                            _tests(), source, max_rps=MAX_RPS, max_checks=400)
        if res is not None:
            return res
    except Exception:
        pass

    # Stage 3: generic single edits stacked on top of the best rewrites.
    stack = specific[:8]
    if stack:
        try:
            gens = []
            for v in stack:
                try:
                    gens.append(itertools.islice(
                        candidates_generic(v, max_edits=1), 80))
                except Exception:
                    pass
            if gens:
                res = first_passing(chain(*gens), ENTRY, _tests(), source,
                                    max_rps=MAX_RPS, max_checks=400)
                if res is not None:
                    return res
        except Exception:
            pass

    # Stage 4: generic double-edit search (budgeted).
    try:
        res = first_passing(candidates_generic(source, max_edits=2, budget=1500),
                            ENTRY, _tests(), source, max_rps=MAX_RPS,
                            max_checks=450)
        if res is not None:
            return res
    except Exception:
        pass

    return None


def repair(source):
    """Repair a buggy `sort_age` submission; return fixed source or None."""
    try:
        return _repair(source)
    except Exception:
        return None
```
