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


def _replace_call_attr(source, tree, old_name, new_name):
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == old_name:
            out.append(_splice(source, node, source[_span(source, node)[0]:_span(source, node)[1]].replace(old_name, new_name, 1)))
    return out


def _swapcase_to_capitalize_on_if(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if not node.orelse and len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                expr = node.body[0].value
                if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "print" and len(expr.args) == 1:
                    arg = expr.args[0]
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "title":
                        new_arg = source[_span(source, arg.func.value)[0]:_span(source, arg.func.value)[1]] + ".swapcase()"
                        out.append(_splice(source, arg, new_arg))
    return out


def _capitalize_to_swapcase_in_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.List):
            elts = node.value.elts
            if len(elts) == 2:
                for e in elts:
                    if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "capitalize":
                        s, epos = _span(source, e.func)
                        new_text = source[s:epos].replace("capitalize", "swapcase", 1)
                        out.append(_splice(source, e, new_text + source[epos:_span(source, e)[1]] if False else new_text))
    return out


def _fix_list_index_capitalize(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" and len(node.args) == 1:
            arg = node.args[0]
            if isinstance(arg, ast.Subscript) and isinstance(arg.value, ast.List):
                txt = source[_span(source, arg)[0]:_span(source, arg)[1]]
                if ".capitalize()" in txt:
                    out.append(_splice(source, arg, txt.replace(".capitalize()", ".swapcase()")))
    return out


def _fix_upper_truthiness(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left_txt = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
            right_txt = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
            if ".upper()" in right_txt and left_txt.endswith("[1:]"):
                out.append(_splice(source, node, left_txt + ".isupper()"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "upper":
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if txt.endswith(".upper"):
                out.append(_splice(source, node, txt + "()"))
    return out


def _add_len_one_or_isupper(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "word.isupper()" in txt and "len(word) == 1" not in txt:
                out.append(_splice(source, node, txt[:-1] + " or len(word) == 1)"))
            if "word[1:].isupper()" in txt and "len(word) == 1" not in txt:
                out.append(_splice(source, node, txt[:-1] + " or len(word) == 1)"))
            if "a[1:].isupper()" in txt and "len(a) == 1" not in txt:
                out.append(_splice(source, node, txt[:-1] + " or (len(a) == 1 and a.islower()))"))
    return out


def _fix_swapcase_condition(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            cond = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if "s.isupper()" in cond and "len(s) == 1" not in cond:
                out.append(_splice(source, node.test, cond.replace("s.isupper()", "s.isupper() or len(s) == 1")))
            if "word == word.capitalize()" in cond:
                out.append(_splice(source, node.test, cond.replace("word == word.capitalize() or word[0:] == word[0:].capitalize() or len(word) == 1", "word == word.upper() or word[1:] == word[1:].upper() or len(word) == 1")))
    return out


def _capitalize_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize":
            out.append(_splice(source, node.func, source[_span(source, node.func)[0]:_span(source, node.func)[1]].replace("capitalize", "swapcase")))
    return out


def _fix_title_to_swapcase(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "title":
            out.append(_splice(source, node.func, source[_span(source, node.func)[0]:_span(source, node.func)[1]].replace("title", "swapcase")))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="capitalize_misused_for_capslock", apply=_capitalize_to_swapcase, symptoms=("wrong",)),
            Rule(name="title_misused_for_capslock", apply=_fix_title_to_swapcase, symptoms=("wrong",)),
            Rule(name="truthy_upper_method_call", apply=_fix_upper_truthiness, symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_len_one_branch", apply=_add_len_one_or_isupper, symptoms=("wrong",)),
            Rule(name="swapcase_condition_missing_len_one", apply=_fix_swapcase_condition, symptoms=("wrong",)),
            Rule(name="list_index_capitalize_to_swapcase", apply=_fix_list_index_capitalize, symptoms=("wrong",)),
        ]