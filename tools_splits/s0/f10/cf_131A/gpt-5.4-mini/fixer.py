import ast
from src.core.repair import Rule


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


def _all_upper_or_first_lower(expr):
    return (
        f"({expr}.isupper() or ({expr}[0].islower() and {expr}[1:].isupper()))"
    )


def _rule_swapcase_on_capslock(source):
    """Replace common 'capitalize/lower' outputs with swapcase under the capslock rule."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # if X.isupper() ... -> if X.isupper() or X[1:].isupper(): ...
            test = node.test
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                continue
            if isinstance(test, ast.Attribute) and test.attr == "isupper":
                obj = test.value
                if isinstance(obj, ast.Subscript):
                    continue
                expr = source[_span(source, obj)[0]:_span(source, obj)[1]]
                new_test = _all_upper_or_first_lower(expr)
                out.append(_splice(source, test, new_test))
            elif isinstance(test, ast.Compare):
                continue
            # capitalize() / lower() / uppercase() inside branches
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in {"capitalize", "lower", "uppercase"}:
                obj = node.func.value
                if isinstance(obj, ast.Name):
                    expr = source[_span(source, obj)[0]:_span(source, obj)[1]]
                    if attr == "capitalize":
                        new_text = f"{expr}.swapcase()"
                    elif attr == "lower":
                        new_text = f"{expr}.swapcase()"
                    else:
                        new_text = f"{expr}.swapcase()"
                    out.append(_splice(source, node, new_text))
    return out


def _rule_fix_isupper_slice_tests(source):
    """Treat the caps-lock condition as a slice-based uppercase check."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            vals = node.values
            if len(vals) != 2:
                continue
            left, right = vals
            # pattern: x.isupper() or x[1:].isupper()
            def _is_isupper(call):
                return (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "isupper"
                )

            if _is_isupper(left) and _is_isupper(right):
                lv = left.func.value
                rv = right.func.value
                if isinstance(lv, ast.Name) and isinstance(rv, ast.Subscript):
                    expr = source[_span(source, lv)[0]:_span(source, lv)[1]]
                    new_text = f"{expr}[1:]=={expr}[1:].upper()"
                    out.append(_splice(source, node, new_text))
    return out


def _rule_wrong_capitalize_for_singleton(source):
    """Fix capitalize/lowercase handling on length-1 words by swapping case instead."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            # len(x) == 1 or x.isupper() or (x[0].islower() and x[1:].isupper())
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                text = source[_span(source, test)[0]:_span(source, test)[1]]
                if "len(" in text and "isupper" in text:
                    out.append(_splice(source, test, text.replace(".capitalize()", ".swapcase()")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "capitalize":
                obj = node.func.value
                expr = source[_span(source, obj)[0]:_span(source, obj)[1]]
                out.append(_splice(source, node, f"{expr}.swapcase()"))
    return out


def _rule_range_loop_off_by_one(source):
    """Fix loops that stop one step too early in a per-character scan."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            if len(node.args) == 1:
                arg = node.args[0]
                txt = source[_span(source, arg)[0]:_span(source, arg)[1]]
                if txt.endswith("-1"):
                    out.append(_splice(source, arg, txt[:-2]))
    return out


def _rule_swapcase_only_when_condition_matches(source):
    """Replace unconditional swapcase with conditional swapcase under the caps-lock predicate."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "swapcase":
                obj = call.func.value
                expr = source[_span(source, obj)[0]:_span(source, obj)[1]]
                new_stmt = f"if {expr}[1:]=={expr}[1:].upper():\n    print({expr}.swapcase())\nelse:\n    print({expr})"
                out.append(_splice(source, node, new_stmt))
    return out


def _rule_fix_upper_to_lower_on_allcaps(source):
    """Map all-uppercase inputs to lowercase instead of swapcase in common branches."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            text = source[_span(source, node)[0]:_span(source, node)[1]]
            if ".isupper()" in text and ".swapcase()" in text:
                out.append(_splice(source, node, text.replace(".swapcase()", ".lower()")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="capslock_swapcase_condition",
                apply=_rule_swapcase_only_when_condition_matches,
                symptoms=("wrong",),
            ),
            Rule(
                name="capslock_slice_isupper_check",
                apply=_rule_fix_isupper_slice_tests,
                symptoms=("wrong",),
            ),
            Rule(
                name="capslock_capitalize_to_swapcase",
                apply=_rule_swapcase_on_capslock,
                symptoms=("wrong",),
            ),
            Rule(
                name="capslock_singleton_capitalize_fix",
                apply=_rule_wrong_capitalize_for_singleton,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_range_scan",
                apply=_rule_range_loop_off_by_one,
                symptoms=("wrong", "timeout"),
            ),
            Rule(
                name="allcaps_use_lower_not_swapcase",
                apply=_rule_fix_upper_to_lower_on_allcaps,
                symptoms=("wrong",),
            ),
        ]