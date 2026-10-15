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


def _replace_node(source, old, new):
    return _splice(source, old, new)


class Fixer:
    def rules(self):
        return [
            Rule(name="return_len_after_scan", apply=self._return_len_after_scan, symptoms=("wrong",)),
            Rule(name="break_then_return_loop_var", apply=self._break_then_return_loop_var, symptoms=("wrong",)),
            Rule(name="premature_else_return", apply=self._premature_else_return, symptoms=("wrong",)),
            Rule(name="strict_gt_should_be_ge_in_scan", apply=self._strict_gt_should_be_ge_in_scan, symptoms=("wrong",)),
            Rule(name="scan_until_first_ge", apply=self._scan_until_first_ge, symptoms=("wrong",)),
            Rule(name="enumerate_sorted_index", apply=self._enumerate_sorted_index, symptoms=("wrong",)),
            Rule(name="off_by_one_return_i_plus_1", apply=self._off_by_one_return_i_plus_1, symptoms=("wrong",)),
            Rule(name="wrong_loop_bound_len_plus_one", apply=self._wrong_loop_bound_len_plus_one, symptoms=("wrong", "err:IndexError")),
            Rule(name="replace_seq_index_with_counter", apply=self._replace_seq_index_with_counter, symptoms=("wrong",)),
            Rule(name="fix_none_false_empty_returns", apply=self._fix_none_false_empty_returns, symptoms=("wrong",)),
            Rule(name="fix_tuple_or_empty_check", apply=self._fix_tuple_or_empty_check, symptoms=("wrong",)),
            Rule(name="fix_len_seq_call", apply=self._fix_len_seq_call, symptoms=("wrong", "err:TypeError")),
            Rule(name="fix_assignment_vs_equality_counter", apply=self._fix_assignment_vs_equality_counter, symptoms=("err:NameError", "wrong")),
            Rule(name="fix_insert_returning_sequence", apply=self._fix_insert_returning_sequence, symptoms=("wrong",)),
            Rule(name="fix_break_return_insertion_scan", apply=self._fix_break_return_insertion_scan, symptoms=("wrong",)),
            Rule(name="fix_param_shadowing_in_loop", apply=self._fix_param_shadowing_in_loop, symptoms=("wrong",)),
            Rule(name="fix_search2_name", apply=self._fix_search2_name, symptoms=("wrong",)),
            Rule(name="fix_return_operator_gt_to_lt", apply=self._fix_return_operator_gt_to_lt, symptoms=("wrong",)),
            Rule(name="fix_max_min_boundary_only", apply=self._fix_max_min_boundary_only, symptoms=("wrong",)),
            Rule(name="fix_none_return_to_zero", apply=self._fix_none_return_to_zero, symptoms=("wrong",)),
        ]

    def _return_len_after_scan(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for st in node.body:
                    if isinstance(st, ast.For) and len(st.body) == 1 and isinstance(st.body[0], ast.If):
                        if st.orelse == [] and isinstance(st.body[0].body[0], ast.Return):
                            ret = st.body[0].body[0]
                            if isinstance(ret.value, ast.Name) and ret.value.id in {"i", "counter", "pos", "result", "indx"}:
                                end = node.body[-1]
                                if isinstance(end, ast.Return) and isinstance(end.value, ast.BinOp) and isinstance(end.value.op, ast.Add):
                                    if isinstance(end.value.left, ast.Name) and end.value.left.id == ret.value.id:
                                        out.append(_replace_node(source, end, f"return len(seq)"))
        return out

    def _break_then_return_loop_var(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and len(node.body) == 1:
                st = node.body[0]
                if isinstance(st, ast.If) and len(st.body) == 1 and isinstance(st.body[0], ast.Break):
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.FunctionDef) and node in parent.body:
                            idx = parent.body.index(node)
                            if idx + 1 < len(parent.body) and isinstance(parent.body[idx + 1], ast.Return):
                                out.append(_replace_node(source, parent.body[idx + 1], "return len(seq)"))
        return out

    def _premature_else_return(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and node.orelse:
                if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
                    if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return):
                        out.append(_replace_node(source, node.orelse[0], "continue"))
        return out

    def _strict_gt_should_be_ge_in_scan(self, source):
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
                out.append(_replace_node(source, node, source[ls:le] + " >= " + source[rs:re]))
        return out

    def _scan_until_first_ge(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if len(node.body) == 1 and isinstance(node.body[0], ast.If):
                    ifs = node.body[0]
                    if len(ifs.body) == 1 and isinstance(ifs.body[0], ast.Return):
                        cond = ifs.test
                        if isinstance(cond, ast.Compare) and len(cond.ops) == 1 and isinstance(cond.ops[0], ast.Lt):
                            left, right = cond.left, cond.comparators[0]
                            ls, le = _span(source, left)
                            rs, re = _span(source, right)
                            out.append(_replace_node(source, cond, source[ls:le] + " <= " + source[rs:re]))
        return out

    def _enumerate_sorted_index(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple):
                if len(node.target.elts) == 2 and isinstance(node.target.elts[0], ast.Name):
                    if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "enumerate":
                        new = "for i, elem in enumerate(seq):"
                        out.append(_replace_node(source, node, new))
        return out

    def _off_by_one_return_i_plus_1(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                if isinstance(node.value.left, ast.Name) and node.value.left.id in {"i", "counter", "pos", "indx"}:
                    if isinstance(node.value.right, ast.Constant) and node.value.right.value == 1:
                        out.append(_replace_node(source, node, f"return len(seq)"))
        return out

    def _wrong_loop_bound_len_plus_one(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                if node.iter.func.id == "range" and len(node.iter.args) == 1:
                    arg = node.iter.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                        if isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) and arg.left.func.id == "len":
                            out.append(_replace_node(source, arg, f"len(seq)"))
        return out

    def _replace_seq_index_with_counter(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.attr == "index":
                    out.append(_replace_node(source, call, "i"))
        return out

    def _fix_none_false_empty_returns(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value in {None, False, -1, ()}:
                out.append(_replace_node(source, node, "return 0"))
        return out

    def _fix_tuple_or_empty_check(self, source):
        if "seq == () or []" in source:
            return [source.replace("seq == () or []", "seq == () or seq == []")]
        if "if seq == () or []:" in source:
            return [source.replace("if seq == () or []:", "if seq == () or seq == []:")]
        return []

    def _fix_len_seq_call(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "seq":
                out.append(_replace_node(source, node.iter, "range(len(seq))"))
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "len":
                out.append(_replace_node(source, node.iter, "range(len(seq))"))
        return out

    def _fix_assignment_vs_equality_counter(self, source):
        if "count==0" in source:
            return [source.replace("count==0", "count=0")]
        return []

    def _fix_insert_returning_sequence(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "seq":
                out.append(_replace_node(source, node, "return len(seq)"))
        return out

    def _fix_break_return_insertion_scan(self, source):
        if "return i-1" in source:
            return [source.replace("return i-1", "return i")]
        return []

    def _fix_param_shadowing_in_loop(self, source):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out = []
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == "x":
                out.append(_replace_node(source, node.target, "ele"))
        return out

    def _fix_search2_name(self, source):
        if "def search2(" in source:
            return [source.replace("def search2(", "def search(")]
        return []

    def _fix_return_operator_gt_to_lt(self, source):
        if "if x>i:" in source:
            return [source.replace("if x>i:", "if x<=i:")]
        return []

    def _fix_max_min_boundary_only(self, source):
        if "x>=max(seq)" in source:
            return [source.replace("x>=max(seq)", "x>max(seq)")]
        if "x<=min(seq)" in source:
            return [source.replace("x<=min(seq)", "x<=seq[0]")]
        return []

    def _fix_none_return_to_zero(self, source):
        if "return None" in source:
            return [source.replace("return None", "return 0")]
        return []