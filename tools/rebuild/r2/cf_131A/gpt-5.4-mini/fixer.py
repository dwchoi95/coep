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


def _is_input_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "input"
    )


def _replace_expr(source, old_node, new_text):
    return _splice(source, old_node, new_text)


def _fix_conditions(source, keep_original_on_else=False):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out = []
    seen = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test

        # pattern: if <name>.isupper() or <name>[1:].isupper():
        if (
            isinstance(test, ast.BoolOp)
            and isinstance(test.op, ast.Or)
            and len(test.values) == 2
        ):
            a, b = test.values
            # if word.isupper() or word[1:].isupper()
            if (
                isinstance(a, ast.Call)
                and isinstance(a.func, ast.Attribute)
                and a.func.attr == "isupper"
                and isinstance(b, ast.Call)
                and isinstance(b.func, ast.Attribute)
                and b.func.attr == "isupper"
                and isinstance(b.func.value, ast.Subscript)
            ):
                left_src = source[_span(source, a)[0]:_span(source, a)[1]]
                sub = b.func.value
                sub_src = source[_span(source, sub)[0]:_span(source, sub)[1]]
                new_test = f"{left_src} or len({sub_src}) == 1 or ({sub_src}[0].islower() and {sub_src}[1:].isupper())"
                new_src = _splice(source, test, new_test)
                if new_src not in seen:
                    seen.add(new_src)
                    out.append(new_src)

            # if len(n)==1 and n.isupper():  -> len(n)==1 and n.islower()
            if (
                isinstance(a, ast.BoolOp)
                and isinstance(a.op, ast.And)
                and len(a.values) == 2
                and isinstance(a.values[0], ast.Compare)
                and isinstance(a.values[1], ast.Call)
                and isinstance(a.values[1].func, ast.Attribute)
                and a.values[1].func.attr == "isupper"
            ):
                cmp = a.values[0]
                if (
                    len(cmp.ops) == 1
                    and isinstance(cmp.ops[0], ast.Eq)
                    and isinstance(cmp.left, ast.Call)
                    and isinstance(cmp.left.func, ast.Name)
                    and cmp.left.func.id == "len"
                    and len(cmp.left.args) == 1
                ):
                    name_src = source[_span(source, cmp.left.args[0])[0]:_span(source, cmp.left.args[0])[1]]
                    new_if = source[_span(source, test)[0]:_span(source, test)[1]].replace(
                        ".isupper()", ".islower()", 1
                    )
                    out.append(_splice(source, test, new_if))

        # if x.isupper() or (x[0].isupper() and x[1:].islower()) -> toggle / relax
        if (
            isinstance(test, ast.BoolOp)
            and isinstance(test.op, ast.Or)
            and len(test.values) == 2
        ):
            a, b = test.values
            if (
                isinstance(a, ast.Call)
                and isinstance(a.func, ast.Attribute)
                and a.func.attr == "isupper"
                and isinstance(b, ast.BoolOp)
                and isinstance(b.op, ast.And)
                and len(b.values) == 2
            ):
                # replace nested .islower() with .isupper() when needed
                btxt = source[_span(source, b)[0]:_span(source, b)[1]]
                if ".islower()" in btxt:
                    out.append(_splice(source, b, btxt.replace(".islower()", ".isupper()")))
                if ".lower()" in btxt and ".upper()" not in btxt:
                    out.append(_splice(source, b, btxt.replace(".lower()", ".upper()")))
                # special case: if body prints x itself / else prints x.upper()/title
                if ".title()" in source and ".swapcase()" not in source:
                    out.append(source.replace(".title()", ".swapcase()"))

        # if len(s)==1 and s.isupper(): print(s.lower()) -> len(s)==1 and s.islower()
        if (
            isinstance(test, ast.BoolOp)
            and isinstance(test.op, ast.And)
            and len(test.values) == 2
            and isinstance(test.values[0], ast.Compare)
            and isinstance(test.values[1], ast.Call)
            and isinstance(test.values[1].func, ast.Attribute)
            and test.values[1].func.attr == "isupper"
        ):
            out.append(_splice(source, test.values[1], source[_span(source, test.values[1])[0]:_span(source, test.values[1])[1]].replace("isupper", "islower")))

        # if a.lower() or a[1:].upper(): -> should use equality / truthiness of isupper
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
            txt = source[_span(source, test)[0]:_span(source, test)[1]]
            if ".lower()" in txt and ".upper()" in txt and "or" in txt:
                new = txt.replace(".lower()", ".upper() == ", 1)
                out.append(_splice(source, test, new))

    return out


def _fix_swapcase_conditions(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
            if ".islower()" in txt and ".isupper()" in txt and ".swapcase()" in source:
                out.append(source.replace(".islower()", ".isupper()"))
            if "s.lower()" in source and "if a==a.lower()" in source:
                out.append(source.replace("a.lower()", "a[1:]"))
    return out


def _generic_swapcase_to_conditional(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print" and len(call.args) == 1:
                arg = call.args[0]
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "swapcase":
                    # print(x.swapcase()) -> conditional around it if the source has an if on isupper / slice
                    out.append(source.replace("print(", "print(", 1))
        if isinstance(node, ast.Assign):
            txt = source[_span(source, node)[0]:_span(source, node)[1]]
            if ".capitalize()" in txt and ".swapcase()" not in txt:
                out.append(source.replace(".capitalize()", ".swapcase()"))
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="or_with_slice_isupper_to_capslock_rule",
                apply=self._rule_or_with_slice_isupper,
                symptoms=("wrong",),
            ),
            Rule(
                name="len1_upper_should_toggle_and_single_char_guard",
                apply=self._rule_len1_upper_singlechar,
                symptoms=("wrong",),
            ),
            Rule(
                name="string_upper_check_must_be_isupper_not_truthy",
                apply=self._rule_truthy_upper_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalization_should_be_swapcase_in_capslock_branch",
                apply=self._rule_capitalize_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_missing_assignment_or_dead_call",
                apply=self._rule_dead_capitalize_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="single_char_upper_lower_swap",
                apply=self._rule_single_char_upper_lower,
                symptoms=("wrong",),
            ),
            Rule(
                name="slice_lower_branch_to_slice_upper_branch",
                apply=self._rule_slice_lower_to_upper,
                symptoms=("wrong",),
            ),
            Rule(
                name="generic_capslock_if_uses_swapcase_or_title_wrongly",
                apply=self._rule_generic_patterns,
                symptoms=("wrong",),
            ),
        ]

    def _rule_or_with_slice_isupper(self, source):
        out = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if "isupper()" in txt and "[1:]" in txt and "or" in txt:
                    new = txt.replace("[1:].isupper()", "[1:].isupper() or len(" + txt.split(".")[0] + ") == 1")
                    if new != txt:
                        out.append(_splice(source, node.test, new))
        return out

    def _rule_len1_upper_singlechar(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if "len(" in txt and "isupper()" in txt and "and" in txt:
                    out.append(_splice(source, node.test, txt.replace("isupper()", "islower()")))
        return out

    def _rule_truthy_upper_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if ".upper()" in txt and "or" in txt and ".isupper" not in txt:
                    out.append(_splice(source, node.test, txt.replace(".lower() or", ".upper() ==")))
                if ".isupper" in txt and "()" not in txt:
                    out.append(_splice(source, node.test, txt.replace(".isupper", ".isupper()")))
        return out

    def _rule_capitalize_to_swapcase(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "capitalize":
                    out.append(_splice(source, node.func, source[_span(source, node.func)[0]:_span(source, node.func)[1]].replace("capitalize", "swapcase")))
                if node.func.attr == "title":
                    out.append(_splice(source, node.func, source[_span(source, node.func)[0]:_span(source, node.func)[1]].replace("title", "swapcase")))
        return out

    def _rule_dead_capitalize_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                txt = source[_span(source, node)[0]:_span(source, node)[1]]
                if ".capitalize()" in txt and "print" not in txt:
                    out.append(_splice(source, node.value.func, source[_span(source, node.value.func)[0]:_span(source, node.value.func)[1]].replace("capitalize", "swapcase")))
        return out

    def _rule_single_char_upper_lower(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if "len(" in txt and "== 1" in txt and "isupper()" in txt:
                    out.append(_splice(source, node.test, txt.replace("isupper()", "islower()")))
        return out

    def _rule_slice_lower_to_upper(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if ".islower()" in txt and "[1:]" in txt:
                    out.append(_splice(source, node.test, txt.replace(".islower()", ".isupper()")))
        return out

    def _rule_generic_patterns(self, source):
        out = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = source[_span(source, node.test)[0]:_span(source, node.test)[1]]
                if "s.lower()" in txt and "s.capitalize" in source:
                    out.append(source.replace(".capitalize()", ".swapcase()"))
                if "isupper" in txt and "isupper()" not in txt:
                    out.append(source.replace(".isupper", ".isupper()"))
                if ".title()" in txt:
                    out.append(source.replace(".title()", ".swapcase()"))
        return out