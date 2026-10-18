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


def _replace_node(source, target, new_text):
    try:
        ast.parse(source)
    except SyntaxError:
        return []
    return [_splice(source, target, new_text)]


def _is_search_func(node):
    return isinstance(node, ast.FunctionDef) and node.name == "search"


def _empty_check_fix(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if _is_search_func(n)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.If):
                test = node.test
                if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                    parts = test.values
                    if any(isinstance(p, ast.Compare) and any(isinstance(op, ast.Eq) for op in p.ops) for p in parts):
                        for p in parts:
                            if isinstance(p, ast.Compare) and len(p.ops) == 1 and isinstance(p.ops[0], ast.Eq):
                                if isinstance(p.left, ast.Name) and p.left.id in {"seq", "seqs", "lst", "list1", "newseq"}:
                                    rhs = p.comparators[0]
                                    if isinstance(rhs, ast.Tuple) and len(rhs.elts) == 0:
                                        s, e = _span(source, p)
                                        out.append(source[:s] + f"{p.left.id} == []" + source[e:])
                                        s, e = _span(source, test)
                                        out.append(source[:s] + f"{p.left.id} == [] or {p.left.id} == ()" + source[e:])
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                    if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Tuple) and len(test.comparators[0].elts) == 0:
                        s, e = _span(source, test)
                        out.append(source[:s] + f"{test.left.id} == []" + source[e:])
    return out


def _fix_return_len_off_by_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if _is_search_func(n)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                left, right = node.value.left, node.value.right
                if isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == "len":
                    if isinstance(right, ast.Constant) and right.value == 1:
                        s, e = _span(source, node.value)
                        out.append(source[:s] + "len(seq)" + source[e:])
    return out


def _fix_strict_to_nonstrict_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if _is_search_func(n)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.Lt):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    out.append(source[:ls] + source[ls:le] + " <= " + source[rs:re] + source[re:])
                elif isinstance(op, ast.Gt):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    out.append(source[:ls] + source[ls:le] + " >= " + source[rs:re] + source[re:])
    return out


def _fix_immediate_return_else(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if _is_search_func(n)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                if len(node.orelse) == 0:
                    last = fn.body[-1] if fn.body else None
                    if last is node:
                        s, e = _span(source, node)
                        txt = source[s:e]
                        if "\n        return" in txt:
                            out.append(source[:s] + txt.replace("\n        return", "\n    return", 1) + source[e:])
    return out


def _fix_newseq_usage(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for fn in [n for n in ast.walk(tree) if _is_search_func(n)]:
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        if "newseq" in names:
            for node in ast.walk(fn):
                if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                    cmp = node.test
                    if isinstance(cmp.left, ast.Subscript) and isinstance(cmp.left.value, ast.Name) and cmp.left.value.id == "newseq":
                        s, e = _span(source, cmp.left)
                        out.append(source[:s] + "seq[-1]" + source[e:])
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="empty_sequence_returns_zero", apply=_empty_check_fix, symptoms=("wrong", "err:IndexError")),
            Rule(name="strict_comparison_to_non_strict", apply=_fix_strict_to_nonstrict_compare, symptoms=("wrong",)),
            Rule(name="len_plus_one_off_by_one", apply=_fix_return_len_off_by_one, symptoms=("wrong",)),
            Rule(name="immediate_return_in_if_needs_else_or_dedent", apply=_fix_immediate_return_else, symptoms=("wrong",)),
            Rule(name="wrong_newseq_guard_uses_uninitialized_seq", apply=_fix_newseq_usage, symptoms=("err:UnboundLocalError", "wrong")),
        ]