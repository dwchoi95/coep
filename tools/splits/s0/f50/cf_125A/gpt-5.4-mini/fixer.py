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
    return _splice(source, target, new_text)


def _replace_expr(source, old, new_src):
    return _splice(source, old, new_src)


class Fixer:
    def rules(self):
        return [
            Rule(
                name="off_by_one_add_one_before_div3",
                symptoms=("wrong",),
                apply=self._add_one_before_div3,
            ),
            Rule(
                name="cast_inexact_in_print",
                symptoms=("wrong",),
                apply=self._cast_printed_divisions,
            ),
            Rule(
                name="use_rounded_feet_from_cm_not_truncated",
                symptoms=("wrong",),
                apply=self._feet_from_rounded_inches,
            ),
            Rule(
                name="fix_truncated_feet_when_remainder_present",
                symptoms=("wrong",),
                apply=self._feet_from_n_plus_one_over_36,
            ),
            Rule(
                name="fix_wrong_modulus_26_to_36",
                symptoms=("wrong",),
                apply=self._mod26_to_mod36,
            ),
            Rule(
                name="fix_inch_rounding_threshold",
                symptoms=("wrong",),
                apply=self._round_half_up_for_remainder_two,
            ),
            Rule(
                name="replace_ceil_on_fractional_inches_with_integer_rounding",
                symptoms=("wrong",),
                apply=self._ceil_fractional_inches,
            ),
            Rule(
                name="fix_feet_inches_order_after_rounded_inches",
                symptoms=("wrong",),
                apply=self._split_rounded_inches_into_feet_inches,
            ),
            Rule(
                name="fix_output_of_raw_centimeters_as_inches",
                symptoms=("wrong",),
                apply=self._convert_cm_to_inches_before_printing,
            ),
            Rule(
                name="comparison_flip_lt_to_le",
                symptoms=("wrong",),
                apply=self._lt_to_le,
            ),
            Rule(
                name="comparison_flip_gt_to_ge",
                symptoms=("wrong",),
                apply=self._gt_to_ge,
            ),
        ]

    def _add_one_before_div3(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv) and isinstance(node.right, ast.Constant) and node.right.value == 3:
                left = node.left
                new = f"({ast.get_source_segment(source, left)})+1" if not isinstance(left, ast.Constant) else f"{ast.get_source_segment(source, left)}+1"
                out.append(_splice(source, node, f"({new})//3"))
        return out

    def _cast_printed_divisions(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                args = []
                changed = False
                for a in node.args:
                    if isinstance(a, ast.BinOp) and isinstance(a.op, ast.FloorDiv):
                        seg = ast.get_source_segment(source, a)
                        args.append(f"int({seg})")
                        changed = True
                    else:
                        args.append(ast.get_source_segment(source, a))
                if changed:
                    out.append(_splice(source, node, "print(" + ", ".join(args) + ")"))
        return out

    def _feet_from_rounded_inches(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                tgt = node.targets[0]
                if isinstance(tgt, ast.Name) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
                    right = node.value.right
                    if isinstance(right, ast.Constant) and right.value == 36:
                        left_src = ast.get_source_segment(source, node.value.left)
                        out.append(_splice(source, node.value, f"round({left_src}/3)"))
        return out

    def _feet_from_n_plus_one_over_36(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.FloorDiv):
                if isinstance(node.right, ast.Constant) and node.right.value == 36:
                    out.append(_splice(source, node, f"({ast.get_source_segment(source, node.left)}+1)//36"))
        return out

    def _mod26_to_mod36(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.right, ast.Constant) and node.right.value == 26:
                out.append(_splice(source, node, f"{ast.get_source_segment(source, node.left)}%36"))
        return out

    def _round_half_up_for_remainder_two(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
                    if isinstance(test.ops[0], ast.Lt):
                        left = ast.get_source_segment(source, test.left)
                        right = ast.get_source_segment(source, test.comparators[0])
                        if right == "0.5":
                            out.append(_splice(source, test, f"{left}%1<=0.5"))
        return out

    def _ceil_fractional_inches(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "ceil" and len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Div):
                        out.append(_splice(source, node, f"(({ast.get_source_segment(source, arg.left)})+2)//3"))
        return out

    def _split_rounded_inches_into_feet_inches(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                tgt = node.targets[0]
                if isinstance(tgt, ast.Name) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.FloorDiv):
                    if isinstance(node.value.right, ast.Constant) and node.value.right.value == 3:
                        out.append(_splice(source, node.value, f"{ast.get_source_segment(source, node.value.left)}//3"))
        return out

    def _convert_cm_to_inches_before_printing(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                args = [ast.get_source_segment(source, a) for a in node.args]
                if len(args) == 2 and any(a.isidentifier() for a in args):
                    out.append(_splice(source, node, f"print({args[0]}//12, {args[1]}%12)"))
        return out

    def _lt_to_le(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Lt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " <= " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out

    def _gt_to_ge(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Gt):
                left, right = node.left, node.comparators[0]
                ls, le = _span(source, left)
                rs, re = _span(source, right)
                new_cmp = source[ls:le] + " >= " + source[rs:re]
                out.append(_splice(source, node, new_cmp))
        return out