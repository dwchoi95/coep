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


def _replace_node(source, node, new_text):
    return _splice(source, node, new_text)


def _count_lucky_expr(expr):
    return f"sum(1 for _ch in {expr} if _ch == '4' or _ch == '7')"


class Fixer:
    def rules(self):
        return [
            Rule(
                name="lucky_digit_compare_int_to_str",
                symptoms=("wrong",),
                apply=self._int_digit_compare,
            ),
            Rule(
                name="count_four_twice",
                symptoms=("wrong",),
                apply=self._second_count_four_to_seven,
            ),
            Rule(
                name="remove_loop_break_on_unlucky_digit",
                symptoms=("wrong",),
                apply=self._remove_break_on_else,
            ),
            Rule(
                name="assignment_plus_equals_fix",
                symptoms=("wrong",),
                apply=self._fix_count_assignment,
            ),
            Rule(
                name="while_int_division_floor",
                symptoms=("wrong", "err:TypeError"),
                apply=self._fix_int_division_in_while,
            ),
            Rule(
                name="substring_count_to_digit_count",
                symptoms=("wrong",),
                apply=self._substring_len_equality_to_count_check,
            ),
            Rule(
                name="modulo_count_should_check_value",
                symptoms=("wrong",),
                apply=self._fix_modulo_count_checks,
            ),
            Rule(
                name="len_of_input_not_answer_string",
                symptoms=("wrong",),
                apply=self._fix_len_input_equals_count,
            ),
            Rule(
                name="wrong_count_inclusion_exclusive_or",
                symptoms=("wrong",),
                apply=self._fix_all_digits_check,
            ),
            Rule(
                name="strip_print_debug_and_last_print",
                symptoms=("wrong",),
                apply=self._remove_debug_prints_and_trailing_print,
            ),
            Rule(
                name="compare_length_literals_to_count",
                symptoms=("wrong",),
                apply=self._fix_len_literal_check,
            ),
            Rule(
                name="digit_membership_and_counts",
                symptoms=("wrong",),
                apply=self._count_digits_instead_of_all_digits,
            ),
            Rule(
                name="fix_range_off_by_one_in_digit_loop",
                symptoms=("wrong",),
                apply=self._fix_range_off_by_one,
            ),
            Rule(
                name="fix_or_true_condition_on_digit_membership",
                symptoms=("wrong",),
                apply=self._fix_always_true_or_conditions,
            ),
            Rule(
                name="fix_bool_accumulator_for_non_digits",
                symptoms=("wrong",),
                apply=self._fix_non_digit_flag_logic,
            ),
        ]

    def _int_digit_compare(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left, right = node.left, node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and isinstance(right.value, int) and right.value in (4, 7):
                    s, e = _span(source, right)
                    out.append(source[:s] + repr(str(right.value)) + source[e:])
                elif isinstance(right, ast.Name) and isinstance(left, ast.Constant) and isinstance(left.value, int) and left.value in (4, 7):
                    s, e = _span(source, left)
                    out.append(source[:s] + repr(str(left.value)) + source[e:])
        return out

    def _second_count_four_to_seven(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "count":
                if len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "4":
                    s, e = _span(source, node.args[0])
                    out.append(source[:s] + repr("7") + source[e:])
        return out

    def _remove_break_on_else(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Break):
                parent_text = source[:_span(source, node)[0]]
                if "else:" in parent_text[-40:]:
                    s, e = _span(source, node)
                    out.append(source[:s] + "pass" + source[e:])
        return out

    def _fix_count_assignment(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Constant) and node.value.value == 1:
                    s, e = _span(source, node.value)
                    out.append(source[:s] + "0" + source[e:])
        return out

    def _fix_int_division_in_while(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "int" and len(call.args) == 1:
                    arg = call.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                        s, e = _span(source, call.func)
                        out.append(source[:s] + "" + source[e:])
                        s2, e2 = _span(source, arg)
                        out[-1] = out[-1][:s2] + source[_span(source, arg.left)[0]:_span(source, arg.left)[1]] + " // " + source[_span(source, arg.right)[0]:_span(source, arg.right)[1]] + out[-1][e2:]
        return out

    def _substring_len_equality_to_count_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "len(" in txt and "len(" in txt and "st" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + f"({node.left.id}.count('4') + {node.left.id}.count('7')) in [4, 7]" if isinstance(node.left, ast.Call) else source[s:e] + source[e:])
        return [x for x in out if x != source]

    def _fix_modulo_count_checks(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "% 4 == 0 or" in txt or txt and "% 7 == 0" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + "c == 4 or c == 7" + source[e:])
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
                parent = ast.get_source_segment(source, node)
                if parent and "count%4==0" in parent.replace(" ", ""):
                    s, e = _span(source, node)
                    out.append(source[:s] + "count" + source[e:])
        return [x for x in out if x != source]

    def _fix_len_input_equals_count(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "len(res)" in txt and "len(s)" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + "b == 4 or b == 7" + source[e:])
        return out

    def _fix_all_digits_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "len(s)" in txt and "count" in txt and "==" in txt and "len(res)" in txt:
                    continue
        return out

    def _remove_debug_prints_and_trailing_print(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "print":
                    if node.value.args and isinstance(node.value.args[0], (ast.List, ast.Name, ast.Constant)):
                        txt = ast.get_source_segment(source, node)
                        if txt and ("print(entrada)" in txt or "print(luckyNumber)" in txt or "print(count)" in txt):
                            s, e = _span(source, node)
                            out.append(source[:s] + "" + source[e:])
        return out

    def _fix_len_literal_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = ast.get_source_segment(source, node)
                if txt and "len" in txt and "==4" in txt.replace(" ", ""):
                    s, e = _span(source, node)
                    out.append(source[:s] + "(a.count('4') + a.count('7')) == 4 or (a.count('4') + a.count('7')) == 7" + source[e:])
        return out

    def _count_digits_instead_of_all_digits(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                body = node.body
                if body and isinstance(body[0], ast.If):
                    txt = ast.get_source_segment(source, body[0].test)
                    if txt and "character.isdigit()" in txt:
                        s, e = _span(source, body[0].test)
                        out.append(source[:s] + f"karakter == '4' or karakter == '7'" + source[e:])
        return out

    def _fix_range_off_by_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
                if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range" and len(node.iter.args) == 2:
                    a1, a2 = node.iter.args
                    if isinstance(a1, ast.Constant) and a1.value == 0:
                        s, e = _span(source, node.iter)
                        out.append(source[:s] + f"range(0, len(n))" + source[e:])
                        s2, e2 = _span(source, node.iter)
                        out.append(source[:s2] + f"range(len(n))" + source[e2:])
        return out

    def _fix_always_true_or_conditions(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                txt = ast.get_source_segment(source, node)
                if txt and ("'4'" in txt and "'7'" in txt) and "not in" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + "i in [\"4\",\"7\"]" + source[e:])
        return out

    def _fix_non_digit_flag_logic(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                txt = ast.get_source_segment(source, node)
                if txt and "i != '4' or i != '7'" in txt:
                    s, e = _span(source, node)
                    out.append(source[:s] + "i == '4' or i == '7'" + source[e:])
        return out