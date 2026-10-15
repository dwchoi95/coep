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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _replace_name_in_comp(source, node, new_name):
    if isinstance(node, ast.Name):
        return source[_span(source, node)[0]:_span(source, node)[1]].replace(node.id, new_name, 1)
    return None


def _fix_misbound_identifier(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            left = node.left
            right = node.comparators[0]
            if isinstance(left, ast.Name) and left.id in {"day", "date"} and isinstance(right, ast.Name) and right.id in {"day", "date"}:
                if left.id != right.id:
                    ls, le = _span(source, left)
                    rs, re = _span(source, right)
                    new = source[:ls] + right.id + source[le:rs] + left.id + source[re:]
                    out.append(_splice(source, node, new[ls:_span(new, node)[1] if False else len(new)]))
    return out


def _replace_compare_op(source, old_op, new_op):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], old_op):
            ls, le = _span(source, node.left)
            rs, re = _span(source, node.comparators[0])
            new_cmp = source[ls:le] + f" {new_op} " + source[rs:re]
            out.append(_splice(source, node, new_cmp))
    return out


def _fix_day_identifier(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "day":
            continue
        if isinstance(node, ast.Name) and node.id == "date":
            parent = None
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="day_parameter_should_not_be_date",
                apply=self._day_param_to_day,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="day_variable_used_instead_of_parameter",
                apply=self._day_name_fix,
                symptoms=("wrong", "err:NameError"),
            ),
            Rule(
                name="unique_count_should_be_exactly_one",
                apply=self._count_to_exactly_one,
                symptoms=("wrong",),
            ),
            Rule(
                name="contains_unique_day_should_check_month_membership",
                apply=self._contains_unique_day_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="strict_gt_should_be_eq_for_uniqueness",
                apply=self._gt_to_eq_fix,
                symptoms=("wrong",),
            ),
            Rule(
                name="count_zero_before_return_false",
                apply=self._add_missing_false_for_nonunique,
                symptoms=("wrong",),
            ),
        ]

    def _day_param_to_day(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "unique_day"]:
            if fn.args.args and fn.args.args[0].arg != "day":
                arg = fn.args.args[0]
                out.append(_splice(source, arg, "day"))
        return out

    def _day_name_fix(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "day":
                out.append(source[:_span(source, node)[0]] + "date" + source[_span(source, node)[1]:])
                break
        return out

    def _count_to_exactly_one(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                if isinstance(node.ops[0], ast.LtE):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    new_cmp = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
                elif isinstance(node.ops[0], ast.Gt):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    new_cmp = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
        return out

    def _contains_unique_day_fix(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
            text = ast.get_source_segment(source, fn)
            if text and ("return True" in text or "return False" in text):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
                    ls, le = _span(source, node.left)
                    rs, re = _span(source, node.comparators[0])
                    new_cmp = source[ls:le] + " == " + source[rs:re]
                    out.append(_splice(source, node, new_cmp))
                    break
        return out

    def _gt_to_eq_fix(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                ls, le = _span(source, node.left)
                rs, re = _span(source, node.comparators[0])
                new_cmp = source[ls:le] + " == " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out

    def _add_missing_false_for_nonunique(self, source):
        tree = _safe_parse(source)
        if tree is None:
            return []
        out = []
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "contains_unique_day"]:
            text = ast.get_source_segment(source, fn)
            if text and "return False" not in text:
                end = _span(source, fn)[1]
                indent = " " * fn.col_offset
                out.append(source[:end] + f"\n{indent}return False" + source[end:])
        return out