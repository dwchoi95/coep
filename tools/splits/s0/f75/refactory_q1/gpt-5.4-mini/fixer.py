from src.core.repair import Rule
import ast


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


def _replace_node(source, old_node, new_text):
    return _splice(source, old_node, new_text)


def _build_compare(source, node, op_text):
    left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
    right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
    return f"{left} {op_text} {right}"


def _fix_none_return_in_empty_case(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            parent = None
            for p in ast.walk(tree):
                for ch in ast.iter_child_nodes(p):
                    if ch is node:
                        parent = p
                        break
            if isinstance(parent, ast.If):
                new = _splice(source, node, "0")
                out.append(new)
    return out


def _fix_strict_to_nonstrict(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, ast.Lt):
                out.append(_replace_node(source, node, _build_compare(source, node, "<=")))
            elif isinstance(op, ast.Gt):
                out.append(_replace_node(source, node, _build_compare(source, node, ">=")))
    return out


def _fix_off_by_one_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
            left = node.value.left
            right = node.value.right
            if isinstance(right, ast.Constant) and right.value == 1:
                s, e = _span(source, left)
                out.append(_splice(source, node.value, source[s:e]))
        if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Sub):
            left = node.value.left
            right = node.value.right
            if isinstance(right, ast.Constant) and right.value == 1:
                s, e = _span(source, left)
                out.append(_splice(source, node.value, source[s:e]))
    return out


def _fix_bare_pass_empty(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                pass_node = node.body[0]
                out.append(_splice(source, pass_node, "return 0"))
    return out


def _fix_return_x_instead_of_index(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            if node.value.id in {"x", "elem", "element"}:
                out.append(_splice(source, node.value, "i"))
    return out


def _fix_loop_first_branch_returns_zero(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value == 0:
            out.append(source)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="empty_sequence_returns_zero_instead_of_none",
                apply=self._empty_returns_zero,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="strict_comparison_should_be_non_strict",
                apply=self._strict_to_nonstrict,
                symptoms=("wrong",),
            ),
            Rule(
                name="off_by_one_return_expression",
                apply=self._off_by_one_return,
                symptoms=("wrong",),
            ),
            Rule(
                name="return_index_not_value",
                apply=self._return_index_not_value,
                symptoms=("wrong",),
            ),
            Rule(
                name="range_len_off_by_one_to_full_length",
                apply=self._range_len_off_by_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_pass_should_return_zero",
                apply=self._bare_pass_empty,
                symptoms=("wrong", "err:TypeError"),
            ),
            Rule(
                name="missing_final_return_zero",
                apply=self._missing_final_return_zero,
                symptoms=("wrong",),
            ),
            Rule(
                name="loop_condition_strict_to_nonstrict",
                apply=self._loop_condition_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="while_increment_by_position_should_increment_by_one",
                apply=self._while_increment_fix,
                symptoms=("timeout", "wrong"),
            ),
        ]

    def _empty_returns_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
                out.append(_splice(source, node, "return 0"))
        return out

    def _strict_to_nonstrict(self, source):
        return _fix_strict_to_nonstrict(source)

    def _off_by_one_return(self, source):
        return _fix_off_by_one_return(source)

    def _return_index_not_value(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "x":
                out.append(_splice(source, node.value, "i"))
        return out

    def _range_len_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
                if len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                        s, e = _span(source, arg)
                        out.append(source[:s] + source[_span(source, arg.left)[0]:_span(source, arg.left)[1]] + source[e:])
        return out

    def _bare_pass_empty(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                out.append(_splice(source, node, "return 0"))
        return out

    def _missing_final_return_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "search"]:
            if fn.body and isinstance(fn.body[-1], ast.Return):
                rv = fn.body[-1].value
                if isinstance(rv, ast.Constant) and rv.value is None:
                    out.append(_splice(source, fn.body[-1], "    return 0"))
        return out

    def _loop_condition_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Lt) and isinstance(node.left, ast.Name) and node.left.id in {"x", "value", "val"}:
                    out.append(_replace_node(source, node, _build_compare(source, node, "<=")))
                if isinstance(node.ops[0], ast.Gt) and isinstance(node.left, ast.Name) and node.left.id in {"x", "value", "val"}:
                    out.append(_replace_node(source, node, _build_compare(source, node, ">=")))
        return out

    def _while_increment_fix(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if isinstance(node.value, ast.Name) and node.value.id == node.target.id:
                    out.append(_splice(source, node.value, "1"))
        return out