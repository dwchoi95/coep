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


def _count_lucky_digits_expr(expr):
    return f"sum(1 for _ch in ({expr}) if _ch == '4' or _ch == '7')"


def _replace_compare_op(node, source, new_op_text):
    left = node.left
    right = node.comparators[0]
    ls, le = _span(source, left)
    rs, re = _span(source, right)
    return source[:ls] + source[ls:le] + f" {new_op_text} " + source[rs:re] + source[_span(source, node)[1]:]


def _is_input_call(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input"


def _is_str_count_call(node, ch):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "count"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == ch
    )


class Fixer:
    def rules(self):
        return [
            Rule(name="count_lucky_digits_not_all_digits", apply=self._count_lucky_digits_not_all_digits, symptoms=("wrong",)),
            Rule(name="replace_len_with_lucky_digit_count", apply=self._replace_len_with_lucky_digit_count, symptoms=("wrong",)),
            Rule(name="fix_wrong_count7_operand", apply=self._fix_wrong_count7_operand, symptoms=("wrong",)),
            Rule(name="fix_count_compare_to_lucky_number", apply=self._fix_count_compare_to_lucky_number, symptoms=("wrong",)),
            Rule(name="fix_count_modulo_lucky_check", apply=self._fix_count_modulo_lucky_check, symptoms=("wrong",)),
            Rule(name="fix_non_lucky_digit_break", apply=self._fix_non_lucky_digit_break, symptoms=("wrong",)),
            Rule(name="fix_assignment_operators_and_string_outputs", apply=self._fix_assignment_operators_and_string_outputs, symptoms=("wrong",)),
            Rule(name="fix_digit_int_comparisons", apply=self._fix_digit_int_comparisons, symptoms=("wrong",)),
            Rule(name="fix_off_by_one_range", apply=self._fix_off_by_one_range, symptoms=("wrong",)),
            Rule(name="fix_always_true_or_false_digit_tests", apply=self._fix_always_true_or_false_digit_tests, symptoms=("wrong",)),
        ]

    def _count_lucky_digits_not_all_digits(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add):
                    l = node.left.left
                    r = node.left.right
                    if _is_input_call(l) and _is_input_call(r):
                        continue
            if isinstance(node, ast.If):
                txt = ast.get_source_segment(source, node.test) or ""
                if "count" in txt and ("== 4" in txt or "== 7" in txt or "in (4, 7)" in txt or "in {4, 7}" in txt):
                    continue
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_src = ast.get_source_segment(source, node.test)
                if not test_src:
                    continue
                if "count" in test_src or "len(" in test_src:
                    # Replace obvious "all digits lucky" style checks with lucky-count check.
                    if any(k in test_src for k in ("len(", "all(", "not in", "== len(", "==len(")):
                        new_test = f"({ _count_lucky_digits_expr('n') } == 4 or { _count_lucky_digits_expr('n') } == 7)"
                        try:
                            target = node.test
                            out.append(_splice(source, target, new_test))
                        except Exception:
                            pass
        return list(dict.fromkeys(out))

    def _replace_len_with_lucky_digit_count(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "len(" in txt and ("== 4" in txt or "== 7" in txt):
                    left_src = ast.get_source_segment(source, node.left)
                    if left_src:
                        new_text = f"({_count_lucky_digits_expr(left_src)} == 4 or {_count_lucky_digits_expr(left_src)} == 7)"
                        out.append(_splice(source, node, new_text))
        return list(dict.fromkeys(out))

    def _fix_wrong_count7_operand(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Name) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
                    if node.value.func.attr == "count" and len(node.value.args) == 1:
                        arg = node.value.args[0]
                        if isinstance(arg, ast.Constant) and arg.value == "4":
                            new_text = ast.get_source_segment(source, node).replace('.count("4")', '.count("7")').replace(".count('4')", ".count('7')")
                            if new_text != ast.get_source_segment(source, node):
                                out.append(_splice(source, node, new_text))
        return list(dict.fromkeys(out))

    def _fix_count_compare_to_lucky_number(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and any(p in txt for p in ("count == len(", "count==len(", "sum == len(", "sum==len(")):
                    left = ast.get_source_segment(source, node.left)
                    if left:
                        new = f"({left} == 4 or {left} == 7)"
                        out.append(_splice(source, node, new))
                if txt and "== (4 or 7)" in txt:
                    new = txt.replace("== (4 or 7)", "in (4, 7)")
                    out.append(_splice(source, node, new))
        return list(dict.fromkeys(out))

    def _fix_count_modulo_lucky_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and ("% 4 == 0" in txt or "% 7 == 0" in txt or "count%4==0" in txt or "count%7==0" in txt):
                    left = ast.get_source_segment(source, node.left)
                    if left:
                        out.append(_splice(source, node, f"({left} == 4 or {left} == 7)"))
        return list(dict.fromkeys(out))

    def _fix_non_lucky_digit_break(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                parent = None
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = ast.get_source_segment(source, node.test) or ""
                if "else:" in (ast.get_source_segment(source, node) or "") and "break" in (ast.get_source_segment(source, node) or ""):
                    if "!=" in test and ("'4'" in test or "'7'" in test or '"4"' in test or '"7"' in test):
                        seg = ast.get_source_segment(source, node)
                        if seg:
                            out.append(seg.replace("else:\n        break", "else:\n        continue"))
        return list(dict.fromkeys(out))

    def _fix_assignment_operators_and_string_outputs(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
                seg = ast.get_source_segment(source, node)
                if seg and "count =+ 1" in seg:
                    out.append(_splice(source, node, seg.replace("=+ 1", "+= 1")))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in ("Yes", "No", "yes", "no", "si", "Si", "NO ", " YES"):
                    out.append(_splice(source, node, repr(node.value.upper() if node.value.lower() in ("yes", "no") else node.value)))
        return list(dict.fromkeys(out))

    def _fix_digit_int_comparisons(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                txt = ast.get_source_segment(source, node)
                if txt and ("== 4" in txt or "== 7" in txt) and ("n[i]" in txt or "i" in txt or "digit" in txt):
                    new = txt.replace("== 4", "== '4'").replace("== 7", "== '7'")
                    out.append(_splice(source, node, new))
                if txt and ("!= 4" in txt or "!= 7" in txt):
                    new = txt.replace("!= 4", "!= '4'").replace("!= 7", "!= '7'")
                    out.append(_splice(source, node, new))
        return list(dict.fromkeys(out))

    def _fix_off_by_one_range(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range" and len(node.args) == 2:
                txt = ast.get_source_segment(source, node)
                if txt and "-1" in txt:
                    out.append(_splice(source, node, txt.replace("-1", "")))
        return list(dict.fromkeys(out))

    def _fix_always_true_or_false_digit_tests(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                txt = ast.get_source_segment(source, node)
                if txt and ("!= '4' or" in txt or "!= '7' or" in txt or '!=4 or' in txt or '!=7 or' in txt):
                    parts = txt.replace(" or ", " and ")
                    out.append(_splice(source, node, parts))
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
                txt = ast.get_source_segment(source, node)
                if txt and ("== '4' and" in txt or "== '7' and" in txt or '==4 and' in txt or '==7 and' in txt):
                    parts = txt.replace(" and ", " or ")
                    out.append(_splice(source, node, parts))
        return list(dict.fromkeys(out))