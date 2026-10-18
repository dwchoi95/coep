"""
Repair rules for the "cAPS lOCK" (Codeforces 131A) assignment.

Each rule targets one recurring misconception observed in buggy student
submissions and proposes small, local, structural edits (computed via AST
node spans spliced back into the original source text).
"""

import ast

from src.core.repair import Rule


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------

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


def _safe_parse(source):
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError):
        return None


def _unwrap_index(sl):
    # Python < 3.9 wraps subscript indices in ast.Index
    if isinstance(sl, ast.Index):
        return sl.value
    return sl


def _call_func_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            ids.add(id(node.func))
    return ids


# --------------------------------------------------------------------------
# Rule 1: s.capitalize() / s.title()  ->  s.swapcase()
# --------------------------------------------------------------------------

def _capitalize_title_to_swapcase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("capitalize", "title"):
            targets.append(node)
    if not targets:
        return []

    out = []

    def replace_attr(src, node, new_attr):
        vs, ve = _span(src, node.value)
        ns, ne = _span(src, node)
        value_text = src[vs:ve]
        return src[:ns] + value_text + "." + new_attr + src[ne:]

    # one candidate per individual occurrence
    for t in targets:
        out.append(replace_attr(source, t, "swapcase"))

    # one candidate with ALL occurrences replaced at once
    if len(targets) > 1:
        targets_sorted = sorted(targets, key=lambda n: n.col_offset)
        # process from rightmost to leftmost using absolute spans
        spans = sorted((_span(source, t) for t in targets), key=lambda x: x[0], reverse=True)
        new_src = source
        for (s, e) in spans:
            # find matching node again by span (cheap, targets list small)
            pass
        # simpler: rebuild using attribute replace, rightmost-first
        targets_by_pos = sorted(targets, key=lambda n: _span(source, n)[0], reverse=True)
        new_src = source
        for t in targets_by_pos:
            new_src = replace_attr(new_src, t, "swapcase")
        out.append(new_src)

    return out


# --------------------------------------------------------------------------
# Rule 2: bare / mis-named boolean-context case methods
#   - obj.isupper   (missing call)         -> obj.isupper()
#   - obj.upper     (missing call, meant isX) -> obj.isupper()
#   - obj.upper()   (called, meant isX)    -> obj.isupper()
#   (symmetrically for lower/islower)
# --------------------------------------------------------------------------

_WRAP_ONLY = {"isupper", "islower", "isalpha", "isdigit", "istitle",
              "isspace", "isalnum", "capitalize", "title", "swapcase"}
_RENAME_BARE = {"upper": "isupper", "lower": "islower"}
_RENAME_CALLED = {"upper": "isupper", "lower": "islower"}


def _collect_bool_leaves(test):
    """Collect ids of leaf expressions directly tested as booleans."""
    leaves = []

    def visit(node):
        if isinstance(node, ast.BoolOp):
            for v in node.values:
                visit(v)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            visit(node.operand)
        else:
            leaves.append(node)

    visit(test)
    return leaves


def _bool_context_case_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    call_func_ids = _call_func_ids(tree)

    out = []
    stmt_types = (ast.If, ast.While)
    test_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, stmt_types):
            test_nodes.append(node.test)
        elif isinstance(node, (ast.IfExp, ast.Assert)):
            test_nodes.append(node.test)

    for test in test_nodes:
        leaves = _collect_bool_leaves(test)
        edits = []  # list of (start, end, new_text)
        for leaf in leaves:
            if isinstance(leaf, ast.Attribute) and id(leaf) not in call_func_ids:
                if leaf.attr in _WRAP_ONLY:
                    s, e = _span(source, leaf)
                    edits.append((s, e, source[s:e] + "()"))
                elif leaf.attr in _RENAME_BARE:
                    vs, ve = _span(source, leaf.value)
                    s, e = _span(source, leaf)
                    new_attr = _RENAME_BARE[leaf.attr]
                    edits.append((s, e, source[vs:ve] + "." + new_attr + "()"))
            elif (isinstance(leaf, ast.Call) and isinstance(leaf.func, ast.Attribute)
                  and not leaf.args and not leaf.keywords
                  and leaf.func.attr in _RENAME_CALLED):
                vs, ve = _span(source, leaf.func.value)
                s, e = _span(source, leaf)
                new_attr = _RENAME_CALLED[leaf.func.attr]
                edits.append((s, e, source[vs:ve] + "." + new_attr + "()"))
        if not edits:
            continue
        edits.sort(key=lambda t: t[0], reverse=True)
        new_src = source
        for (s, e, text) in edits:
            new_src = new_src[:s] + text + new_src[e:]
        out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 3: single-character words always need swapcase; insert a safe
# short-circuit right after the line that reads input.
# --------------------------------------------------------------------------

def _finds_input_assign(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            for sub in ast.walk(node.value):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                   and sub.func.id == "input":
                    found.append(node)
                    break
    found.sort(key=lambda n: (n.lineno, n.col_offset))
    return found


def _insert_len1_shortcut(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    assigns = _finds_input_assign(tree)
    if not assigns:
        return []

    out = []
    lines = source.splitlines(keepends=True)
    for node in assigns:
        varname = node.targets[0].id
        # Verify the statement starts at the beginning of its line
        # (col_offset chars are all whitespace).
        line_idx = node.lineno - 1
        line = lines[line_idx]
        prefix = line[:node.col_offset]
        if prefix.strip() != "":
            continue
        indent = " " * node.col_offset
        _, end_off = _span(source, node)
        # move to right after the end-of-line following the statement
        nl_pos = source.find("\n", end_off)
        if nl_pos == -1:
            insert_pos = len(source)
            prefix_nl = "\n"
        else:
            insert_pos = nl_pos + 1
            prefix_nl = ""
        block = (
            prefix_nl
            + indent + "if len(%s) == 1:\n" % varname
            + indent + "    print(%s.swapcase())\n" % varname
            + indent + "    exit()\n"
        )
        new_src = source[:insert_pos] + block + source[insert_pos:]
        out.append(new_src)
    return out


# --------------------------------------------------------------------------
# Rule 4: manual "capitalize" construction  var[0].upper() + var[1:].lower()
#          -> var.swapcase()
# --------------------------------------------------------------------------

def _is_var_zero_index(node, varname):
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id != varname:
        return False
    sl = _unwrap_index(node.slice)
    return isinstance(sl, ast.Constant) and sl.value == 0


def _is_var_from1_slice(node, varname):
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id != varname:
        return False
    sl = _unwrap_index(node.slice)
    if not isinstance(sl, ast.Slice):
        return False
    if sl.lower is None or not (isinstance(sl.lower, ast.Constant) and sl.lower.value == 1):
        return False
    if sl.upper is None:
        return True
    if isinstance(sl.upper, ast.Call) and isinstance(sl.upper.func, ast.Name) \
       and sl.upper.func.id == "len":
        return True
    return False


def _firstupper_restlower_to_swapcase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = node.left, node.right
            if not (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                    and left.func.attr == "upper" and not left.args):
                continue
            if not (isinstance(right, ast.Call) and isinstance(right.func, ast.Attribute)
                    and right.func.attr == "lower" and not right.args):
                continue
            lv, rv = left.func.value, right.func.value
            if isinstance(lv, ast.Subscript) and isinstance(rv, ast.Subscript) \
               and isinstance(lv.value, ast.Name) and isinstance(rv.value, ast.Name) \
               and lv.value.id == rv.value.id:
                varname = lv.value.id
                if _is_var_zero_index(lv, varname) and _is_var_from1_slice(rv, varname):
                    out.append(_splice(source, node, "%s.swapcase()" % varname))
    return out


def _print_call_target(stmt):
    if not isinstance(stmt, ast.Expr):
        return None
    call = stmt.value
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == "print"):
        return None
    if len(call.args) != 1:
        return None
    return call.args[0]


def _match_print_upper_first(stmt):
    arg = _print_call_target(stmt)
    if arg is None:
        return None
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
       and arg.func.attr == "upper" and not arg.args:
        sub = arg.func.value
        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
            varname = sub.value.id
            if _is_var_zero_index(sub, varname):
                return varname
    return None


def _match_print_lower_rest(stmt):
    arg = _print_call_target(stmt)
    if arg is None:
        return None
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) \
       and arg.func.attr == "lower" and not arg.args:
        sub = arg.func.value
        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
            varname = sub.value.id
            if _is_var_from1_slice(sub, varname):
                return varname
    return None


def _two_print_capitalize_to_swapcase(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for i in range(len(body) - 1):
            s1, s2 = body[i], body[i + 1]
            v1 = _match_print_upper_first(s1)
            v2 = _match_print_lower_rest(s2)
            if v1 is not None and v1 == v2:
                s_start, _ = _span(source, s1)
                _, e_end = _span(source, s2)
                new_text = "print(%s.swapcase())" % v1
                out.append(source[:s_start] + new_text + source[e_end:])
    return out


# --------------------------------------------------------------------------
# Rule 5: flip a single isupper()/islower() call (wrong direction)
# --------------------------------------------------------------------------

def _flip_is_case_single(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and not node.args and not node.keywords
                and node.func.attr in ("isupper", "islower")):
            vs, ve = _span(source, node.func.value)
            s, e = _span(source, node)
            new_attr = "islower" if node.func.attr == "isupper" else "isupper"
            new_text = source[vs:ve] + "." + new_attr + "()"
            out.append(source[:s] + new_text + source[e:])
    return out


# --------------------------------------------------------------------------
# Rule 6: `if x.islower(): x = x.upper()` used as single-char fallback but
# missing the `len(x) == 1` guard (so it wrongly fires on any all-lowercase
# word, not just length-1 ones).
# --------------------------------------------------------------------------

def _len1_guard_islower(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute)
                and test.func.attr == "islower" and not test.args):
            continue
        val = test.func.value
        if not isinstance(val, ast.Name):
            continue
        varname = val.id
        has_upper = False
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "upper"
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == varname):
                    has_upper = True
        if not has_upper:
            continue
        ts, te = _span(source, test)
        new_test = "len(%s) == 1 and %s" % (varname, source[ts:te])
        out.append(source[:ts] + new_test + source[te:])
    return out


# --------------------------------------------------------------------------
# Generic cheap slips
# --------------------------------------------------------------------------

def _lt_to_le(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 \
           and isinstance(node.ops[0], ast.Lt):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            new_cmp = source[ls:le] + " <= " + source[rs:re_]
            out.append(_splice(source, node, new_cmp))
    return out


def _flip_and_or(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                new_op_text = " or "
            elif isinstance(node.op, ast.Or):
                new_op_text = " and "
            else:
                continue
            # rebuild by joining original value texts with the flipped operator
            parts = []
            for v in node.values:
                vs, ve = _span(source, v)
                parts.append(source[vs:ve])
            new_text = new_op_text.join(parts)
            out.append(_splice(source, node, new_text))
    return out


# --------------------------------------------------------------------------
# Fixer
# --------------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(
                name="capitalize_or_title_to_swapcase",
                apply=_capitalize_title_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="bool_context_case_method_fix",
                apply=_bool_context_case_fix,
                symptoms=("wrong", "err:AttributeError", "err:TypeError"),
            ),
            Rule(
                name="insert_len1_swapcase_shortcut",
                apply=_insert_len1_shortcut,
                symptoms=("wrong",),
            ),
            Rule(
                name="firstupper_restlower_to_swapcase",
                apply=_firstupper_restlower_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="two_print_capitalize_to_swapcase",
                apply=_two_print_capitalize_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_isupper_islower_single",
                apply=_flip_is_case_single,
                symptoms=("wrong",),
            ),
            Rule(
                name="len1_guard_islower_upper_branch",
                apply=_len1_guard_islower,
                symptoms=("wrong",),
            ),
            Rule(
                name="flip_and_or",
                apply=_flip_and_or,
                symptoms=("wrong",),
            ),
            Rule(
                name="lt_to_le",
                apply=_lt_to_le,
                symptoms=("wrong",),
            ),
        ]