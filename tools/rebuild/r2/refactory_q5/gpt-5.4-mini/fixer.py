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


def _replace_node(source, target, new_node):
    return _splice(source, target, ast.get_source_segment(source, new_node))


def _max_to_min(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re = _span(source, right)
            out.append(_splice(source, node, source[ls:le] + " > " + source[rs:re]))
    return out


def _append_removed_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Call):
                inner = node.args[0]
                if isinstance(inner.func, ast.Attribute) and inner.func.attr == "remove":
                    arg = ast.get_source_segment(source, inner.args[0])
                    if arg is None:
                        continue
                    new = f"{ast.get_source_segment(source, node.func.value)}.append({arg})"
                    out.append(_splice(source, node, new))
    return out


def _fix_return_slice_k(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == 5:
            out.append(_splice(source, node.slice, "k"))
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.BinOp):
            txt = ast.get_source_segment(source, node.slice)
            if txt and txt.endswith("1") and "k" in txt:
                out.append(_splice(source, node, source[_span(source, node)[0]:_span(source, node)[1]].replace("k-1", "k").replace("k+1", "k")))
    return out


def _fix_pop_max_to_index_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "pop":
            if len(node.args) == 1:
                arg = ast.get_source_segment(source, node.args[0])
                if arg and arg.startswith("max("):
                    new = f"{ast.get_source_segment(source, node.func.value)}.pop({ast.get_source_segment(source, node.func.value)}.index(max({ast.get_source_segment(source, node.func.value)})))"
                    out.append(_splice(source, node, new))
    return out


def _fix_append_max_remove_max(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "append":
            if len(node.args) == 1:
                arg = ast.get_source_segment(source, node.args[0])
                if arg == "lst.remove(max(lst))" or arg == "lst.remove(maximum)":
                    container = ast.get_source_segment(source, node.func.value)
                    new = f"{container}.append(max(lst))"
                    out.append(_splice(source, node, new))
    return out


def _fix_compare_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.left, ast.Name):
            if len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Name):
                l = node.left.id
                r = node.comparators[0].id
                if l != r:
                    seg = ast.get_source_segment(source, node)
                    if seg and (l in seg or r in seg):
                        out.append(_splice(source, node, seg.replace(l, r)))
    return out


def _fix_off_by_one_range(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
            seg = ast.get_source_segment(source, node)
            if seg and "k-1" in seg:
                out.append(_splice(source, node, seg.replace("k-1", "k")))
            elif seg and "k+1" in seg:
                out.append(_splice(source, node, seg.replace("k+1", "k")))
    return out


def _fix_return_lst_to_result(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            seg = ast.get_source_segment(source, node)
            if seg and "return lst[:k]" in seg:
                out.append(_splice(source, node, seg.replace("return lst[:k]", "return result[:k]").replace("return lst[:k+1]", "return result[:k]").replace("return lst[:k-1]", "return result[:k]")))
            elif seg and "return new_lst" in seg and "[:k]" not in seg:
                out.append(_splice(source, node, seg + "[:k]"))
    return out


def _fix_missing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if not tree.body:
        return []
    func = tree.body[0]
    if not isinstance(func, ast.FunctionDef):
        return []
    if any(isinstance(n, ast.Return) for n in ast.walk(func)):
        return []
    return []


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_lt_to_gt", apply=_max_to_min, symptoms=("wrong", "timeout")),
            Rule(name="append_removed_result", apply=_append_removed_call, symptoms=("wrong",)),
            Rule(name="slice_k_not_constant_or_off_by_one", apply=_fix_return_slice_k, symptoms=("wrong",)),
            Rule(name="pop_max_should_use_index", apply=_fix_pop_max_to_index_max, symptoms=("wrong", "err:TypeError")),
            Rule(name="append_max_then_remove_max", apply=_fix_append_max_remove_max, symptoms=("wrong",)),
            Rule(name="name_mismatch_in_comparison", apply=_fix_compare_name_mismatch, symptoms=("err:NameError", "wrong")),
            Rule(name="range_off_by_one", apply=_fix_off_by_one_range, symptoms=("wrong",)),
            Rule(name="return_wrong_variable", apply=_fix_return_lst_to_result, symptoms=("wrong",)),
            Rule(name="missing_return_after_loop", apply=_fix_missing_return, symptoms=("wrong",)),
        ]