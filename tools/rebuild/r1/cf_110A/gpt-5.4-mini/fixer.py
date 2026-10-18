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
        return _splice(source, target, new_text)
    except Exception:
        return None


def _find_all(tree, kind):
    return [n for n in ast.walk(tree) if isinstance(n, kind)]


class Fixer:
    def rules(self):
        return [
            Rule(
                name="count_lucky_digits_instead_of_requiring_all_digits",
                symptoms=("wrong",),
                apply=self._fix_all_digits_to_count,
            ),
            Rule(
                name="compare_count_against_lucky_number",
                symptoms=("wrong",),
                apply=self._fix_count_to_lucky_check,
            ),
            Rule(
                name="fix_lucky_digit_literal_comparisons",
                symptoms=("wrong",),
                apply=self._fix_int_digit_comparisons,
            ),
            Rule(
                name="fix_count_literal_mistakes",
                symptoms=("wrong",),
                apply=self._fix_count_literal_mistakes,
            ),
            Rule(
                name="fix_digit_variable_used_instead_of_remainder",
                symptoms=("wrong",),
                apply=self._fix_wrong_digit_variable,
            ),
            Rule(
                name="fix_or_then_count_check",
                symptoms=("wrong",),
                apply=self._fix_modulo_lucky_check,
            ),
            Rule(
                name="fix_assignment_operator_in_count",
                symptoms=("wrong",),
                apply=self._fix_assignment_operator,
            ),
            Rule(
                name="fix_input_counting_over_length",
                symptoms=("wrong",),
                apply=self._fix_length_based_solution,
            ),
            Rule(
                name="fix_count_digits_method_misuse",
                symptoms=("wrong",),
                apply=self._fix_count_method_misuse,
            ),
            Rule(
                name="fix_printed_yes_no_casing",
                symptoms=("wrong",),
                apply=self._fix_print_casing,
            ),
            Rule(
                name="fix_input_parse_and_digit_loop",
                symptoms=("wrong",),
                apply=self._fix_input_parse_digit_loop,
            ),
            Rule(
                name="fix_boolean_condition_always_true",
                symptoms=("wrong",),
                apply=self._fix_always_true_conditions,
            ),
        ]

    def _fix_all_digits_to_count(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Return):
            if isinstance(node.value, ast.Compare) and len(node.value.ops) == 1:
                cmp = node.value
                if isinstance(cmp.ops[0], (ast.Eq, ast.NotEq)):
                    txt = source[_span(source, cmp.left)[0]:_span(source, cmp.left)[1]]
                    if txt.strip().startswith("len(") or txt.strip().startswith("all("):
                        continue
        for node in _find_all(tree, ast.Compare):
            if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                if ("len(" in left or "len(" in right) and ("count" in left or "count" in right):
                    continue
        return out

    def _fix_count_to_lucky_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.In)):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if "count" in txt or "len(" in txt or "% 4" in txt or "% 7" in txt:
                    continue
        for node in _find_all(tree, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                left = source[_span(source, test.left)[0]:_span(source, test.left)[1]]
                right = source[_span(source, test.comparators[0])[0]:_span(source, test.comparators[0])[1]]
                if left.strip() in {"count", "c", "s", "sum", "ans", "res", "cnt", "k", "x", "y", "z"}:
                    new = f"{left} in (4, 7)"
                    out.append(_replace_node(source, test, new))
        return [x for x in out if x and x != source]

    def _fix_int_digit_comparisons(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            if len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
                l = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                r = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                if (l.strip() in {"i", "char", "digit", "d", "r", "a", "x", "y", "z", "w"} and r.strip() in {"4", "7"}) or (
                    r.strip() in {"i", "char", "digit", "d", "r", "a", "x", "y", "z", "w"} and l.strip() in {"4", "7"}
                ):
                    new = f"{l} == '4' or {l} == '7'" if l.strip() in {"i", "char", "digit", "d", "r", "a", "x", "y", "z", "w"} else f"{r} == '4' or {r} == '7'"
                    out.append(_replace_node(source, node, new))
        return [x for x in out if x and x != source]

    def _fix_count_literal_mistakes(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "count" in txt and "==" in txt and ("4 or" in txt or "7 or" in txt or "or 7" in txt):
                continue
        return out

    def _fix_wrong_digit_variable(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.If):
            test = node.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
                left = source[_span(source, test.left)[0]:_span(source, test.left)[1]]
                if left.strip() == "n":
                    new = f"a == 4 or a == 7"
                    out.append(_replace_node(source, test, new))
        return [x for x in out if x and x != source]

    def _fix_modulo_lucky_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "% 4" in txt or "% 7" in txt:
                continue
            if isinstance(node.ops[0], ast.Eq):
                left = source[_span(source, node.left)[0]:_span(source, node.left)[1]]
                right = source[_span(source, node.comparators[0])[0]:_span(source, node.comparators[0])[1]]
                if left.strip() in {"c", "count", "ans", "sum", "s", "k", "res"} and right.strip() in {"4", "7"}:
                    new = f"{left} == 4 or {left} == 7"
                    out.append(_replace_node(source, node, new))
        return [x for x in out if x and x != source]

    def _fix_assignment_operator(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.AugAssign):
            if isinstance(node.op, ast.Add):
                target = source[_span(source, node.target)[0]:_span(source, node.target)[1]]
                if target.strip() in {"count", "c", "ans", "sum", "s", "k", "res", "b", "cnt"}:
                    continue
        return out

    def _fix_length_based_solution(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "len(" in txt and ("== 4" in txt or "== 7" in txt or "%4" in txt or "%7" in txt):
                continue
        return out

    def _fix_count_method_misuse(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "count" and len(node.args) == 1:
                arg = source[_span(source, node.args[0])[0]:_span(source, node.args[0])[1]]
                if arg.strip() == '"4"' and "count(\"7\")" not in source:
                    s, e = _span(source, node.args[0])
                    out.append(source[:s] + '"7"' + source[e:])
        return [x for x in out if x and x != source]

    def _fix_print_casing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Constant):
            if isinstance(node.value, str) and node.value in {"Yes", "No", "yes", "no", "si", "no"}:
                repl = "YES" if node.value.lower() == "yes" else "NO"
                out.append(_replace_node(source, node, repr(repl)))
        return [x for x in out if x and x != source]

    def _fix_input_parse_digit_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.For):
            if isinstance(node.iter, ast.Name):
                body = source[_span(source, node)[0]:_span(source, node)[1]]
                if "isdigit()" in body:
                    continue
                if "for" in body and "count" in body and "isdigit" in body:
                    continue
        return out

    def _fix_always_true_conditions(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in _find_all(tree, ast.Compare):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "(4 or 7)" in txt:
                new = txt.replace("(4 or 7)", "4").replace("(4 or 7)", "4")
                out.append(_replace_node(source, node, new))
            if "== 4 or" in txt and "==" in txt and "count" not in txt:
                pass
        for node in _find_all(tree, ast.BoolOp):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if "or" in txt and "'4' in" in txt and "'7' in" in txt and "and" in txt:
                continue
        return [x for x in out if x and x != source]