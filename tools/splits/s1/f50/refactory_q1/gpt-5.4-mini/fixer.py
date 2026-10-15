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
    try:
        return _splice(source, target, ast.get_source_segment(source, new_node))
    except Exception:
        return None


class Fixer:
    def rules(self):
        return [
            Rule("empty_seq_returns_zero", self._empty_seq_returns_zero, ("wrong", "err:TypeError")),
            Rule("strict_lt_to_lte", self._strict_lt_to_lte, ("wrong",)),
            Rule("strict_gt_to_gte", self._strict_gt_to_gte, ("wrong",)),
            Rule("wrong_return_break_to_return", self._break_to_return, ("wrong", "timeout")),
            Rule("range_off_by_one_upper", self._range_off_by_one_upper, ("wrong", "timeout")),
            Rule("return_last_index_plus_one", self._return_last_index_plus_one, ("wrong",)),
            Rule("return_last_index_minus_one", self._return_last_index_minus_one, ("wrong",)),
            Rule("fix_none_or_empty_returns_zero", self._fix_none_or_empty_returns_zero, ("wrong", "err:TypeError")),
            Rule("comparison_to_prev_index", self._comparison_to_prev_index, ("wrong",)),
            Rule("position_counter_increment", self._position_counter_increment, ("wrong",)),
            Rule("fix_empty_check_before_indexing", self._fix_empty_check_before_indexing, ("err:IndexError", "wrong")),
        ]

    def _empty_seq_returns_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value in (None, False, "", "empty"):
                out.append(_splice(source, node, "return 0"))
        return out

    def _strict_lt_to_lte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                out.append(_splice(source, node, source[ls:le] + " <= " + source[rs:re]))
        return out

    def _strict_gt_to_gte(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                out.append(_splice(source, node, source[ls:le] + " >= " + source[rs:re]))
        return out

    def _break_to_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                out.append(_splice(source, node, "return i"))
        return out

    def _range_off_by_one_upper(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub) and isinstance(arg.left, ast.Call):
                    if isinstance(arg.left.func, ast.Name) and arg.left.func.id == "len":
                        seg = source[_span(source, arg)[0]:_span(source, arg)[1]]
                        out.append(_splice(source, node, f"range({source[_span(source, arg.left.args[0])[0]:_span(source, arg.left.args[0])[1]]})"))
        return out

    def _return_last_index_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                if isinstance(node.value.right, ast.Constant) and node.value.right.value == 1:
                    out.append(_splice(source, node, "return len(seq)"))
        return out

    def _return_last_index_minus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Sub):
                if isinstance(node.value.right, ast.Constant) and node.value.right.value == 1:
                    out.append(_splice(source, node, "return i"))
        return out

    def _fix_none_or_empty_returns_zero(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in (None, False):
                out.append(_splice(source, node, "0"))
        return out

    def _comparison_to_prev_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.Gt) and isinstance(node.left, ast.Name):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    out.append(_splice(source, node, source[ls:le] + " < " + source[rs:re]))
                if isinstance(node.ops[0], ast.Lt) and isinstance(node.left, ast.Name):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    out.append(_splice(source, node, source[ls:le] + " > " + source[rs:re]))
        return out

    def _position_counter_increment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
                if node.target.id in {"position", "counter", "a", "indx", "pos"}:
                    out.append(_splice(source, node, f"{node.target.id} = {node.target.id} + 1"))
        return out

    def _fix_empty_check_before_indexing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id in {"seq", "new_seq"}:
                if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                    if isinstance(node.comparators[0], (ast.Tuple, ast.List)) and len(node.comparators[0].elts) == 0:
                        out.append(_splice(source, node, f"len({node.left.id}) == 0"))
        return out