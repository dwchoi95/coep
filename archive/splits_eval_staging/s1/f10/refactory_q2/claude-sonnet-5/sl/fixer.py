import ast
import builtins

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


def _line_indent(source, pos):
    line_start = source.rfind("\n", 0, pos) + 1
    return source[line_start:pos]


_BUILTIN_NAMES = set(dir(builtins)) | {"True", "False", "None"}


def _module_global_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


# ---------------------------------------------------------------------------
# Rule: undefined free variable used instead of the parameter (unique_day /
# unique_month only), e.g. `def unique_day(date, ...): ... if day == i[1]`
# ---------------------------------------------------------------------------
def fix_undefined_name_use_param(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    global_names = _module_global_names(tree) | _BUILTIN_NAMES
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name not in ("unique_day", "unique_month"):
            continue
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        defined = set(params)
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                defined.add(n.id)
            if isinstance(n, ast.arg):
                defined.add(n.arg)
        undefined_nodes = []
        undefined_ids = set()
        for n in ast.walk(func):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                if n.id not in defined and n.id not in global_names:
                    undefined_nodes.append(n)
                    undefined_ids.add(n.id)
        if len(undefined_ids) != 1:
            continue
        bad_id = next(iter(undefined_ids))
        replacement = params[0]
        if replacement == bad_id:
            continue
        spans = sorted((_span(source, n) for n in undefined_nodes),
                       key=lambda x: x[0], reverse=True)
        new_src = source
        for s, e in spans:
            new_src = new_src[:s] + replacement + new_src[e:]
        out.append(new_src)
    return out


# ---------------------------------------------------------------------------
# Rule: boolean-flag uniqueness toggle that forgets the "never seen" case.
# ---------------------------------------------------------------------------
def fix_boolean_flag_trailing_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        flagvar = None
        for n in ast.walk(func):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name)
                    and isinstance(n.value, ast.Constant) and n.value.value is False):
                flagvar = n.targets[0].id
                break
        if flagvar is None:
            continue
        found = False
        for n in ast.walk(func):
            if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == flagvar:
                for stmt in n.body:
                    if (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant)
                            and stmt.value.value is False):
                        found = True
        if not found:
            continue
        out.append(_splice(source, last, f"return {flagvar}"))
    return out


# ---------------------------------------------------------------------------
# Rule: `if count > 1: return False else: return True` style threshold that
# misclassifies zero occurrences as unique; tighten to an exact-one check.
# ---------------------------------------------------------------------------
def fix_threshold_to_exact_one(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1):
            continue
        op = test.ops[0]
        if not isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE)):
            continue
        if not isinstance(test.left, ast.Name):
            continue
        if not (len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
                and isinstance(test.comparators[0].value, int)
                and not isinstance(test.comparators[0].value, bool)):
            continue
        if len(node.body) != 1 or len(node.orelse) != 1:
            continue
        b0, b1 = node.body[0], node.orelse[0]
        if not (isinstance(b0, ast.Return) and isinstance(b1, ast.Return)):
            continue
        if not (isinstance(b0.value, ast.Constant) and isinstance(b0.value.value, bool)):
            continue
        if not (isinstance(b1.value, ast.Constant) and isinstance(b1.value.value, bool)):
            continue
        if b0.value.value == b1.value.value:
            continue
        var_name = test.left.id
        new_cmp = f"{var_name} != 1" if b0.value.value is False else f"{var_name} == 1"
        out.append(_splice(source, test, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule: `if count > 1 (or >= 2): return False` followed by an unconditional
# trailing `return True` (missing the exactly-one check for the else path).
# ---------------------------------------------------------------------------
def fix_sequential_threshold_then_return_true(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or not func.body:
            continue
        last = func.body[-1]
        if not (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                and last.value.value is True):
            continue
        count_var = None
        for n in ast.walk(func):
            if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and len(n.test.ops) == 1
                    and isinstance(n.test.ops[0], (ast.Gt, ast.GtE))
                    and isinstance(n.test.left, ast.Name)
                    and len(n.body) == 1 and not n.orelse
                    and isinstance(n.body[0], ast.Return)
                    and isinstance(n.body[0].value, ast.Constant)
                    and n.body[0].value.value is False):
                count_var = n.test.left.id
                break
        if count_var is None:
            continue
        out.append(_splice(source, last, f"return {count_var} == 1"))
    return out


# ---------------------------------------------------------------------------
# Rule: membership test against the whole tuple instead of equality against
# the correct index, inside unique_day / unique_month.
# ---------------------------------------------------------------------------
def fix_membership_should_be_index_equality(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("unique_day", "unique_month"):
            continue
        idx = 1 if func.name == "unique_day" else 0
        params = [a.arg for a in func.args.args]
        if not params:
            continue
        pname = params[0]
        for n in ast.walk(func):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.In):
                left = n.left
                right = n.comparators[0]
                if isinstance(left, ast.Name) and left.id == pname and isinstance(right, ast.Name):
                    new_cmp = f"{pname} == {right.id}[{idx}]"
                    out.append(_splice(source, n, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule: contains_unique_day returns the raw comparison result on the first
# unique_day() hit instead of ANDing the month check and continuing the loop.
# ---------------------------------------------------------------------------
def fix_contains_unique_day_premature_compare_return(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        target = None
        for n in ast.walk(func):
            if isinstance(n, ast.If) and len(n.body) == 1:
                stmt = n.body[0]
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Compare):
                    target = (n, stmt)
                    break
        if target is None:
            continue
        n, stmt = target
        ts, te = _span(source, n.test)
        cs, ce = _span(source, stmt.value)
        new_test = source[ts:te] + " and (" + source[cs:ce] + ")"
        stmt_s, _ = _span(source, stmt)
        indent = _line_indent(source, stmt_s)
        new_if_text = "if " + new_test + ":\n" + indent + "return True"

        edits = [_span(source, n) + (new_if_text,)]

        last = func.body[-1]
        already_false = (isinstance(last, ast.Return) and isinstance(last.value, ast.Constant)
                          and last.value.value is False)
        if not already_false:
            func_first_s, _ = _span(source, func.body[0])
            func_indent = _line_indent(source, func_first_s)
            _, last_e = _span(source, last)
            edits.append((last_e, last_e, "\n" + func_indent + "return False"))

        edits.sort(key=lambda t: t[0], reverse=True)
        candidate = source
        for s, e, rep in edits:
            candidate = candidate[:s] + rep + candidate[e:]
        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule: off-by-one while-loop bound `i <= len(x)` -> `i < len(x)`.
# ---------------------------------------------------------------------------
def fix_while_offbyone(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.LtE):
            right = node.comparators[0]
            if isinstance(right, ast.Call) and isinstance(right.func, ast.Name) and right.func.id == "len":
                ls, le = _span(source, node.left)
                rs, re_ = _span(source, right)
                new_cmp = source[ls:le] + " < " + source[rs:re_]
                out.append(_splice(source, node, new_cmp))
    return out


# ---------------------------------------------------------------------------
# Rule: while loop index variable is never incremented at all (infinite loop).
# ---------------------------------------------------------------------------
def fix_while_missing_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While) or not node.body:
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)):
            continue
        loopvar = test.left.id
        has_incr = False
        for n in ast.walk(node):
            if n is node:
                continue
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == loopvar:
                has_incr = True
            if (isinstance(n, ast.Assign) and len(n.targets) == 1
                    and isinstance(n.targets[0], ast.Name) and n.targets[0].id == loopvar):
                has_incr = True
        if has_incr:
            continue
        last = node.body[-1]
        indent = _line_indent(source, _span(source, last)[0])
        _, e = _span(source, last)
        candidate = source[:e] + "\n" + indent + f"{loopvar} += 1" + source[e:]
        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule: while loop index is incremented only conditionally (nested inside an
# `if`), causing an infinite loop whenever no match is found.
# ---------------------------------------------------------------------------
def fix_while_conditional_increment(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While) or not node.body:
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)):
            continue
        loopvar = test.left.id
        top_level_ids = {id(s) for s in node.body}
        target_incr = None
        for n in ast.walk(node):
            if n is node:
                continue
            if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == loopvar:
                target_incr = n
                break
        if target_incr is None or id(target_incr) in top_level_ids:
            continue

        incr_s, incr_e = _span(source, target_incr)
        line_start = source.rfind("\n", 0, incr_s) + 1
        prefix = source[line_start:incr_s]
        remove_s = line_start if prefix.strip() == "" else incr_s
        remove_e = incr_e
        if remove_e < len(source) and source[remove_e] == "\n":
            remove_e += 1

        last_stmt = node.body[-1]
        _, body_end = _span(source, last_stmt)
        body_first_s, _ = _span(source, node.body[0])
        indent = _line_indent(source, body_first_s)
        incr_text = source[incr_s:incr_e]

        edits = [(remove_s, remove_e, ""), (body_end, body_end, "\n" + indent + incr_text)]
        edits.sort(key=lambda t: t[0], reverse=True)
        candidate = source
        for s, e, rep in edits:
            candidate = candidate[:s] + rep + candidate[e:]
        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule: contains_unique_day never calls unique_day at all (hardcoded/stub
# logic) - rebuild its body using the required helper.
# ---------------------------------------------------------------------------
def fix_contains_unique_day_missing_helper_call(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name != "contains_unique_day":
            continue
        has_call = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "unique_day" for n in ast.walk(func))
        if has_call or not func.body:
            continue
        params = [a.arg for a in func.args.args]
        if len(params) < 2:
            continue
        month_p, days_p = params[0], params[1]
        first_s, _ = _span(source, func.body[0])
        _, last_e = _span(source, func.body[-1])
        indent = _line_indent(source, first_s)
        new_body = (
            f"for i in {days_p}:\n"
            f"{indent}    if {month_p} == i[0]:\n"
            f"{indent}        if unique_day(i[1], {days_p}):\n"
            f"{indent}            return True\n"
            f"{indent}return False"
        )
        candidate = source[:first_s] + new_body + source[last_e:]
        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule: unique_day / unique_month body is a bare stub `return` - fill in the
# canonical counting implementation using the function's own parameter names.
# ---------------------------------------------------------------------------
def fix_bare_return_stub(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("unique_day", "unique_month"):
            continue
        if len(func.body) != 1:
            continue
        stmt = func.body[0]
        is_bare = isinstance(stmt, ast.Return) and (
            stmt.value is None or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)
        )
        if not is_bare:
            continue
        params = [a.arg for a in func.args.args]
        if len(params) < 2:
            continue
        key_p, days_p = params[0], params[1]
        idx = 1 if func.name == "unique_day" else 0
        s, e = _span(source, stmt)
        indent = _line_indent(source, s)
        body_text = (
            f"count = 0\n"
            f"{indent}for i in {days_p}:\n"
            f"{indent}    if {key_p} == i[{idx}]:\n"
            f"{indent}        count += 1\n"
            f"{indent}return count == 1"
        )
        candidate = source[:s] + body_text + source[e:]
        out.append(candidate)
    return out


# ---------------------------------------------------------------------------
# Rule: a helper function is referenced by name in a Compare without being
# called, e.g. `if count_dates == 0:` instead of `count_dates(...) == 1`.
# ---------------------------------------------------------------------------
def fix_uncalled_function_in_compare(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    func_defs = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_defs[node.name] = [a.arg for a in node.args.args]
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        enclosing_params = [a.arg for a in func.args.args]
        for n in ast.walk(func):
            if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Eq):
                sides = [n.left] + list(n.comparators)
                for side in sides:
                    if isinstance(side, ast.Name) and side.id in func_defs and side.id != func.name:
                        callee_params = func_defs[side.id]
                        argc = len(callee_params)
                        if 0 < argc <= len(enclosing_params):
                            args_text = ", ".join(enclosing_params[:argc])
                            new_cmp_text = f"{side.id}({args_text}) == 1"
                            out.append(_splice(source, n, new_cmp_text))
    return out


# ---------------------------------------------------------------------------
# Rule: the module never defines one or more of the required functions
# (unique_day / unique_month / contains_unique_day) - add canonical ones.
# ---------------------------------------------------------------------------
_CANONICAL = {
    "unique_day": (
        "def unique_day(day, possible_birthdays):\n"
        "    count = 0\n"
        "    for i in possible_birthdays:\n"
        "        if day == i[1]:\n"
        "            count += 1\n"
        "    return count == 1\n"
    ),
    "unique_month": (
        "def unique_month(month, possible_birthdays):\n"
        "    count = 0\n"
        "    for i in possible_birthdays:\n"
        "        if month == i[0]:\n"
        "            count += 1\n"
        "    return count == 1\n"
    ),
    "contains_unique_day": (
        "def contains_unique_day(month, possible_birthdays):\n"
        "    for i in possible_birthdays:\n"
        "        if month == i[0]:\n"
        "            if unique_day(i[1], possible_birthdays):\n"
        "                return True\n"
        "    return False\n"
    ),
}


def fix_missing_required_functions(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    missing = [name for name in ("unique_day", "unique_month", "contains_unique_day")
               if name not in defined]
    if not missing:
        return []
    prefix = "".join(_CANONICAL[m] + "\n" for m in missing)
    return [prefix + source]


class Fixer:
    def rules(self):
        return [
            Rule(name="undefined_name_use_param",
                 apply=fix_undefined_name_use_param,
                 symptoms=("err:NameError", "wrong")),
            Rule(name="boolean_flag_trailing_return",
                 apply=fix_boolean_flag_trailing_return,
                 symptoms=("wrong",)),
            Rule(name="threshold_to_exact_one",
                 apply=fix_threshold_to_exact_one,
                 symptoms=("wrong",)),
            Rule(name="sequential_threshold_then_return_true",
                 apply=fix_sequential_threshold_then_return_true,
                 symptoms=("wrong",)),
            Rule(name="membership_should_be_index_equality",
                 apply=fix_membership_should_be_index_equality,
                 symptoms=("wrong",)),
            Rule(name="contains_unique_day_premature_compare_return",
                 apply=fix_contains_unique_day_premature_compare_return,
                 symptoms=("wrong",)),
            Rule(name="while_offbyone",
                 apply=fix_while_offbyone,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="while_missing_increment",
                 apply=fix_while_missing_increment,
                 symptoms=("timeout",)),
            Rule(name="while_conditional_increment",
                 apply=fix_while_conditional_increment,
                 symptoms=("timeout", "wrong")),
            Rule(name="contains_unique_day_missing_helper_call",
                 apply=fix_contains_unique_day_missing_helper_call,
                 symptoms=("wrong",)),
            Rule(name="bare_return_stub",
                 apply=fix_bare_return_stub,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="uncalled_function_in_compare",
                 apply=fix_uncalled_function_in_compare,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="missing_required_functions",
                 apply=fix_missing_required_functions,
                 symptoms=("err:NameError", "wrong")),
        ]