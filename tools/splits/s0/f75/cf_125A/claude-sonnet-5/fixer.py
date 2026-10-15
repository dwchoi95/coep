import ast
import re

from src.core.repair import Rule


def _span(source, node):
    """(start, end) char offsets of node in source."""
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


def _round_offset_fix(source):
    """(X + 2) // 3  ->  (X + 1) // 3

    Misconception: rounding cm-to-inch by always rounding up (ceil
    division) instead of rounding to the nearest inch.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv)
                and isinstance(node.right, ast.Constant) and node.right.value == 3
                and isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add)):
            add_node = node.left
            const_operand = None
            if isinstance(add_node.right, ast.Constant) and add_node.right.value == 2:
                const_operand = add_node.right
            elif isinstance(add_node.left, ast.Constant) and add_node.left.value == 2:
                const_operand = add_node.left
            if const_operand is not None:
                out.append(_splice(source, const_operand, "1"))
    return out


def _ceil_to_round_nearest(source):
    """math.ceil(X / 3)  ->  ((X + 1) // 3)

    Same misconception as above but expressed via math.ceil instead of
    an arithmetic offset.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_ceil = False
        if isinstance(node.func, ast.Attribute) and node.func.attr == "ceil":
            is_ceil = True
        elif isinstance(node.func, ast.Name) and node.func.id == "ceil":
            is_ceil = True
        if not is_ceil or len(node.args) != 1:
            continue
        arg = node.args[0]
        if (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div)
                and isinstance(arg.right, ast.Constant) and arg.right.value == 3):
            ns, ne = _span(source, arg.left)
            num_src = source[ns:ne]
            replacement = "((" + num_src + " + 1) // 3)"
            out.append(_splice(source, node, replacement))
    return out


def _int_cast_after_true_div(source):
    """Wrap `x // 12` / `x % 12` with int(...) when x came from true
    division (`/` or `/=`), fixing float leakage into printed output.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    div_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div) \
           and isinstance(node.target, ast.Name):
            div_names.add(node.target.id)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) \
           and isinstance(node.value.op, ast.Div):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    div_names.add(t.id)
    if not div_names:
        return []

    parent = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parent[c] = p

    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.FloorDiv, ast.Mod)):
            left = node.left
            if isinstance(left, ast.Name) and left.id in div_names:
                par = parent.get(node)
                if isinstance(par, ast.Call) and isinstance(par.func, ast.Name) \
                   and par.func.id == "int":
                    continue
                spans.append(_span(source, node))

    if not spans:
        return []

    new_source = source
    for s, e in sorted(spans, key=lambda x: -x[0]):
        new_source = new_source[:s] + "int(" + new_source[s:e] + ")" + new_source[e:]
    return [new_source]


def _self_name_compare_fix(source):
    """Inside a one-argument helper function, a comparison that checks
    the function's own name against a constant (instead of the
    parameter) is replaced with `param <= constant`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and len(node.args.args) == 1):
            continue
        fname = node.name
        param = node.args.args[0].arg
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Compare) and isinstance(inner.left, ast.Name)
                    and inner.left.id == fname and len(inner.ops) == 1
                    and isinstance(inner.ops[0], ast.Eq)
                    and len(inner.comparators) == 1
                    and isinstance(inner.comparators[0], ast.Constant)):
                const_val = inner.comparators[0].value
                replacement = f"{param} <= {const_val!r}"
                out.append(_splice(source, inner, replacement))
    return out


def _missing_carry_fix(source):
    """When feet/inches are computed on two independent tracks (not via
    //12 and %12 of a combined total), a rounded-up inch count can hit
    12 without carrying into feet. Insert the missing carry check right
    before the final print(feet, inches) call.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    if re.search(r'%\s*12\b', source):
        return []
    if re.search(r'(==|>=)\s*12\b', source):
        return []

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        if not (isinstance(call.func, ast.Name) and call.func.id == "print"):
            continue
        if len(call.args) < 2:
            continue
        a0, a1 = call.args[0], call.args[1]
        if not (isinstance(a0, ast.Name) and isinstance(a1, ast.Name)):
            continue

        s, e = _span(source, node)
        line_start = source.rfind("\n", 0, s) + 1
        indent = source[line_start:s]
        orig = source[s:e]
        insertion = (
            f"if {a1.id} == 12:\n"
            f"{indent}    {a0.id} += 1\n"
            f"{indent}    {a1.id} = 0\n"
            f"{indent}"
        )
        out.append(source[:s] + insertion + orig + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="ceil_offset_round_to_nearest",
                apply=_round_offset_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="math_ceil_round_to_nearest",
                apply=_ceil_to_round_nearest,
                symptoms=("wrong",),
            ),
            Rule(
                name="int_cast_after_true_division",
                apply=_int_cast_after_true_div,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="self_name_compare_to_param",
                apply=_self_name_compare_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_inch_to_foot_carry",
                apply=_missing_carry_fix,
                symptoms=("wrong",),
            ),
        ]