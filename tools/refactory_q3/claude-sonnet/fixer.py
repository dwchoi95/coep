import ast
import difflib
import builtins as _builtins_mod

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


def _text(source, node):
    s, e = _span(source, node)
    return source[s:e]


MUTATORS_NORETURN = {'append', 'extend', 'insert', 'remove', 'pop', 'clear',
                      'sort', 'reverse', 'update', 'add', 'discard'}
SUBSCRIPT_METHODS = {'append', 'count', 'remove', 'insert', 'extend', 'index'}
CALL_PAREN_METHODS = {'reverse', 'sort', 'clear'}


def _collect_defined_names(tree):
    defined = set()

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            defined.add(node.name)
            for a in list(node.args.args) + list(node.args.kwonlyargs):
                defined.add(a.arg)
            if node.args.vararg:
                defined.add(node.args.vararg.arg)
            if node.args.kwarg:
                defined.add(node.args.kwarg.arg)
            self.generic_visit(node)

        def visit_Assign(self, node):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        defined.add(n.id)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    defined.add(n.id)
            self.generic_visit(node)

        def visit_For(self, node):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    defined.add(n.id)
            self.generic_visit(node)

        def visit_With(self, node):
            for item in node.items:
                if item.optional_vars:
                    for n in ast.walk(item.optional_vars):
                        if isinstance(n, ast.Name):
                            defined.add(n.id)
            self.generic_visit(node)

    V().visit(tree)
    return defined


def _fix_undefined_typos(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined = _collect_defined_names(tree)
    candidates_pool = set(defined) | {'list', 'dict', 'set', 'tuple', 'str'}
    builtin_names = set(dir(_builtins_mod))
    bad_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined and node.id not in builtin_names:
                bad_nodes.append(node)
    if not bad_nodes:
        return []
    mapping = {}
    for node in bad_nodes:
        name = node.id
        if name in mapping:
            continue
        pool = [c for c in candidates_pool if c != name]
        match = difflib.get_close_matches(name, pool, n=1, cutoff=0.6)
        if match:
            mapping[name] = match[0]
    if not mapping:
        return []
    spans = [(_span(source, n), mapping[n.id]) for n in bad_nodes if n.id in mapping]
    spans.sort(key=lambda x: x[0][0], reverse=True)
    new_source = source
    for (s, e), rep in spans:
        new_source = new_source[:s] + rep + new_source[e:]
    return [new_source] if new_source != source else []


def _fix_loop_var_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined = _collect_defined_names(tree)
    builtin_names = set(dir(_builtins_mod))
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            T = node.target.id
            undefined_nodes = []
            for sub in ast.walk(node):
                if sub is node.target:
                    continue
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    if sub.id not in defined and sub.id not in builtin_names:
                        undefined_nodes.append(sub)
            ids = set(n.id for n in undefined_nodes)
            if len(ids) == 1:
                U = ids.pop()
                if U != T:
                    spans = [_span(source, n) for n in undefined_nodes]
                    spans.sort(key=lambda x: x[0], reverse=True)
                    new_source = source
                    for s, e in spans:
                        new_source = new_source[:s] + T + new_source[e:]
                    if new_source != source:
                        results.append(new_source)
    return results


def _fix_iter_builtin_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not node.args.args:
                continue
            param = node.args.args[0].arg
            if param == 'list':
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.For) and isinstance(sub.iter, ast.Name) and sub.iter.id == 'list':
                    out.append(_splice(source, sub.iter, param))
    return out


def _fix_missing_call_parens(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute):
            attr = node.value
            if attr.attr in CALL_PAREN_METHODS:
                out.append(_splice(source, node.value, _text(source, node.value) + "()"))
    return out


def _fix_subscript_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr in SUBSCRIPT_METHODS:
                owner_text = _text(source, node.value)
                idx_text = _text(source, node.slice)
                new_text = f"{owner_text}({idx_text})"
                out.append(_splice(source, node, new_text))
    return out


def _fix_self_assign_mutator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            X = node.targets[0].id
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and isinstance(val.func.value, ast.Name):
                if val.func.value.id == X and val.func.attr in MUTATORS_NORETURN:
                    call_text = _text(source, val)
                    out.append(_splice(source, node, call_text))
    return out


def _fix_compare_as_statement(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq):
                right = cmp.comparators[0]
                if isinstance(right, ast.Call) and isinstance(right.func, ast.Attribute):
                    call_text = _text(source, right)
                    out.append(_splice(source, node.value, call_text))
    return out


def _fix_cross_assign_reverse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            X = node.targets[0].id
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
                    and val.func.attr in ('reverse', 'sort') and isinstance(val.func.value, ast.Name):
                Y = val.func.value.id
                if Y != X:
                    indent = " " * node.col_offset
                    args_text = ", ".join(_text(source, a) for a in val.args)
                    new_text = f"{X} = {Y}.copy()\n{indent}{X}.{val.func.attr}({args_text})"
                    out.append(_splice(source, node, new_text))
    return out


def _is_scalar_expr(expr, loopvar):
    if isinstance(expr, ast.Name) and expr.id == loopvar:
        return True
    if isinstance(expr, ast.Subscript):
        return True
    return False


def _fix_wrap_scalar_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.loopvar_stack = []

        def visit_For(self, node):
            lv = node.target.id if isinstance(node.target, ast.Name) else None
            self.loopvar_stack.append(lv)
            self.generic_visit(node)
            self.loopvar_stack.pop()

        def visit_AugAssign(self, node):
            if self.loopvar_stack and isinstance(node.op, ast.Add):
                lv = self.loopvar_stack[-1]
                if lv and _is_scalar_expr(node.value, lv) and not isinstance(node.value, ast.List):
                    val_text = _text(source, node.value)
                    out.append(_splice(source, node.value, "[" + val_text + "]"))
            self.generic_visit(node)

        def visit_Assign(self, node):
            if self.loopvar_stack and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                X = node.targets[0].id
                val = node.value
                if isinstance(val, ast.BinOp) and isinstance(val.op, ast.Add):
                    left = val.left
                    right = val.right
                    lv = self.loopvar_stack[-1]
                    if isinstance(left, ast.Name) and left.id == X and lv \
                            and _is_scalar_expr(right, lv) and not isinstance(right, ast.List):
                        right_text = _text(source, right)
                        out.append(_splice(source, right, "[" + right_text + "]"))
            self.generic_visit(node)

    V().visit(tree)
    return out


def _get_accumulator_name(if_node):
    for branch in (if_node.body, if_node.orelse):
        for stmt in branch:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == 'append' \
                        and isinstance(call.func.value, ast.Name) and len(call.args) == 1:
                    return call.func.value.id
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                return stmt.target.id
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                return stmt.targets[0].id
    return None


def _fix_wrong_membership_container(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loopvar = node.target.id
            for sub in ast.walk(node):
                if isinstance(sub, ast.If) and isinstance(sub.test, ast.Compare) and len(sub.test.ops) == 1:
                    op = sub.test.ops[0]
                    if isinstance(op, (ast.In, ast.NotIn)):
                        left = sub.test.left
                        if isinstance(left, ast.Name) and left.id == loopvar:
                            comparator = sub.test.comparators[0]
                            acc = _get_accumulator_name(sub)
                            if acc:
                                comp_text = _text(source, comparator)
                                if comp_text != acc:
                                    out.append(_splice(source, comparator, acc))
    return out


def _fix_return_none_to_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is None:
            out.append(_splice(source, node.value, "[]"))
    return out


def _fix_missing_import_ordereddict(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    uses = any(isinstance(n, ast.Name) and n.id == 'OrderedDict' for n in ast.walk(tree))
    if not uses:
        return []
    has_import = any(
        (isinstance(n, ast.ImportFrom) and any(a.name == 'OrderedDict' for a in n.names)) or
        (isinstance(n, ast.Import) and any(a.name == 'collections' for a in n.names))
        for n in ast.walk(tree)
    )
    if has_import:
        return []
    return ["from collections import OrderedDict\n" + source]


def _fix_insert_zero_to_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'insert':
            if len(node.args) == 2 and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0:
                owner_text = _text(source, node.func.value)
                second_text = _text(source, node.args[1])
                new_text = f"{owner_text}.append({second_text})"
                out.append(_splice(source, node, new_text))
    return out


def _fix_guard_empty_list(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            if len(body) >= 2 and isinstance(body[0], ast.Assign):
                a = body[0]
                if len(a.targets) == 1 and isinstance(a.targets[0], ast.Name) \
                        and isinstance(a.value, ast.Constant) and a.value.value == 1:
                    if isinstance(body[1], ast.While):
                        if not node.args.args:
                            continue
                        param = node.args.args[0].arg
                        s, _e = _span(source, a)
                        line_start = s - a.col_offset
                        indent = " " * a.col_offset
                        guard = f"{indent}if {param} == []: return {param}\n"
                        new_source = source[:line_start] + guard + source[line_start:]
                        out.append(new_source)
    return out


def _fix_missing_else_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body = node.body
            for i in range(len(body) - 1):
                stmt = body[i]
                if isinstance(stmt, ast.If) and not stmt.orelse and stmt.body:
                    nxt = body[i + 1]
                    if isinstance(nxt, ast.AugAssign) and isinstance(nxt.target, ast.Name) \
                            and isinstance(nxt.op, ast.Add):
                        var = nxt.target.id
                        test_names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
                        if var in test_names:
                            if_indent = " " * stmt.col_offset
                            body_indent = " " * stmt.body[0].col_offset
                            if_s, if_e = _span(source, stmt)
                            aug_s, aug_e = _span(source, nxt)
                            aug_text = source[aug_s:aug_e]
                            new_text = source[if_s:if_e] + "\n" + if_indent + "else:\n" + body_indent + aug_text
                            new_source = source[:if_s] + new_text + source[aug_e:]
                            out.append(new_source)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(name="undefined_name_typo_fix", apply=_fix_undefined_typos,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="loop_var_typo_fix", apply=_fix_loop_var_mismatch,
                 symptoms=("err:NameError",)),
            Rule(name="iterate_over_builtin_list_typo", apply=_fix_iter_builtin_list,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_call_parens_on_mutator", apply=_fix_missing_call_parens,
                 symptoms=("wrong",)),
            Rule(name="subscript_call_typo", apply=_fix_subscript_call,
                 symptoms=("err:TypeError",)),
            Rule(name="self_assign_mutator_drop", apply=_fix_self_assign_mutator,
                 symptoms=("wrong",)),
            Rule(name="compare_as_statement_drop", apply=_fix_compare_as_statement,
                 symptoms=("wrong",)),
            Rule(name="cross_var_reverse_assign_split", apply=_fix_cross_assign_reverse,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="wrap_scalar_as_list_concat", apply=_fix_wrap_scalar_list,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="wrong_membership_container", apply=_fix_wrong_membership_container,
                 symptoms=("wrong",)),
            Rule(name="return_none_to_empty_list", apply=_fix_return_none_to_list,
                 symptoms=("wrong",)),
            Rule(name="missing_import_ordereddict", apply=_fix_missing_import_ordereddict,
                 symptoms=("err:NameError",)),
            Rule(name="insert_zero_to_append", apply=_fix_insert_zero_to_append,
                 symptoms=("wrong",)),
            Rule(name="guard_empty_list_before_index_loop", apply=_fix_guard_empty_list,
                 symptoms=("err:IndexError",)),
            Rule(name="missing_else_before_increment", apply=_fix_missing_else_increment,
                 symptoms=("timeout", "wrong")),
        ]