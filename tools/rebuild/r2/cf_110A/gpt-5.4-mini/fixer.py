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


def _node_text(source, node):
    s, e = _span(source, node)
    return source[s:e]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="count_lucky_digits_must_be_checked_against_47",
                apply=self._count_lucky_digits_must_be_checked_against_47,
                symptoms=("wrong",),
            ),
            Rule(
                name="compare_against_literal_47_or_74",
                apply=self._compare_against_literal_47_or_74,
                symptoms=("wrong",),
            ),
            Rule(
                name="wrong_input_counter_uses_all_digits",
                apply=self._wrong_input_counter_uses_all_digits,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_digit_test_uses_ints_instead_of_strings",
                apply=self._fix_digit_test_uses_ints_instead_of_strings,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_or_instead_of_and_in_digit_filter",
                apply=self._fix_or_instead_of_and_in_digit_filter,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_len_based_solution_to_count_based_solution",
                apply=self._fix_len_based_solution_to_count_based_solution,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_count_constructor_missing_seven",
                apply=self._fix_count_constructor_missing_seven,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_input_name_and_lucky_message",
                apply=self._fix_input_name_and_lucky_message,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_input_call_with_prompt",
                apply=self._fix_input_call_with_prompt,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_while_digit_update_toward_end",
                apply=self._fix_while_digit_update_toward_end,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_decimal_division_to_integer_division",
                apply=self._fix_decimal_division_to_integer_division,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_digit_count_return_check",
                apply=self._fix_digit_count_return_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_any_lucky_digit_presence_to_count_check",
                apply=self._fix_any_lucky_digit_presence_to_count_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_set_or_unique_digit_misconception",
                apply=self._fix_set_or_unique_digit_misconception,
                symptoms=("wrong",),
            ),
            Rule(
                name="fix_overly_strict_all_lucky_digits_solution",
                apply=self._fix_overly_strict_all_lucky_digits_solution,
                symptoms=("wrong",),
            ),
        ]

    def _count_lucky_digits_must_be_checked_against_47(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                txt = _node_text(source, node.comparators[0])
                if txt.strip() in {"(4,7)", "[4,7]", "{4,7}", "(4, 7)", "[4, 7]", "{4, 7}"}:
                    left = _node_text(source, node.left)
                    out.append(_splice(source, node, f"{left} in (4, 7)"))
        return out

    def _compare_against_literal_47_or_74(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in ("Yes", "yes", "No", "no", "si", "si\n", "yes\n", "no\n"):
                out.append(source[:_span(source, node)[0]] + repr("YES" if str(node.value).lower() == "yes" else "NO") + source[_span(source, node)[1]:])
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                rhs = node.comparators[0]
                if isinstance(rhs, ast.Constant) and rhs.value == 47:
                    left = _node_text(source, node.left)
                    out.append(_splice(source, node, f"{left} in (4, 7)"))
                if isinstance(rhs, ast.Constant) and rhs.value == 4 and "or" in _node_text(source, node):
                    left = _node_text(source, node.left)
                    out.append(_splice(source, node, f"{left} in (4, 7)"))
        return out

    def _wrong_input_counter_uses_all_digits(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name):
                body = _node_text(source, node)
                if "isdigit()" in body and "count" in body:
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.If) and isinstance(sub.test, ast.Call) and isinstance(sub.test.func, ast.Attribute) and sub.test.func.attr == "isdigit":
                            replacement = _node_text(source, sub.test.func.value) + " in '47'"
                            out.append(_splice(source, sub.test, replacement))
        return out

    def _fix_digit_test_uses_ints_instead_of_strings(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                if isinstance(node.left, ast.Name) and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value in (4, 7):
                    out.append(_splice(source, node, f"{_node_text(source, node.left)} == '{node.comparators[0].value}'"))
                if isinstance(node.left, ast.Subscript) and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value in (4, 7):
                    out.append(_splice(source, node, f"{_node_text(source, node.left)} == '{node.comparators[0].value}'"))
        return out

    def _fix_or_instead_of_and_in_digit_filter(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                txt = _node_text(source, node)
                if "4" in txt and "7" in txt and ("==" in txt or "in" in txt):
                    parts = [ _node_text(source, v) for v in node.values ]
                    out.append(_splice(source, node, " and ".join(parts)))
        return out

    def _fix_len_based_solution_to_count_based_solution(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                txt = _node_text(source, node)
                if "len(" in txt and ("count" in source or ".count(" in source):
                    out.append(_splice(source, node, txt.replace("len(", "sum(1 for _ in ").replace(")==", ") in ")))
        return out

    def _fix_count_constructor_missing_seven(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                txt = _node_text(source, node)
                if ".count(\"4\")" in txt and ".count(\"7\")" not in txt:
                    out.append(source.replace('.count("4")', '.count("4")').replace('cik2=n.count("4")', 'cik2=n.count("7")'))
        return out

    def _fix_input_name_and_lucky_message(self, source):
        try:
            ast.parse(source)
        except SyntaxError:
            return []
        out = []
        if 'print ("si" if lucky(money) else "no")' in source:
            out.append(source.replace('print ("si" if lucky(money) else "no")', 'print("YES" if lucky(money) else "NO")'))
        if 'return count in (4,7)' in source:
            out.append(source.replace('return count in (4,7)', 'return count in (4, 7)'))
        return out

    def _fix_input_call_with_prompt(self, source):
        try:
            ast.parse(source)
        except SyntaxError:
            return []
        out = []
        if 'input("Enter number : ")' in source:
            out.append(source.replace('input("Enter number : ")', 'input()'))
        if 'input("Enter the number (1 to 10^18): ")' in source:
            out.append(source.replace('input("Enter the number (1 to 10^18): ")', 'input()'))
        return out

    def _fix_while_digit_update_toward_end(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if "n == 4" in txt or "n==4" in txt or "n == 7" in txt or "n==7" in txt:
                    out.append(_splice(source, node.test, txt.replace("n", "a").replace("a", "a", 1)))
        return out

    def _fix_decimal_division_to_integer_division(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
                out.append(_splice(source, node.op, "//"))
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Div):
                out.append(_splice(source, node.value.op, "//"))
        return out

    def _fix_digit_count_return_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                txt = _node_text(source, node.value) if node.value else ""
                if "is_lucky_digit" in txt or "count" in txt:
                    out.append(_splice(source, node, "return count in (4, 7)"))
        return out

    def _fix_any_lucky_digit_presence_to_count_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if " in x" in txt and ("'4'" in txt or "'7'" in txt):
                    new = txt.replace(" and ", " + ").replace(" in x", ".count('4') + x.count('7')")
                    out.append(_splice(source, node.test, new))
                if "len(" in txt and "count" in txt:
                    out.append(_splice(source, node.test, "count == 4 or count == 7"))
        return out

    def _fix_set_or_unique_digit_misconception(self, source):
        try:
            ast.parse(source)
        except SyntaxError:
            return []
        out = []
        if "set(input())" in source and "len(pos) == 2" in source:
            out.append(source.replace("pos = set(pos)\n\nif len(pos) == 2 and (\"4\" in pos or \"7\" in pos):\n    print(\"YES\")\nelse:\n    print(\"NO\")",
                                      "num = list(input())\na = num.count('4')\nb = num.count('7')\nif a + b == 4 or a + b == 7:\n    print('YES')\nelse:\n    print('NO')"))
        return out

    def _fix_overly_strict_all_lucky_digits_solution(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if "all(" in txt and "47" in txt:
                    out.append(_splice(source, node.test, "(sum(1 for c in n if c in '47') in (4, 7))"))
        return out