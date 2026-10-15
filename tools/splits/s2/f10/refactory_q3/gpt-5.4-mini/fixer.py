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


def _iter_fix(source):
    """Fix loops that iterate over the wrong variable or collection."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Name) and isinstance(node.target, ast.Name):
                if node.iter.id != node.target.id:
                    out.append(_splice(source, node.iter, node.target.id))
    return out


def _wrong_return_name(source):
    """Return the accumulated unique list instead of the input list."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            name = node.value.id
            func = None
            parent_stack = [tree]
            for n in ast.walk(tree):
                for child in ast.iter_child_nodes(n):
                    if child is node:
                        func = n
                        break
                if func is not None:
                    break
            if func and isinstance(func, ast.FunctionDef):
                candidates = []
                for n in ast.walk(func):
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            if isinstance(t, ast.Name) and t.id != name:
                                candidates.append(t.id)
                    if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                        if n.target.id != name:
                            candidates.append(n.target.id)
                if candidates:
                    repl = candidates[-1]
                    out.append(_splice(source, node.value, repl))
    return out


def _call_vs_index_fix(source):
    """Fix list/tuple method-subscript mistakes like append[x] or count[x]."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr in {"append", "count", "remove", "extend"}:
                if isinstance(node.slice, ast.Name):
                    new_text = source[_span(source, node.value.value)[0]:_span(source, node.value.value)[1]]
                    attr_span = _span(source, node.value)[0]
                    attr_end = _span(source, node.value)[1]
                    arg = source[_span(source, node.slice)[0]:_span(source, node.slice)[1]]
                    out.append(source[:attr_span] + new_text + "." + node.value.attr + "(" + arg + ")" + source[_span(source, node)[1]:])
    return out


def _binary_plus_list_fix(source):
    """Fix scalar += item used where list concatenation is intended."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name):
                if isinstance(node.value, ast.Name):
                    repl = "[" + source[_span(source, node.value)[0]:_span(source, node.value)[1]] + "]"
                    out.append(_splice(source, node.value, repl))
    return out


def _count_compare_fix(source):
    """Replace count(x)==0 / count(x) > 1 style duplicate checks with membership checks."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left = node.left
            comp = node.comparators[0]
            if isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "count":
                if isinstance(node.ops[0], ast.Eq) and isinstance(comp, ast.Constant) and comp.value == 0:
                    arg = left.args[0]
                    new_text = source[_span(source, arg)[0]:_span(source, arg)[1]] + " not in " + source[_span(source, left.func.value)[0]:_span(source, left.func.value)[1]]
                    out.append(_splice(source, node, new_text))
                if isinstance(node.ops[0], ast.Gt) and isinstance(comp, ast.Constant) and comp.value == 1:
                    arg = left.args[0]
                    new_text = source[_span(source, arg)[0]:_span(source, arg)[1]] + " in " + source[_span(source, left.func.value)[0]:_span(source, left.func.value)[1]]
                    out.append(_splice(source, node, new_text))
    return out


def _range_bound_fix(source):
    """Fix off-by-one range bounds that skip the last element."""
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
                out.append(_splice(source, arg, f"len({txt})"))
            elif len(node.args) == 2:
                start, stop = node.args
                stop_txt = source[_span(source, stop)[0]:_span(source, stop)[1]]
                if stop_txt.endswith("-1"):
                    new_stop = stop_txt[:-2].rstrip()
                    out.append(_splice(source, stop, new_stop))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="iter_over_target_not_result", apply=_iter_fix, symptoms=("wrong",)),
            Rule(name="return_accumulator_instead_of_input", apply=_wrong_return_name, symptoms=("wrong",)),
            Rule(name="method_subscript_to_call", apply=_call_vs_index_fix, symptoms=("wrong", "err:TypeError")),
            Rule(name="list_concat_needs_brackets", apply=_binary_plus_list_fix, symptoms=("wrong", "err:TypeError")),
            Rule(name="count_based_duplicate_check_to_membership", apply=_count_compare_fix, symptoms=("wrong",)),
            Rule(name="range_bound_off_by_one", apply=_range_bound_fix, symptoms=("wrong",)),
        ]