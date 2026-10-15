"""
Repair module for the "cAPS lOCK" assignment.

The misconceptions observed in buggy submissions cluster around a handful of
structural patterns:

  * using a case-conversion call (`.upper()`/`.lower()`) directly as a boolean
    test instead of the matching predicate (`.isupper()`/`.islower()`),
  * forgetting the call parentheses on a predicate (`x.isupper` instead of
    `x.isupper()`),
  * typo'd non-existent methods `.uppercase()` / `.lowercase()`,
  * using `.capitalize()` / `.title()` (or a hand rolled
    `w[0].upper()+w[1:].lower()` formula) where `.swapcase()` is required,
  * a caps-lock condition that forgets the `len(word) == 1` edge case,
  * a caps-lock condition that is tested "backwards" (checking for the
    already-normal shape instead of the shape that needs fixing) with the
    branches left in the original order,
  * applying the swap-case transform totally unconditionally (no guard at
    all), and
  * building a guarded `answer`/result variable inside an `if` but forgetting
    the `else` branch that preserves the original word.

Each rule below targets exactly one of these shapes with a small, local
source-text splice.
"""

import ast

from src.core.repair import Rule


# --------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------

def _span(source, node):
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    s = starts[node.lineno - 1] + node.col_offset
    e = starts[node.end_lineno - 1] + node.end_col_offset
    return s, e


def _splice(source, node, new_text):
    s, e = _span(source, node)
    return source[:s] + new_text + source[e:]


def _add_parents(tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent
    return tree


def _contains_input_call(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input":
            return True
    return False


def _is_main_guard(test):
    return (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
            and test.left.id == "__name__" and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__")


def _get_working_body(tree):
    body = tree.body
    if (len(body) == 1 and isinstance(body[0], ast.If)
            and _is_main_guard(body[0].test) and not body[0].orelse):
        return body[0].body
    return body


def _unwrap_index(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


# --------------------------------------------------------------------------
# Rule: case-method call used directly as a boolean test
# --------------------------------------------------------------------------

def _truthy_call_to_is(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _add_parents(tree)
    targets = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("upper", "lower") and not node.args and not node.keywords):
            continue
        parent = getattr(node, "parent", None)
        is_bool_ctx = False
        if isinstance(parent, ast.If) and parent.test is node:
            is_bool_ctx = True
        elif isinstance(parent, ast.BoolOp) and node in parent.values:
            is_bool_ctx = True
        elif isinstance(parent, ast.IfExp) and parent.test is node:
            is_bool_ctx = True
        elif isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Not) and parent.operand is node:
            is_bool_ctx = True
        if is_bool_ctx:
            targets.append(node)
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_src = source
    for node in targets:
        s, e = _span(source, node)
        text = new_src[s:e]
        if text.endswith(".upper()"):
            new_text = text[: -len(".upper()")] + ".isupper()"
        elif text.endswith(".lower()"):
            new_text = text[: -len(".lower()")] + ".islower()"
        else:
            continue
        new_src = new_src[:s] + new_text + new_src[e:]
    if new_src == source:
        return []
    return [new_src]


# --------------------------------------------------------------------------
# Rule: bare predicate attribute used without being called
# --------------------------------------------------------------------------

_BOOL_METHODS = ("isupper", "islower", "isalpha", "isdigit", "isalnum", "istitle")


def _bare_attr_add_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    called_ids = {id(c.func) for c in ast.walk(tree) if isinstance(c, ast.Call)}
    targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr in _BOOL_METHODS
                and id(node) not in called_ids):
            targets.append(node)
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_src = source
    for node in targets:
        s, e = _span(source, node)
        new_src = new_src[:s] + new_src[s:e] + "()" + new_src[e:]
    return [new_src]


# --------------------------------------------------------------------------
# Rule: typo'd .uppercase()/.lowercase() methods
# --------------------------------------------------------------------------

def _typo_uppercase_lowercase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("uppercase", "lowercase")):
            targets.append(node.func)
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_src = source
    for node in targets:
        s, e = _span(source, node)
        text = new_src[s:e]
        if text.endswith("uppercase"):
            new_text = text[: -len("uppercase")] + "upper"
        else:
            new_text = text[: -len("lowercase")] + "lower"
        new_src = new_src[:s] + new_text + new_src[e:]
    return [new_src]


# --------------------------------------------------------------------------
# Rule: .capitalize()/.title() used where .swapcase() is required
# --------------------------------------------------------------------------

def _capitalize_title_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("capitalize", "title")
                and not node.args and not node.keywords):
            targets.append(node.func)
    if not targets:
        return []
    targets.sort(key=lambda n: _span(source, n)[0], reverse=True)
    new_src = source
    for node in targets:
        s, e = _span(source, node)
        text = new_src[s:e]
        if "." not in text:
            continue
        prefix, _, _ = text.rpartition(".")
        new_src = new_src[:s] + prefix + ".swapcase" + new_src[e:]
    if new_src == source:
        return []
    return [new_src]


# --------------------------------------------------------------------------
# Rule: hand-rolled w[0].upper()+w[1:].lower() formula -> w.swapcase()
# --------------------------------------------------------------------------

def _manual_formula_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    targets = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            continue
        left, right = node.left, node.right
        if not (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                and left.func.attr == "upper" and not left.args):
            continue
        if not (isinstance(right, ast.Call) and isinstance(right.func, ast.Attribute)
                and right.func.attr == "lower" and not right.args):
            continue
        lval, rval = left.func.value, right.func.value
        if not (isinstance(lval, ast.Subscript) and isinstance(rval, ast.Subscript)):
            continue
        if not (isinstance(lval.value, ast.Name) and isinstance(rval.value, ast.Name)):
            continue
        if lval.value.id != rval.value.id:
            continue
        lsl = _unwrap_index(lval.slice)
        rsl = _unwrap_index(rval.slice)
        if not (isinstance(lsl, ast.Constant) and lsl.value == 0):
            continue
        if not (isinstance(rsl, ast.Slice) and rsl.upper is None
                and isinstance(rsl.lower, ast.Constant) and rsl.lower.value == 1):
            continue
        targets.append((node, lval.value.id))
    if not targets:
        return []
    targets.sort(key=lambda t: _span(source, t[0])[0], reverse=True)
    new_src = source
    for node, var in targets:
        s, e = _span(source, node)
        new_src = new_src[:s] + f"{var}.swapcase()" + new_src[e:]
    return [new_src]


# --------------------------------------------------------------------------
# Rule: caps-lock condition missing the len(word) == 1 edge case
# --------------------------------------------------------------------------

def _add_len_one_clause(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        has_isupper = False
        has_len = False
        var = None
        for n in ast.walk(test):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "len":
                has_len = True
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("isupper", "islower") and not n.args):
                has_isupper = True
                base = n.func.value
                while isinstance(base, ast.Subscript):
                    base = base.value
                if isinstance(base, ast.Name):
                    var = base.id
        if has_isupper and not has_len and var:
            ts, te = _span(source, test)
            new_test = "(" + source[ts:te] + f") or len({var}) == 1"
            out.append(source[:ts] + new_test + source[te:])
    return out


# --------------------------------------------------------------------------
# Rule: backward caps condition with branches left unswapped
#   if V.isupper() or (V[0].isupper() and V[1:].islower()):
#       print(V)
#   else:
#       print(<some wrong fix action>)
# --------------------------------------------------------------------------

def _fix_backward_caps_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or) and len(test.values) == 2):
            continue
        v0, v1 = test.values
        if not (isinstance(v0, ast.Call) and isinstance(v0.func, ast.Attribute)
                and v0.func.attr == "isupper" and not v0.args
                and isinstance(v0.func.value, ast.Name)):
            continue
        var = v0.func.value.id
        if not (isinstance(v1, ast.BoolOp) and isinstance(v1.op, ast.And) and len(v1.values) == 2):
            continue
        a, b = v1.values

        def _match(n, idx0):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("isupper", "islower") and not n.args):
                return None
            val = n.func.value
            if not (isinstance(val, ast.Subscript) and isinstance(val.value, ast.Name)
                    and val.value.id == var):
                return None
            sl = _unwrap_index(val.slice)
            if idx0:
                if isinstance(sl, ast.Constant) and sl.value == 0:
                    return n.func.attr
                return None
            if isinstance(sl, ast.Slice) and sl.upper is None and sl.lower is not None \
                    and isinstance(sl.lower, ast.Constant) and sl.lower.value == 1:
                return n.func.attr
            return None

        attr_a = _match(a, True)
        attr_b = _match(b, False)
        if attr_a != "isupper" or attr_b != "islower":
            continue
        if len(node.body) != 1 or len(node.orelse) != 1:
            continue

        def _is_print_expr(s):
            return (isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
                    and isinstance(s.value.func, ast.Name) and s.value.func.id == "print")

        if not (_is_print_expr(node.body[0]) and _is_print_expr(node.orelse[0])):
            continue

        indent = " " * node.col_offset
        new_if = (f"{indent}if len({var}) == 1 or {var}.isupper() or "
                  f"({var}[0].islower() and {var}[1:].isupper()):\n"
                  f"{indent}    print({var}.swapcase())\n"
                  f"{indent}else:\n"
                  f"{indent}    print({var})")
        s_, e_ = _span(source, node)
        out.append(source[:s_] + new_if + source[e_:])
    return out


# --------------------------------------------------------------------------
# Rule: unconditional transform with no guard at all
# --------------------------------------------------------------------------

def _unconditional_transform_guard(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    body = _get_working_body(tree)
    if not body:
        return []
    if any(isinstance(n, (ast.If, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
           for n in body):
        return []

    var = None
    assign_idx = None
    for i, n in enumerate(body):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and _contains_input_call(n.value)):
            var = n.targets[0].id
            assign_idx = i
            break
    if var is None:
        return []

    rest = body[assign_idx + 1:]
    if not rest:
        return []

    last = rest[-1]
    if not (isinstance(last, ast.Expr) and isinstance(last.value, ast.Call)
            and isinstance(last.value.func, ast.Name) and last.value.func.id == "print"):
        return []

    assign_node = body[assign_idx]
    indent = " " * assign_node.col_offset
    new_tail = (f"{indent}if {var}[1:] == {var}[1:].upper():\n"
                f"{indent}    {var} = {var}.swapcase()\n"
                f"{indent}print({var})")

    start, _ = _span(source, rest[0])
    _, end = _span(source, rest[-1])
    new_src = source[:start] + new_tail + source[end:]
    if new_src == source:
        return []
    return [new_src]


# --------------------------------------------------------------------------
# Rule: if-body builds a result variable but forgets the else that keeps
# the original word unchanged.
# --------------------------------------------------------------------------

def _add_missing_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    src_var = None
    for n in tree.body:
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name) and _contains_input_call(n.value)):
            src_var = n.targets[0].id
            break
    if src_var is None:
        return []

    body = tree.body
    for i, node in enumerate(body):
        if not (isinstance(node, ast.If) and not node.orelse):
            continue
        target_names = set()
        for n in ast.walk(node):
            if isinstance(n, (ast.Assign, ast.AugAssign)):
                tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in tgts:
                    if isinstance(t, ast.Name):
                        target_names.add(t.id)
        if not target_names:
            continue
        for later in body[i + 1:]:
            if (isinstance(later, ast.Expr) and isinstance(later.value, ast.Call)
                    and isinstance(later.value.func, ast.Name) and later.value.func.id == "print"
                    and len(later.value.args) == 1 and isinstance(later.value.args[0], ast.Name)
                    and later.value.args[0].id in target_names):
                pname = later.value.args[0].id
                indent = " " * node.col_offset
                insertion = f"\n{indent}else:\n{indent}    {pname} = {src_var}"
                _, e_ = _span(source, node)
                out.append(source[:e_] + insertion + source[e_:])
    return out


# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="truthy_case_call_to_is_predicate",
                apply=_truthy_call_to_is,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_predicate_attr_missing_call",
                apply=_bare_attr_add_call,
                symptoms=("wrong", "err:AttributeError", "err:TypeError"),
            ),
            Rule(
                name="typo_uppercase_lowercase_method",
                apply=_typo_uppercase_lowercase,
                symptoms=("err:AttributeError",),
            ),
            Rule(
                name="capitalize_title_should_be_swapcase",
                apply=_capitalize_title_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="manual_titlecase_formula_should_be_swapcase",
                apply=_manual_formula_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="caps_condition_missing_len_one_case",
                apply=_add_len_one_clause,
                symptoms=("wrong",),
            ),
            Rule(
                name="backward_caps_condition_unswapped_branches",
                apply=_fix_backward_caps_condition,
                symptoms=("wrong",),
            ),
            Rule(
                name="unconditional_transform_missing_guard",
                apply=_unconditional_transform_guard,
                symptoms=("wrong",),
            ),
            Rule(
                name="if_branch_missing_else_keep_original",
                apply=_add_missing_else,
                symptoms=("wrong",),
            ),
        ]