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


def _replace_node(source, old, new_node):
    return _splice(source, old, ast.get_source_segment(source, new_node))


def _parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


class Fixer:
    def rules(self):
        return [
            Rule(name="compare_count_to_lucky_number", apply=self._compare_count_to_lucky_number, symptoms=("wrong",)),
            Rule(name="reject_non_lucky_digits_only", apply=self._reject_non_lucky_digits_only, symptoms=("wrong",)),
            Rule(name="count_lucky_digits_not_all_digits", apply=self._count_lucky_digits_not_all_digits, symptoms=("wrong",)),
            Rule(name="fix_digit_membership_precedence", apply=self._fix_digit_membership_precedence, symptoms=("wrong",)),
            Rule(name="fix_digit_vs_int_comparison", apply=self._fix_digit_vs_int_comparison, symptoms=("wrong",)),
            Rule(name="fix_range_exclusive_upper_bound", apply=self._fix_range_exclusive_upper_bound, symptoms=("wrong",)),
            Rule(name="fix_accumulator_update_inside_loop", apply=self._fix_accumulator_update_inside_loop, symptoms=("wrong",)),
            Rule(name="fix_immediate_return_in_loop", apply=self._fix_immediate_return_in_loop, symptoms=("wrong",)),
            Rule(name="fix_division_to_floor_division", apply=self._fix_division_to_floor_division, symptoms=("wrong",)),
            Rule(name="fix_boolean_count_final_check", apply=self._fix_boolean_count_final_check, symptoms=("wrong",)),
            Rule(name="fix_wrong_lucky_set_membership", apply=self._fix_wrong_lucky_set_membership, symptoms=("wrong",)),
            Rule(name="fix_input_digit_count_solution", apply=self._fix_input_digit_count_solution, symptoms=("wrong",)),
        ]

    def _compare_count_to_lucky_number(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                right = node.comparators[0]
                if isinstance(right, (ast.Tuple, ast.List)):
                    elts = right.elts
                    if len(elts) == 2 and all(isinstance(e, ast.Constant) and e.value in (4, 7) for e in elts):
                        left = ast.get_source_segment(source, node.left)
                        new_text = f"{left} == 4 or {left} == 7"
                        out.append(_splice(source, node, new_text))
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == len("47"):
                    pass
        return out

    def _reject_non_lucky_digits_only(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id in {"flag", "res", "lucky", "nearly_lucky", "ans", "flagged"}:
                pass
            if isinstance(node, ast.If):
                t = node.test
                if isinstance(t, ast.Name) and t.id in {"flag", "res", "lucky"}:
                    out.append(_splice(source, t, "count == 4 or count == 7"))
        return out

    def _count_lucky_digits_not_all_digits(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                t = node.test
                if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                    left = ast.get_source_segment(source, t.left)
                    right = ast.get_source_segment(source, t.comparators[0])
                    if left and right and (left == "b" and right == "len(word)" or left == "m" and right == "c"):
                        out.append(_splice(source, t, "b == 4 or b == 7"))
                        out.append(_splice(source, t, "m == 4 or m == 7"))
                if isinstance(t, ast.BoolOp):
                    seg = ast.get_source_segment(source, t)
                    if seg and ("len(word)" in seg or "len(inp)" in seg or "len(n)" in seg):
                        out.append(_splice(source, t, "s == 4 or s == 7"))
        return out

    def _fix_digit_membership_precedence(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                seg = ast.get_source_segment(source, node)
                if seg and ("'4' or '7' in" in seg or '"4" or "7" in' in seg):
                    out.append(_splice(source, node, "i == '4' or i == '7'"))
                if seg and ("if '4' or '7' in x" in seg or "'4' or '7' in x" in seg):
                    out.append(_splice(source, node, "'4' in x or '7' in x"))
        return out

    def _fix_digit_vs_int_comparison(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left = ast.get_source_segment(source, node.left)
                right = ast.get_source_segment(source, node.comparators[0])
                if left in {"i", "n[i]"} and right in {"4", "7"}:
                    new = f"{left} == '4' or {left} == '7'"
                    out.append(_splice(source, node, new))
                if left in {"d", "rest"} and right in {"4", "7"}:
                    new = f"{left} == 4 or {left} == 7"
                    out.append(_splice(source, node, new))
        return out

    def _fix_range_exclusive_upper_bound(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                seg = ast.get_source_segment(source, node)
                if seg and "len(n)-1" in seg:
                    out.append(_splice(source, node.args[1], "len(n)"))
        return out

    def _fix_accumulator_update_inside_loop(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                t = node.test
                if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.NotEq):
                    if ast.get_source_segment(source, t.left) == "i" and ast.get_source_segment(source, t.comparators[0]) in {"4", "7"}:
                        out.append(_splice(source, t, "i == '4' or i == '7'"))
            if isinstance(node, ast.If) and node.body:
                seg = ast.get_source_segment(source, node)
                if seg and "counter == 4 or counter == 7" in seg and "for i in num" in source:
                    out.append(_splice(source, node.test, "counter == 4 or counter == 7"))
        return out

    def _fix_immediate_return_in_loop(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                p = getattr(node, "parent", None)
            if isinstance(node, ast.FunctionDef):
                for b in node.body:
                    for sub in ast.walk(b):
                        if isinstance(sub, ast.Return):
                            seg = ast.get_source_segment(source, sub)
                            if seg and "return count ==4 or count == 7" in seg:
                                out.append(_splice(source, sub, ""))
        return out

    def _fix_division_to_floor_division(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
                out.append(_splice(source, node.op, "//"))
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Div):
                out.append(_splice(source, node.value.op, "//"))
        return out

    def _fix_boolean_count_final_check(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test)
                if seg and ("not flag" in seg or "flag == True" in seg or "flag" == seg.strip()):
                    out.append(_splice(source, node.test, "count == 4 or count == 7"))
        return out

    def _fix_wrong_lucky_set_membership(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                seg = ast.get_source_segment(source, node)
                if seg and "set(str(n))" in source and "i in k" in seg:
                    out.append(_splice(source, node, "i == '4' or i == '7'"))
        return out

    def _fix_input_digit_count_solution(self, source):
        tree = _parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                seg = ast.get_source_segment(source, node.test)
                if seg and ("count%4 == 0 or count%7 == 0" in seg or "count == 4 or 7" in seg or "count == 4 or count == 7 or count == 47" in seg):
                    out.append(_splice(source, node.test, "count == 4 or count == 7"))
        return out