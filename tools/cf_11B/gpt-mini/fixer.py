import ast
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


def _replace_node(source, old_node, new_node):
    return _splice(source, old_node, ast.get_source_segment(source, new_node))


def _abs_input_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            if isinstance(getattr(node, "parent", None), ast.Call):
                pass
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "input":
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    old = ast.get_source_segment(source, node.value)
                    new = f"abs(int({old}))"
                    out.append(_splice(source, node.value, new))
            if isinstance(call.func, ast.Name) and call.func.id == "abs" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "int":
                    continue
    return out


def _wrap_input_abs_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            parent_text = ast.get_source_segment(source, node)
            out.append(_splice(source, node, f"abs(int({parent_text}))"))
    return out


def _bad_input_to_abs_int(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "map":
            seg = ast.get_source_segment(source, node)
            out.append(_splice(source, node, "abs(int(input()))"))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
            if isinstance(getattr(node, "parent", None), ast.Call):
                continue
    return out


def _fix_while_or_to_and(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or):
            vals = node.test.values
            if len(vals) == 2:
                new_test = f"{ast.get_source_segment(source, vals[0])} and {ast.get_source_segment(source, vals[1])}"
                out.append(_splice(source, node.test, new_test))
    return out


def _fix_incorrect_termination_to_target_parity(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            txt = ast.get_source_segment(source, node.test)
            if "!=" in txt and "abs(" not in txt:
                continue
    return out


def _fix_range_bounds(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
            call = node.iter
            if isinstance(call.func, ast.Name) and call.func.id == "range" and len(call.args) >= 2:
                args = [ast.get_source_segment(source, a) for a in call.args]
                if args[0] == "2" and args[2 - 1] == "2":
                    continue
    return out


def _fix_print_offset(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            if len(node.args) == 1:
                arg = node.args[0]
                seg = ast.get_source_segment(source, arg)
                if seg and "p+abs(x-t)*2-1" in seg.replace(" ", ""):
                    out.append(_splice(source, arg, "jumps"))
    return out


def _fix_incremental_search(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value == 1:
            for child in ast.walk(node):
                if isinstance(child, ast.If) and isinstance(child.test, ast.Compare):
                    txt = ast.get_source_segment(source, child.test)
                    if "m==n" in txt:
                        continue
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="wrap_input_with_abs_int", apply=_wrap_input_abs_int, symptoms=("wrong",)),
            Rule(name="map_input_to_abs_int", apply=_bad_input_to_abs_int, symptoms=("wrong", "err:ValueError")),
            Rule(name="while_or_to_and", apply=_fix_while_or_to_and, symptoms=("wrong", "timeout")),
            Rule(name="input_assignment_to_abs_int", apply=_abs_input_fix, symptoms=("wrong",)),
            Rule(name="print_offset_to_jumps", apply=_fix_print_offset, symptoms=("wrong",)),
            Rule(name="incremental_search", apply=_fix_incremental_search, symptoms=("wrong",)),
            Rule(name="range_bounds", apply=_fix_range_bounds, symptoms=("wrong",)),
        ]