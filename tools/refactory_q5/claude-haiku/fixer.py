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


class Fixer:
    def rules(self):
        return [
            Rule(name="loop_condition_lte_to_lt", apply=self._loop_lte_to_lt, 
                 symptoms=("wrong",)),
            Rule(name="loop_condition_ge_to_gt", apply=self._loop_ge_to_gt,
                 symptoms=("wrong",)),
            Rule(name="hardcoded_slice_to_k", apply=self._hardcoded_slice,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_list", apply=self._return_wrong_list,
                 symptoms=("wrong",)),
            Rule(name="missing_break_in_loop", apply=self._missing_break,
                 symptoms=("wrong", "timeout")),
            Rule(name="missing_k_zero_check", apply=self._missing_k_zero,
                 symptoms=("wrong",)),
            Rule(name="append_index_not_value", apply=self._append_index_not_value,
                 symptoms=("wrong",)),
            Rule(name="counter_init_zero_should_be_one", apply=self._counter_init,
                 symptoms=("wrong",)),
        ]

    def _loop_lte_to_lt(self, source):
        """Fix: change while len(l) <= k to while len(l) < k"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 \
               and isinstance(node.ops[0], ast.LtE):
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " < " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out

    def _loop_ge_to_gt(self, source):
        """Fix: change while k >= 0 to while k > 0"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 \
               and isinstance(node.ops[0], ast.GtE):
                left = node.left
                right = node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " > " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out

    def _hardcoded_slice(self, source):
        """Fix: change return tmp[:5] to return tmp[:k]"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Slice):
                    upper = node.slice.upper
                    if isinstance(upper, ast.Constant) and isinstance(upper.value, int):
                        s, e = _span(source, upper)
                        out.append(_splice(source, upper, "k"))
        return out

    def _return_wrong_list(self, source):
        """Fix: change return lst[:k] to return result[:k] when appending to result"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value:
                if isinstance(node.value, ast.Subscript):
                    subscript = node.value
                    if isinstance(subscript.value, ast.Name):
                        if subscript.value.id == "lst":
                            s, e = _span(source, subscript.value)
                            out.append(_splice(source, subscript.value, "result"))
        return out

    def _missing_break(self, source):
        """Fix: add break statement after popping element in inner loop"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.body, list) and len(node.body) > 0:
                    last_stmt = node.body[-1]
                    if isinstance(last_stmt, ast.If):
                        if_node = last_stmt
                        if isinstance(if_node.body, list) and len(if_node.body) > 0:
                            last_if_stmt = if_node.body[-1]
                            if isinstance(last_if_stmt, ast.Expr) and \
                               isinstance(last_if_stmt.value, ast.Call):
                                call = last_if_stmt.value
                                if isinstance(call.func, ast.Attribute) and \
                                   call.func.attr == "pop":
                                    s, e = _span(source, if_node)
                                    if_text = source[s:e]
                                    if "break" not in if_text:
                                        lines = if_text.split('\n')
                                        if len(lines) > 1:
                                            indent = len(lines[-1]) - len(lines[-1].lstrip())
                                            new_if = if_text + "\n" + " " * (indent + 4) + "break"
                                            out.append(_splice(source, if_node, new_if))
        return out

    def _missing_k_zero(self, source):
        """Fix: add k == 0 check in if condition"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    comp = node.test
                    if len(comp.ops) == 1 and isinstance(comp.ops[0], ast.Eq):
                        if isinstance(comp.left, ast.Name) and comp.left.id == "lst":
                            if isinstance(comp.comparators[0], ast.List) and \
                               len(comp.comparators[0].elts) == 0:
                                s, e = _span(source, comp)
                                new_test = source[s:e] + " or k == 0"
                                out.append(_splice(source, comp, new_test))
        return out

    def _append_index_not_value(self, source):
        """Fix: change lst.extend([i]) to lst.extend([lst[i]])"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and \
                   node.func.attr == "extend" and len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.List) and len(arg.elts) == 1:
                        elem = arg.elts[0]
                        if isinstance(elem, ast.Name) and elem.id == "i":
                            s, e = _span(source, elem)
                            out.append(_splice(source, elem, "lst[i]"))
        return out

    def _counter_init(self, source):
        """Fix: change counter = 0 to counter = 1 when using counter <= k"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    if node.targets[0].id == "counter":
                        if isinstance(node.value, ast.Constant) and \
                           node.value.value == 0:
                            s, e = _span(source, node.value)
                            out.append(_splice(source, node.value, "1"))
        return out