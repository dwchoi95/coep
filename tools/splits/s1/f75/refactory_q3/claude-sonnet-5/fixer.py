"""
Repair module for the 'remove_extras' duplicate-elimination assignment.

Each Rule below targets one recurring misconception observed in buggy
submissions and performs a small, local AST-span splice to fix it.
"""

import ast
import builtins

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _annotate_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def _enclosing_for(node):
    p = getattr(node, "parent", None)
    while p is not None:
        if isinstance(p, ast.For):
            return p
        p = getattr(p, "parent", None)
    return None


def _enclosing_function(node):
    p = getattr(node, "parent", None)
    while p is not None:
        if isinstance(p, ast.FunctionDef):
            return p
        p = getattr(p, "parent", None)
    return None


def _find_container(tree, target):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            val = getattr(node, field, None)
            if isinstance(val, list):
                for i, s in enumerate(val):
                    if s is target:
                        return val, i
    return None, None


def _collect_defined_names(func):
    names = set(a.arg for a in func.args.args)
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
    return names


def _find_accumulator(body_stmts):
    for stmt in body_stmts:
        for node in ast.walk(stmt):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("append", "extend", "insert")
                    and isinstance(node.func.value, ast.Name)):
                return node.func.value.id
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                return node.target.id
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                return node.targets[0].id
    return None


def _find_first_empty_container(func):
    for stmt in func.body:
        if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)):
            val = stmt.value
            if isinstance(val, ast.List) and not val.elts:
                return stmt.targets[0].id
            if isinstance(val, ast.Tuple) and not val.elts:
                return stmt.targets[0].id
    return None


def _get_inplace_mutator(value):
    if (isinstance(value, ast.Call) and not value.args and not value.keywords
            and isinstance(value.func, ast.Attribute) and value.func.attr in ("reverse", "sort")
            and isinstance(value.func.value, ast.Name)):
        return value.func.value.id, value.func.attr
    if (isinstance(value, ast.Attribute) and value.attr in ("reverse", "sort")
            and isinstance(value.value, ast.Name)):
        return value.value.id, value.attr
    return None


# ----------------------------------------------------------------------
# Rule implementations
# ----------------------------------------------------------------------

def fix_iterate_builtin_list_name(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        if not func.args.args:
            continue
        param = func.args.args[0].arg
        for node in ast.walk(func):
            if isinstance(node, ast.For) and isinstance(node.iter, ast.Name) and node.iter.id == "list":
                new_source = _splice(source, node.iter, param)
                if new_source != source:
                    out.append(new_source)
    return out


def fix_membership_compare_operands(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _annotate_parents(tree)
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], (ast.In, ast.NotIn))
                and isinstance(node.test.left, ast.Name) and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Name)):
            forloop = _enclosing_for(node)
            if forloop is None or not isinstance(forloop.target, ast.Name):
                continue
            loopvar = forloop.target.id
            acc = _find_accumulator(node.body)
            if not acc:
                continue
            left_id = node.test.left.id
            right_id = node.test.comparators[0].id
            if left_id == loopvar and right_id == acc:
                continue
            op_text = "in" if isinstance(node.test.ops[0], ast.In) else "not in"
            new_test = f"{loopvar} {op_text} {acc}"
            new_source = _splice(source, node.test, new_test)
            if new_source != source:
                out.append(new_source)
    return out


def fix_in_polarity_before_append(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.In)
                and isinstance(node.test.left, ast.Name) and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Name)):
            left_id = node.test.left.id
            right_id = node.test.comparators[0].id
            found = False
            for stmt in ast.walk(node):
                if (isinstance(stmt, ast.Call) and isinstance(stmt.func, ast.Attribute)
                        and stmt.func.attr == "append" and isinstance(stmt.func.value, ast.Name)
                        and stmt.func.value.id == right_id and len(stmt.args) == 1
                        and isinstance(stmt.args[0], ast.Name) and stmt.args[0].id == left_id):
                    found = True
                    break
            if not found:
                continue
            new_test = f"{left_id} not in {right_id}"
            new_source = _splice(source, node.test, new_test)
            if new_source != source:
                out.append(new_source)
    return out


def fix_extend_arg(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "extend" and len(node.args) == 1):
            arg = node.args[0]
            if isinstance(arg, (ast.List, ast.Tuple)):
                continue
            if (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                    and arg.func.id == "list" and len(arg.args) == 1):
                inner = arg.args[0]
                s, e = _span(source, inner)
                new_text = f"[{source[s:e]}]"
                rs, re_ = _span(source, arg)
                new_source = source[:rs] + new_text + source[re_:]
            else:
                s, e = _span(source, arg)
                new_text = f"[{source[s:e]}]"
                new_source = source[:s] + new_text + source[e:]
            if new_source != source:
                out.append(new_source)
    return out


def fix_bare_method_call_statement(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    methods = {"reverse", "sort", "pop", "copy", "clear"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Attribute) and node.value.attr in methods:
            s, e = _span(source, node)
            new_source = source[:s] + source[s:e] + "()" + source[e:]
            if new_source != source:
                out.append(new_source)
    return out


def fix_return_inplace_mutator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            res = _get_inplace_mutator(node.value)
            if res:
                X, attr = res
                indent = " " * node.col_offset
                new_text = f"{X}.{attr}()\n{indent}return {X}"
                new_source = _splice(source, node, new_text)
                if new_source != source:
                    out.append(new_source)
    return out


def fix_assign_inplace_mutator(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            res = _get_inplace_mutator(node.value)
            if res:
                X, attr = res
                T = node.targets[0].id
                indent = " " * node.col_offset
                new_text = f"{T} = {X}.copy()\n{indent}{T}.{attr}()"
                new_source = _splice(source, node, new_text)
                if new_source != source:
                    out.append(new_source)
    return out


def fix_missing_final_reverse(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        reverses = [n for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "reverse" and isinstance(n.func.value, ast.Name)]
        if len(reverses) != 1:
            continue
        X = reverses[0].func.value.id
        if not func.body:
            continue
        last = func.body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.Name) and last.value.id == X:
            indent = " " * last.col_offset
            s, _e = _span(source, last)
            new_source = source[:s] + f"{X}.reverse()\n{indent}" + source[s:]
            if new_source != source:
                out.append(new_source)
    return out


def fix_count_check_wrong_target(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            test = node.test
            left = test.left
            op = test.ops[0]
            comp = test.comparators[0]
            if (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "count"
                    and len(left.args) == 1 and isinstance(left.func.value, ast.Name)
                    and isinstance(op, (ast.Eq, ast.Lt, ast.Gt, ast.LtE, ast.GtE))
                    and isinstance(comp, ast.Constant) and isinstance(comp.value, int)):
                acc = _find_accumulator(node.body)
                if not acc:
                    continue
                a_id = left.func.value.id
                already_ok = (a_id == acc and isinstance(op, ast.Eq) and comp.value == 0)
                if already_ok:
                    continue
                arg_s, arg_e = _span(source, left.args[0])
                arg_text = source[arg_s:arg_e]
                new_test_text = f"{acc}.count({arg_text}) == 0"
                new_source = _splice(source, test, new_test_text)
                if new_source != source:
                    out.append(new_source)
    return out


def fix_return_name_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        acc = _find_first_empty_container(func)
        if not acc:
            continue
        for stmt in ast.walk(func):
            if isinstance(stmt, ast.FunctionDef) and stmt is not func:
                continue
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name) and stmt.value.id != acc:
                new_source = _splice(source, stmt.value, acc)
                if new_source != source:
                    out.append(new_source)
    return out


def fix_missing_else_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and not node.orelse:
            container, idx = _find_container(tree, node)
            if container is None or idx + 1 >= len(container):
                continue
            nxt = container[idx + 1]
            if (isinstance(nxt, ast.AugAssign) and isinstance(nxt.op, ast.Add)
                    and isinstance(nxt.target, ast.Name)
                    and isinstance(nxt.value, ast.Constant) and nxt.value.value == 1):
                if_s, if_e = _span(source, node)
                nxt_s, nxt_e = _span(source, nxt)
                indent_if = " " * node.col_offset
                indent_body = indent_if + "    "
                nxt_text = source[nxt_s:nxt_e]
                else_block = f"\n{indent_if}else:\n{indent_body}{nxt_text}"
                new_source = source[:if_e] + else_block + source[nxt_e:]
                if new_source != source:
                    out.append(new_source)
    return out


def fix_undefined_accumulator_reference(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _annotate_parents(tree)
    out = []
    builtin_names = set(dir(builtins))
    for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        defined = _collect_defined_names(func)
        name_nodes = [n for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
        undefined = {}
        for n in name_nodes:
            if n.id not in defined and n.id not in builtin_names and n.id != func.name:
                undefined.setdefault(n.id, []).append(n)
        if len(undefined) != 1:
            continue
        uid, nodes = next(iter(undefined.items()))
        all_ok = True
        for n in nodes:
            parent = getattr(n, "parent", None)
            ok = False
            if isinstance(parent, ast.Attribute) and parent.attr in ("append", "extend") and parent.value is n:
                ok = True
            elif isinstance(parent, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in parent.ops):
                ok = True
            elif isinstance(parent, ast.AugAssign) and parent.target is n:
                ok = True
            if not ok:
                all_ok = False
                break
        if not all_ok:
            continue
        acc = _find_first_empty_container(func)
        if not acc or acc == uid:
            continue
        spans = sorted([_span(source, n) for n in nodes], key=lambda x: -x[0])
        new_source = source
        for s, e in spans:
            new_source = new_source[:s] + acc + new_source[e:]
        if new_source != source:
            out.append(new_source)
    return out


def fix_loop_var_mismatch(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    _annotate_parents(tree)
    out = []
    builtin_names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            L = node.target.id
            func = _enclosing_function(node)
            if func is None:
                continue
            defined = _collect_defined_names(func)
            undefined = {}
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                    if n.id not in defined and n.id not in builtin_names and n.id != func.name:
                        undefined.setdefault(n.id, []).append(n)
            if len(undefined) != 1:
                continue
            U, _nodes = next(iter(undefined.items()))
            rename_nodes = [node.target]
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and n.id == L and n is not node.target:
                    rename_nodes.append(n)
            spans = sorted([_span(source, n) for n in rename_nodes], key=lambda x: -x[0])
            new_source = source
            for s, e in spans:
                new_source = new_source[:s] + U + new_source[e:]
            if new_source != source:
                out.append(new_source)
    return out


def fix_lists_typo(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "lists":
            new_source = _splice(source, node.func, "list")
            if new_source != source:
                out.append(new_source)
    return out


def fix_missing_ordereddict_import(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    uses = any(isinstance(n, ast.Name) and n.id == "OrderedDict" for n in ast.walk(tree))
    if not uses:
        return []
    has_import = any(isinstance(n, ast.ImportFrom) and n.module == "collections"
                      and any(a.name == "OrderedDict" for a in n.names) for n in ast.walk(tree))
    if has_import:
        return []
    new_source = "from collections import OrderedDict\n" + source
    return [new_source]


def fix_set_to_ordereddict(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list"
                and len(node.args) == 1 and isinstance(node.args[0], ast.Call)
                and isinstance(node.args[0].func, ast.Name) and node.args[0].func.id == "set"
                and len(node.args[0].args) == 1):
            inner = node.args[0].args[0]
            inner_s, inner_e = _span(source, inner)
            inner_text = source[inner_s:inner_e]
            new_text = f"list(OrderedDict.fromkeys({inner_text}))"
            new_source = _splice(source, node, new_text)
            if "OrderedDict" not in source:
                new_source = "from collections import OrderedDict\n" + new_source
            if new_source != source:
                out.append(new_source)
    return out


def fix_subscript_as_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    methods = {"append", "extend", "insert", "remove", "pop"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr in methods:
            sl = node.slice
            if isinstance(sl, ast.Index):
                sl = sl.value
            owner_s, owner_e = _span(source, node.value)
            owner_text = source[owner_s:owner_e]
            idx_s, idx_e = _span(source, sl)
            idx_text = source[idx_s:idx_e]
            new_text = f"{owner_text}({idx_text})"
            new_source = _splice(source, node, new_text)
            if new_source != source:
                out.append(new_source)
    return out


def fix_append_return_assigned(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    methods = {"append", "extend", "insert", "sort", "reverse", "remove", "pop", "clear"}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in methods):
            call_s, call_e = _span(source, node.value)
            call_text = source[call_s:call_e]
            new_source = _splice(source, node, call_text)
            if new_source != source:
                out.append(new_source)
    return out


def fix_augassign_scalar_wrap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
            val = node.value
            if isinstance(val, (ast.List, ast.Tuple)):
                continue
            s, e = _span(source, val)
            new_text = f"[{source[s:e]}]"
            new_source = source[:s] + new_text + source[e:]
            if new_source != source:
                out.append(new_source)
    return out


def fix_assign_add_wrap(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add)
                and isinstance(node.value.left, ast.Name) and node.value.left.id == node.targets[0].id):
            right = node.value.right
            if isinstance(right, (ast.List, ast.Tuple)):
                continue
            if (isinstance(right, ast.Call) and isinstance(right.func, ast.Name)
                    and right.func.id == "list" and len(right.args) == 1):
                inner = right.args[0]
                s, e = _span(source, inner)
                new_text = f"[{source[s:e]}]"
                rs, re_ = _span(source, right)
                new_source = source[:rs] + new_text + source[re_:]
            else:
                s, e = _span(source, right)
                new_text = f"[{source[s:e]}]"
                new_source = source[:s] + new_text + source[e:]
            if new_source != source:
                out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="iterate_builtin_list_name",
                 apply=fix_iterate_builtin_list_name,
                 symptoms=("wrong", "err:NameError", "err:TypeError")),
            Rule(name="membership_compare_wrong_operands",
                 apply=fix_membership_compare_operands,
                 symptoms=("wrong",)),
            Rule(name="in_polarity_before_append",
                 apply=fix_in_polarity_before_append,
                 symptoms=("wrong",)),
            Rule(name="extend_scalar_arg",
                 apply=fix_extend_arg,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="bare_noarg_method_call",
                 apply=fix_bare_method_call_statement,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="return_inplace_mutator_result",
                 apply=fix_return_inplace_mutator,
                 symptoms=("wrong",)),
            Rule(name="assign_inplace_mutator_result",
                 apply=fix_assign_inplace_mutator,
                 symptoms=("wrong", "err:TypeError", "err:AttributeError")),
            Rule(name="missing_final_reverse",
                 apply=fix_missing_final_reverse,
                 symptoms=("wrong",)),
            Rule(name="count_check_wrong_target",
                 apply=fix_count_check_wrong_target,
                 symptoms=("wrong",)),
            Rule(name="return_name_mismatch",
                 apply=fix_return_name_mismatch,
                 symptoms=("wrong", "err:NameError")),
            Rule(name="missing_else_increment",
                 apply=fix_missing_else_increment,
                 symptoms=("wrong", "timeout")),
            Rule(name="undefined_accumulator_reference",
                 apply=fix_undefined_accumulator_reference,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="loop_var_mismatch",
                 apply=fix_loop_var_mismatch,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="lists_typo",
                 apply=fix_lists_typo,
                 symptoms=("err:NameError",)),
            Rule(name="missing_ordereddict_import",
                 apply=fix_missing_ordereddict_import,
                 symptoms=("err:NameError",)),
            Rule(name="set_to_ordereddict",
                 apply=fix_set_to_ordereddict,
                 symptoms=("wrong",)),
            Rule(name="subscript_as_call",
                 apply=fix_subscript_as_call,
                 symptoms=("err:TypeError",)),
            Rule(name="append_return_assigned",
                 apply=fix_append_return_assigned,
                 symptoms=("wrong",)),
            Rule(name="augassign_scalar_wrap",
                 apply=fix_augassign_scalar_wrap,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="assign_add_scalar_wrap",
                 apply=fix_assign_add_wrap,
                 symptoms=("wrong", "err:TypeError")),
        ]