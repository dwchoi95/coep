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


def _find_enclosing_stmt(tree, target):
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            for child in ast.iter_child_nodes(node):
                if child is target:
                    return node
    return None


def _replace_node_text(source, old, new_text):
    return _splice(source, old, new_text)


class Fixer:
    def rules(self):
        return [
            Rule(name="use_isupper_for_capslock_check", apply=self._use_isupper_for_capslock_check, symptoms=("wrong",)),
            Rule(name="add_missing_len_one_to_capslock_check", apply=self._add_missing_len_one_to_capslock_check, symptoms=("wrong",)),
            Rule(name="fix_first_char_or_logic", apply=self._fix_first_char_or_logic, symptoms=("wrong",)),
            Rule(name="replace_capitalize_title_with_swapcase", apply=self._replace_capitalize_title_with_swapcase, symptoms=("wrong",)),
            Rule(name="replace_canonicalized_output_with_original", apply=self._replace_canonicalized_output_with_original, symptoms=("wrong",)),
            Rule(name="fix_only_first_char_uppercase_output", apply=self._fix_only_first_char_uppercase_output, symptoms=("wrong",)),
            Rule(name="remove_unconditional_lower_then_capitalize", apply=self._remove_unconditional_lower_then_capitalize, symptoms=("wrong",)),
            Rule(name="fix_always_true_string_check", apply=self._fix_always_true_string_check, symptoms=("wrong",)),
            Rule(name="fix_wrong_isupper_return_branch", apply=self._fix_wrong_isupper_return_branch, symptoms=("wrong",)),
            Rule(name="generic_lt_to_le", apply=self._generic_lt_to_le, symptoms=("wrong",)),
            Rule(name="generic_gt_to_ge", apply=self._generic_gt_to_ge, symptoms=("wrong",)),
        ]

    def _use_isupper_for_capslock_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "upper" and not node.args and not node.keywords:
                parent = getattr(node, "parent", None)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "upper":
                if not node.args and not node.keywords:
                    txt = _node_text(source, node)
                    if txt.endswith(".upper()"):
                        out.append(_replace_node_text(source, node, txt[:-8] + ".isupper()"))
        return list(dict.fromkeys(out))

    def _add_missing_len_one_to_capslock_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                texts = [_node_text(source, v) for v in node.values]
                if any(t.replace(" ", "") == "word[1:].isupper()" or t.replace(" ", "") == "s[1:].isupper()" or t.replace(" ", "") == "n[1:].isupper()" for t in texts):
                    if not any(isinstance(v, ast.Compare) and _node_text(source, v).replace(" ", "") in {"len(word)==1", "len(s)==1", "len(n)==1", "len(a)==1"} for v in node.values):
                        new = _node_text(source, node)
                        for name in ("word", "s", "n", "a", "x", "text", "v"):
                            if f"{name}[1:].isupper()" in new and f"len({name}) == 1" not in new:
                                rep = f"len({name}) == 1 or "
                                idx = new.find(f"{name}[1:].isupper()")
                                new = new[:idx] + rep + new[idx:]
                                out.append(_replace_node_text(source, node, new))
                                break
        return list(dict.fromkeys(out))

    def _fix_first_char_or_logic(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                txt = _node_text(source, node)
                if ".lower()" in txt and ("[0].lower()" in txt or "[0].upper()" in txt) and ".upper()" in txt:
                    for v in node.values:
                        if isinstance(v, ast.Call):
                            vt = _node_text(source, v)
                            if vt.endswith(".lower()") or vt.endswith(".upper()"):
                                new = txt.replace(vt, "False")
                                out.append(_replace_node_text(source, node, new))
                                break
        return list(dict.fromkeys(out))

    def _replace_capitalize_title_with_swapcase(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("capitalize", "title"):
                txt = _node_text(source, node)
                if txt.endswith(".capitalize()") or txt.endswith(".title()"):
                    out.append(_replace_node_text(source, node, txt.rsplit(".", 1)[0] + ".swapcase()"))
        return list(dict.fromkeys(out))

    def _replace_canonicalized_output_with_original(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                tgt = node.targets[0].id
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                    txt = _node_text(source, node)
                    if f"{tgt} = {tgt}[0].upper()" in txt or f"{tgt} = {tgt}[0].upper() +" in txt or f"{tgt} = {tgt}[0].upper() + {tgt}[1:].lower()" in txt:
                        out.append(_replace_node_text(source, node, f"{tgt} = {tgt}"))
        return list(dict.fromkeys(out))

    def _fix_only_first_char_uppercase_output(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if ".isupper()" in txt and "word[0].isupper()" in txt:
                    new = txt.replace("word[0].isupper()", "word.isupper()")
                    out.append(_replace_node_text(source, node.test, new))
                if ".isupper()" in txt and "s[0].isupper()" in txt:
                    new = txt.replace("s[0].isupper()", "s.isupper()")
                    out.append(_replace_node_text(source, node.test, new))
                if ".isupper()" in txt and "x[0].isupper()" in txt:
                    new = txt.replace("x[0].isupper()", "x.isupper()")
                    out.append(_replace_node_text(source, node.test, new))
        return list(dict.fromkeys(out))

    def _remove_unconditional_lower_then_capitalize(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                txt = _node_text(source, node)
                if ".lower()" in txt and ".capitalize()" not in txt and ".upper()" not in txt and "input()" not in txt:
                    if any(isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "lower" for v in ast.walk(node.value)):
                        out.append(source.replace(txt, txt.split("=", 1)[0] + "= input()"))
        return list(dict.fromkeys(out))

    def _fix_always_true_string_check(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if ".lower()" in txt and "if" not in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace(".lower()", ".islower()")))
                if ".upper()" in txt and "if" not in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace(".upper()", ".isupper()")))
        return list(dict.fromkeys(out))

    def _fix_wrong_isupper_return_branch(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                txt = _node_text(source, node.test)
                if "len(word) == 1 and word.isupper()" in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace("word.isupper()", "word.islower()")))
                if "len(s) > 1 and s[1:].islower()" in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace("s[1:].islower()", "s[1:].isupper()")))
                if "word[1:].islower()" in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace("word[1:].islower()", "word[1:].isupper()")))
                if "word.islower() or" in txt:
                    out.append(_replace_node_text(source, node.test, txt.replace("word.islower() or ", "")))
        return list(dict.fromkeys(out))

    def _generic_lt_to_le(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
        return list(dict.fromkeys(out))

    def _generic_gt_to_ge(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " >= " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
        return list(dict.fromkeys(out))