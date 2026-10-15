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


def _replace_node(source, old, new_text):
    return _splice(source, old, new_text)


def _is_search_def(node):
    return isinstance(node, ast.FunctionDef) and node.name == "search"


def _empty_check_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in tree.body:
        if not _is_search_def(fn):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.left, ast.Name) and node.left.id == "seq":
                    if len(node.comparators) == 1:
                        comp = node.comparators[0]
                        if isinstance(comp, ast.Tuple) and comp.elts == []:
                            out.append(_replace_node(source, node, "not seq"))
                        elif isinstance(comp, ast.List) and comp.elts == []:
                            out.append(_replace_node(source, node, "not seq"))
    return out


def _strict_to_nonstrict(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " <= " + source[rs:re_]))
            elif isinstance(op, ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                out.append(_replace_node(source, node, source[ls:le] + " >= " + source[rs:re_]))
    return out


def _fix_return_len_minus_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp):
            b = node.value
            if isinstance(b.op, ast.Add) and isinstance(b.right, ast.Constant) and b.right.value == 1:
                if isinstance(b.left, ast.Name) and b.left.id in {"i", "idx", "index", "counter", "c"}:
                    out.append(_replace_node(source, node.value, "len(seq)"))
    return out


def _fix_off_by_one_len_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Constant) and node.value.value in {-1, None, ()}:
                out.append(_replace_node(source, node.value, "0"))
    return out


def _fix_range_len(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            it = node.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                if len(it.args) == 1:
                    arg = it.args[0]
                    if isinstance(arg, ast.Name) and arg.id == "len":
                        continue
                    txt = ast.get_source_segment(source, arg)
                    if txt and txt == "len(seq)+1":
                        out.append(_replace_node(source, it, "range(len(seq))"))
    return out


def _fix_empty_seq_guard_insert(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in tree.body:
        if not _is_search_def(fn):
            continue
        if fn.body and isinstance(fn.body[0], ast.If):
            test = fn.body[0].test
            if isinstance(test, ast.Compare):
                seg = ast.get_source_segment(source, test)
                if seg in {"seq == ()", "seq == []", "len(seq) == 0"}:
                    if len(fn.body[0].body) == 1 and isinstance(fn.body[0].body[0], ast.Return):
                        rv = fn.body[0].body[0].value
                        if isinstance(rv, ast.Constant) and rv.value in {-1, None, ()}:
                            out.append(_replace_node(source, rv, "0"))
    return out


def _fix_return_in_loop_to_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if len(node.body) >= 2:
                last = node.body[-1]
                if isinstance(last, ast.Return):
                    seg = ast.get_source_segment(source, last.value)
                    if seg in {"len(seq) + 1", "i + 1", "i+1"}:
                        out.append(_replace_node(source, last.value, "len(seq)"))
    return out


def _fix_append_insert_mutation(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Name) and node.value.id == "seq":
                out.append(_replace_node(source, node.value, "len(seq)"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_seq_guard_to_zero", apply=_empty_check_fix, symptoms=("wrong", "err:IndexError")),
            Rule(name="strict_to_nonstrict_compare", apply=_strict_to_nonstrict, symptoms=("wrong",)),
            Rule(name="return_len_minus_one_fix", apply=_fix_return_len_minus_one, symptoms=("wrong",)),
            Rule(name="return_noninteger_empty_fix", apply=_fix_off_by_one_len_return, symptoms=("wrong",)),
            Rule(name="range_len_off_by_one", apply=_fix_range_len, symptoms=("wrong", "timeout")),
            Rule(name="guard_return_zero", apply=_fix_empty_seq_guard_insert, symptoms=("wrong",)),
            Rule(name="loop_terminal_return_len", apply=_fix_return_in_loop_to_else, symptoms=("wrong",)),
            Rule(name="returned_seq_as_position", apply=_fix_append_insert_mutation, symptoms=("wrong",)),
        ]