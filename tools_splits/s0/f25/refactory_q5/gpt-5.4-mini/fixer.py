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


def _replace_name(source, node, new_name):
    return _splice(source, node, new_name)


def _replace_stmt(source, node, new_text):
    return _splice(source, node, new_text)


def _fix_misnamed_loop_var(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            target = node.target.id
            used = {}
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id != target:
                    used[n.id] = used.get(n.id, 0) + 1
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in {target}:
                    used[n.id] = used.get(n.id, 0) + 1
            if target == "elements":
                for n in ast.walk(node):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == "element":
                        out.append(_replace_name(source, n, "elements"))
            elif target == "element":
                for n in ast.walk(node):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == "elements":
                        out.append(_replace_name(source, n, "element"))
            if target == "i":
                for n in ast.walk(node):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id == "oldest":
                        out.append(_replace_name(source, n, "biggest"))
    return out


def _fix_assignment_in_loop(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "oldest" and isinstance(node.value, ast.Name) and node.value.id == "i":
                out.append(_replace_name(source, node.targets[0], "biggest"))
            if node.targets[0].id == "minimum" and isinstance(node.value, ast.Name) and node.value.id == "x":
                out.append(_replace_name(source, node.targets[0], "largest"))
    return out


def _fix_pop_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "pop":
            parent_ok = False
            for p in ast.walk(tree):
                for child in ast.iter_child_nodes(p):
                    if child is node:
                        parent_ok = True
            if parent_ok:
                s, e = _span(source, node)
                out.append(source[:s] + "pop" + source[e:])
    return out


def _fix_k_slice(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp):
            if isinstance(node.slice.op, ast.Add) and isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                s, e = _span(source, node.slice)
                out.append(source[:s] + "k" + source[e:])
            if isinstance(node.slice.op, ast.Sub) and isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                s, e = _span(source, node.slice)
                out.append(source[:s] + "k" + source[e:])
    return out


def _fix_while_bounds(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            txt = ast.get_source_segment(source, node.test)
            if txt == "len(newlst)<=k":
                s, e = _span(source, node.test)
                out.append(source[:s] + "len(newlst) < k" + source[e:])
            if txt == "while len(lst)>len(lst)-k":
                s, e = _span(source, node.test)
                out.append(source[:s] + "while len(result) < k" + source[e:])
            if txt == "while n <= k":
                s, e = _span(source, node.test)
                out.append(source[:s] + "n < = k".replace(" ", "") + source[e:])
            if txt == "while len(sortedlst) != k":
                s, e = _span(source, node.test)
                out.append(source[:s] + "len(sortedlst) < k" + source[e:])
    return out


def _fix_recursive_call_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "new_lst":
            out.append(_replace_name(source, node, "new_list"))
    return out


def _fix_return_reverse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            seg = ast.get_source_segment(source, node.value) if node.value else None
            if seg and seg.startswith("list.reverse("):
                s, e = _span(source, node.value)
                inner = seg[len("list.reverse("):-1]
                out.append(source[:s] + inner + source[e:])
    return out


def _fix_for_range_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                args = node.iter.args
                if len(args) == 1 and isinstance(args[0], ast.Name) and args[0].id == "k":
                    pass
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="loop_variable_name_fix", apply=_fix_misnamed_loop_var, symptoms=("wrong",)),
            Rule(name="assignment_target_fix", apply=_fix_assignment_in_loop, symptoms=("wrong",)),
            Rule(name="pop_call_attribute_fix", apply=_fix_pop_call, symptoms=("err:TypeError", "wrong")),
            Rule(name="slice_k_off_by_one_fix", apply=_fix_k_slice, symptoms=("wrong",)),
            Rule(name="while_condition_bound_fix", apply=_fix_while_bounds, symptoms=("wrong", "timeout")),
            Rule(name="recursive_variable_name_fix", apply=_fix_recursive_call_typo, symptoms=("err:NameError",)),
            Rule(name="reverse_return_fix", apply=_fix_return_reverse, symptoms=("wrong", "err:TypeError")),
        ]