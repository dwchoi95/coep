"""
Repair module for the "cAPS lOCK" assignment.

All rules are structural (AST-span splice) local edits targeting the
recurring misconceptions seen in student submissions for this problem:

  * calling a boolean string method without parentheses (`x.isupper`)
    when used as a condition,
  * calling `.upper()`/`.lower()` where `.isupper()`/`.islower()` was
    meant, inside a boolean test,
  * forgetting the single-character special case (`len(word) == 1`),
  * doing an unconditional/half-guarded "titlecase" transform
    (`word[0].upper() + word[1:].lower()`) instead of a guarded
    `swapcase()`,
  * using `.capitalize()`/`.title()` where `.swapcase()` is required,
  * writing the only-"else" branch with a `.title()`/`.capitalize()`
    call that should be a guarded `swapcase()`,
  * forgetting the `else` branch that keeps the accumulator string
    unchanged when iterating character by character.

Each rule returns zero or more alternative sources produced by a small,
localized text splice; none of them rewrite a whole function or module.
"""

import ast

from src.core.repair import Rule


# ----------------------------------------------------------------------
# generic span / splice helpers
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


def _indent_of(source, node):
    s, _ = _span(source, node)
    line_start = source.rfind("\n", 0, s) + 1
    return source[line_start:s]


def _unwrap_index(sl):
    if hasattr(ast, "Index") and isinstance(sl, ast.Index):
        return sl.value
    return sl


def _replace_attr_name(source, attr_node, old_name, new_name):
    s, e = _span(source, attr_node)
    text = source[s:e]
    if text.endswith(old_name):
        return source[:s] + text[: -len(old_name)] + new_name + source[e:]
    return None


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ----------------------------------------------------------------------
# Rule 1: boolean string-method called without parentheses
# ----------------------------------------------------------------------

BOOL_METHODS = {
    "isupper", "islower", "istitle", "isalpha",
    "isdigit", "isspace", "isnumeric", "isalnum",
}


def _fix_missing_bool_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    called_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_ids.add(id(node.func))
    targets = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and n.attr in BOOL_METHODS
        and id(n) not in called_ids
    ]
    if not targets:
        return []
    out = []
    for node in targets:
        s, e = _span(source, node)
        out.append(source[:e] + "()" + source[e:])
    if len(targets) > 1:
        ordered = sorted(targets, key=lambda n: _span(source, n)[0], reverse=True)
        new_source = source
        for node in ordered:
            s, e = _span(new_source, node)
            new_source = new_source[:e] + "()" + new_source[e:]
        out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 2: `.upper()`/`.lower()` used as a boolean test -> `.isupper()`/`.islower()`
# ----------------------------------------------------------------------

def _match_upper_lower_call(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
       and not node.args and not node.keywords:
        if node.func.attr == "upper":
            return "upper", "isupper"
        if node.func.attr == "lower":
            return "lower", "islower"
    return None


def _fix_bool_upper_lower_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    matches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            for val in node.values:
                m = _match_upper_lower_call(val)
                if m:
                    matches.append((val, m[0], m[1]))
        elif isinstance(node, ast.If):
            m = _match_upper_lower_call(node.test)
            if m:
                matches.append((node.test, m[0], m[1]))
    if not matches:
        return []
    out = []
    for call_node, old, new in matches:
        replaced = _replace_attr_name(source, call_node.func, old, new)
        if replaced:
            out.append(replaced)
    if len(matches) > 1:
        ordered = sorted(matches, key=lambda m: _span(source, m[0])[0], reverse=True)
        new_source = source
        for call_node, old, new in ordered:
            replaced = _replace_attr_name(new_source, call_node.func, old, new)
            if replaced:
                new_source = replaced
        out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 3: missing single-character special case
# ----------------------------------------------------------------------

def _add_len1_case(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        base = None
        for sub in ast.walk(test):
            if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                sl = _unwrap_index(sub.slice)
                if isinstance(sl, ast.Slice) and sl.upper is None and sl.lower is not None \
                   and isinstance(sl.lower, ast.Constant) and sl.lower.value == 1:
                    base = sub.value.id
                    break
        if base is None:
            continue
        s, e = _span(source, test)
        old_text = source[s:e]
        if ("len(%s)" % base).replace(" ", "") in old_text.replace(" ", ""):
            continue
        new_text = "len(%s) == 1 or (%s)" % (base, old_text)
        out.append(source[:s] + new_text + source[e:])
    return out


# ----------------------------------------------------------------------
# shared matchers for the "titlecase instead of swapcase" family
# ----------------------------------------------------------------------

def _is_full_upper_bound(node, base):
    if node is None:
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len" \
       and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == base:
        return True
    return False


def _match_subscript0(node):
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
        return None
    sl = _unwrap_index(node.slice)
    if isinstance(sl, ast.Constant) and sl.value == 0:
        return node.value.id
    return None


def _match_subscript_rest(node):
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
        return None
    sl = _unwrap_index(node.slice)
    if isinstance(sl, ast.Slice) and sl.lower is not None and isinstance(sl.lower, ast.Constant) \
       and sl.lower.value == 1:
        base = node.value.id
        if _is_full_upper_bound(sl.upper, base):
            return base
    return None


def _match_idx0_upper_or_bare(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
       and node.func.attr == "upper" and not node.args and not node.keywords:
        return _match_subscript0(node.func.value)
    return _match_subscript0(node)


def _match_idx1_rest(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
       and node.func.attr == "lower" and not node.args and not node.keywords:
        return _match_subscript_rest(node.func.value)
    return _match_subscript_rest(node)


def _match_titlecase_binop(node):
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
        return None
    b1 = _match_idx0_upper_or_bare(node.left)
    if b1 is None:
        return None
    b2 = _match_idx1_rest(node.right)
    if b2 == b1:
        return b1
    return None


# ----------------------------------------------------------------------
# Rule 4: bare/half-guarded titlecase assign or print -> guarded swapcase
# ----------------------------------------------------------------------

def _titlecase_stmt_fix(source, stmt):
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        base = _match_titlecase_binop(stmt.value)
        if base and stmt.targets[0].id == base:
            indent = _indent_of(source, stmt)
            new_text = (
                "if %s[1:] == %s[1:].upper():\n"
                "%s    %s = %s.swapcase()" % (base, base, indent, base, base)
            )
            s, e = _span(source, stmt)
            return source[:s] + new_text + source[e:]
    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Name) and call.func.id == "print" \
           and len(call.args) == 1 and not call.keywords:
            base = _match_titlecase_binop(call.args[0])
            if base:
                indent = _indent_of(source, stmt)
                new_text = (
                    "if %s[1:] == %s[1:].upper():\n"
                    "%s    print(%s.swapcase())\n"
                    "%selse:\n"
                    "%s    print(%s)" % (base, base, indent, base, indent, indent, base)
                )
                s, e = _span(source, stmt)
                return source[:s] + new_text + source[e:]
    return None


def _fix_bare_titlecase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    seen = set()
    for parent in ast.walk(tree):
        for attr_name in ("body", "orelse", "finalbody"):
            body = getattr(parent, attr_name, None)
            if not isinstance(body, list):
                continue
            for stmt in body:
                try:
                    result = _titlecase_stmt_fix(source, stmt)
                except Exception:
                    result = None
                if result:
                    key = _span(source, stmt)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(result)
    return out


# ----------------------------------------------------------------------
# Rule 5: two consecutive `print` statements doing the titlecase split
# ----------------------------------------------------------------------

def _match_print_call(stmt):
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Name) and call.func.id == "print" and call.args:
            return call.args[0]
    return None


def _fix_two_print_titlecase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for parent in ast.walk(tree):
        body = getattr(parent, "body", None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            a1 = _match_print_call(s1)
            a2 = _match_print_call(s2)
            if a1 is None or a2 is None:
                continue
            b1 = _match_idx0_upper_or_bare(a1)
            if b1 is None:
                continue
            b2 = _match_idx1_rest(a2)
            if b2 != b1:
                continue
            base = b1
            indent = _indent_of(source, s1)
            new_text = (
                "if %s[1:] == %s[1:].upper():\n"
                "%s    print(%s.swapcase())\n"
                "%selse:\n"
                "%s    print(%s)" % (base, base, indent, base, indent, indent, base)
            )
            s_start, _e1 = _span(source, s1)
            _s2, s_end = _span(source, s2)
            out.append(source[:s_start] + new_text + source[s_end:])
    return out


# ----------------------------------------------------------------------
# Rule 6: `.capitalize()` / `.title()` -> `.swapcase()`
# ----------------------------------------------------------------------

def _fix_capitalize_to_swapcase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
           and node.func.attr in ("capitalize", "title") and not node.args and not node.keywords:
            nodes.append(node.func)
    if not nodes:
        return []
    out = []
    for attr_node in nodes:
        replaced = _replace_attr_name(source, attr_node, attr_node.attr, "swapcase")
        if replaced:
            out.append(replaced)
    if len(nodes) > 1:
        ordered = sorted(nodes, key=lambda n: _span(source, n)[0], reverse=True)
        new_source = source
        for attr_node in ordered:
            replaced = _replace_attr_name(new_source, attr_node, attr_node.attr, "swapcase")
            if replaced:
                new_source = replaced
        if new_source != source:
            out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule 7: `if X.upper() == X: ... else: print(X.title()/.capitalize())`
# ----------------------------------------------------------------------

def _match_upper_eq_self(test):
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        return None
    left, right = test.left, test.comparators[0]

    def is_upper_call(n, name):
        return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
            and n.func.attr == "upper" and not n.args and not n.keywords \
            and isinstance(n.func.value, ast.Name) and n.func.value.id == name

    if isinstance(left, ast.Name) and is_upper_call(right, left.id):
        return left.id
    if isinstance(right, ast.Name) and is_upper_call(left, right.id):
        return right.id
    return None


def _fix_single_branch_upper_check(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        base = _match_upper_eq_self(node.test)
        if base is None:
            continue
        if len(node.orelse) != 1:
            continue
        stmt = node.orelse[0]
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
            continue
        call = stmt.value
        if not (isinstance(call.func, ast.Name) and call.func.id == "print"
                and len(call.args) == 1 and not call.keywords):
            continue
        arg = call.args[0]
        if not (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                and arg.func.attr in ("title", "capitalize")
                and not arg.args and not arg.keywords):
            continue
        if not (isinstance(arg.func.value, ast.Name) and arg.func.value.id == base):
            continue
        indent = _indent_of(source, stmt)
        new_text = (
            "if %s[1:] == %s[1:].upper():\n"
            "%s    print(%s.swapcase())\n"
            "%selse:\n"
            "%s    print(%s)" % (base, base, indent, base, indent, indent, base)
        )
        s, e = _span(source, stmt)
        out.append(source[:s] + new_text + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule 8: for-loop accumulator missing the "keep unchanged" else branch
# ----------------------------------------------------------------------

def _add_else_for_loop_accum(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or node.orelse:
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.For):
            continue
        for_node = node.body[0]
        if not isinstance(for_node.iter, ast.Name):
            continue
        base = for_node.iter.id
        target = None
        for st in ast.walk(for_node):
            if isinstance(st, ast.AugAssign) and isinstance(st.op, ast.Add) \
               and isinstance(st.target, ast.Name):
                target = st.target.id
                break
        if target is None:
            continue
        indent = _indent_of(source, node)
        s, e = _span(source, for_node)
        insertion = "\n%selse:\n%s    %s = %s" % (indent, indent, target, base)
        out.append(source[:e] + insertion + source[e:])
    return out


# ----------------------------------------------------------------------
# Fixer
# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="missing_bool_method_call_parens",
                apply=_fix_missing_bool_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="upper_lower_call_should_be_isupper_islower_in_bool_context",
                apply=_fix_bool_upper_lower_call,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_single_char_special_case",
                apply=_add_len1_case,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_titlecase_should_be_guarded_swapcase",
                apply=_fix_bare_titlecase,
                symptoms=("wrong",),
            ),
            Rule(
                name="two_print_titlecase_should_be_guarded_swapcase",
                apply=_fix_two_print_titlecase,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_or_title_should_be_swapcase",
                apply=_fix_capitalize_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="single_else_titlecase_branch_should_be_guarded_swapcase",
                apply=_fix_single_branch_upper_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="loop_accumulator_missing_unchanged_else",
                apply=_add_else_for_loop_accum,
                symptoms=("wrong",),
            ),
        ]