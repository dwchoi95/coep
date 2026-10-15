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


def _is_input_call(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input"


def _capslock_condition(s_expr):
    return f"({s_expr}[1:] == {s_expr}[1:].upper() or len({s_expr}) == 1)"


def _capslock_condition_isupper(s_expr):
    return f"({s_expr}.isupper() or {s_expr}[1:].isupper() or len({s_expr}) == 1)"


def _word_expr_from_assign(source, tree):
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)]
    for a in assigns:
        if _is_input_call(a.value):
            return a.targets[0].id
    return None


class Fixer:
    def rules(self):
        return [
            Rule("add_len_one_to_capslock_guard", self._add_len_one_to_capslock_guard, ("wrong",)),
            Rule("invert_lower_check_to_upper_suffix_check", self._invert_lower_check_to_upper_suffix_check, ("wrong",)),
            Rule("replace_late_isupper_with_suffix_isupper", self._replace_late_isupper_with_suffix_isupper, ("wrong",)),
            Rule("capitalize_to_swapcase_for_capslock", self._capitalize_to_swapcase_for_capslock, ("wrong",)),
            Rule("lower_to_swapcase_for_capslock", self._lower_to_swapcase_for_capslock, ("wrong",)),
            Rule("swapcase_needed_in_if_branch", self._swapcase_needed_in_if_branch, ("wrong",)),
            Rule("replace_unconditional_capitalize_with_conditional_swapcase", self._replace_unconditional_capitalize_with_conditional_swapcase, ("wrong",)),
            Rule("fix_singleton_upper_rule", self._fix_singleton_upper_rule, ("wrong",)),
            Rule("fix_truthy_isupper_or_islower_checks", self._fix_truthy_isupper_or_islower_checks, ("wrong",)),
            Rule("fix_range_off_by_one_on_suffix_scan", self._fix_range_off_by_one_on_suffix_scan, ("wrong",)),
        ]

    def _add_len_one_to_capslock_guard(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                seg = ast.get_source_segment(source, node)
                if not seg:
                    continue
                if ".isupper()" in seg and "len(" not in seg and "swapcase" not in seg:
                    new = seg + " or len(" + seg.split(".")[0].strip("() ") + ") == 1"
                    out.append(_splice(source, node, new))
        return out

    def _invert_lower_check_to_upper_suffix_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                seg = ast.get_source_segment(source, node)
                if seg and ".lower()" in seg and node.left and node.comparators:
                    left = ast.get_source_segment(source, node.left)
                    right = ast.get_source_segment(source, node.comparators[0])
                    if left and right:
                        out.append(_splice(source, node, f"{right}.upper() == {right}"))
        return out

    def _replace_late_isupper_with_suffix_isupper(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "isupper":
                parent = None
                for n in ast.walk(tree):
                    for child in ast.iter_child_nodes(n):
                        if child is node:
                            parent = n
                            break
                if isinstance(parent, ast.Call) and parent.func is node:
                    seg = ast.get_source_segment(source, parent)
                    if seg and "[1:]" not in seg and "word[0]" not in seg and "s[0]" not in seg:
                        base = ast.get_source_segment(source, node.value)
                        if base:
                            out.append(_splice(source, parent, f"{base}[1:].isupper()"))
        return out

    def _capitalize_to_swapcase_for_capslock(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "capitalize":
                base = ast.get_source_segment(source, node.func.value)
                if base:
                    out.append(_splice(source, node, f"{base}.swapcase()"))
        return out

    def _lower_to_swapcase_for_capslock(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "lower":
                base = ast.get_source_segment(source, node.func.value)
                if base:
                    out.append(_splice(source, node, f"{base}.swapcase()"))
        return out

    def _swapcase_needed_in_if_branch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test)
                if seg and ("isupper" in seg or "islower" in seg or "lower()" in seg):
                    new = seg.replace(".lower()", ".upper()")
                    new = new.replace(".capitalize()", ".swapcase()")
                    if new != seg:
                        out.append(_splice(source, node.test, new))
        return out

    def _replace_unconditional_capitalize_with_conditional_swapcase(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "capitalize":
                    base = ast.get_source_segment(source, call.func.value)
                    if base:
                        out.append(_splice(source, call, f"{base}.swapcase()"))
        return out

    def _fix_singleton_upper_rule(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                seg = ast.get_source_segment(source, node)
                if seg and "len(" in seg and "== 1" in seg and "isupper" in seg:
                    out.append(_splice(source, node, seg.replace("and", "or")))
        return out

    def _fix_truthy_isupper_or_islower_checks(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test)
                if seg and ".lower()" in seg and "or" in seg:
                    new = seg.replace(".lower()", ".isupper()")
                    out.append(_splice(source, node.test, new))
        return out

    def _fix_range_off_by_one_on_suffix_scan(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                args = node.iter.args
                if len(args) >= 2:
                    seg = ast.get_source_segment(source, node.iter)
                    if seg and "1" in seg and "len(" in seg:
                        new = seg.replace("range(1, len(", "range(1, len(")
                        if new == seg and "len(" in seg and "," in seg:
                            new = seg.replace("range(0, len(", "range(1, len(")
                        if new != seg:
                            out.append(_splice(source, node.iter, new))
        return out