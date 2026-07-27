from src.core.repair import Rule
import ast

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
    except SyntaxError:
        return None


def _method_call_rewrite(source, old_name, new_name):
    """Rewrite a bare `X.<old_name>()` call into `X.<new_name>()`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == old_name and not node.args and not node.keywords):
            obj = node.func.value
            os_, oe = _span(source, obj)
            obj_text = source[os_:oe]
            new_call = f"{obj_text}.{new_name}()"
            new_src = _splice(source, node, new_call)
            if new_src != source:
                out.append(new_src)
    return out


def _capitalize_to_swapcase(source):
    """`.capitalize()` used as the case-fix transform should be `.swapcase()`."""
    return _method_call_rewrite(source, "capitalize", "swapcase")


def _capitalize_to_upper(source):
    """`.capitalize()` used to mimic an all-upper check/transform should be `.upper()`."""
    return _method_call_rewrite(source, "capitalize", "upper")


def _title_to_swapcase(source):
    """`.title()` used as the case-fix transform should be `.swapcase()`."""
    return _method_call_rewrite(source, "title", "swapcase")


def _fix_condition_transform_as_check(source):
    """Inside an `if` test, a bare `.upper()`/`.lower()` call (no args) used as a
    boolean check should really be `.isupper()`/`.islower()`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for n2 in ast.walk(node.test):
            if (isinstance(n2, ast.Call) and isinstance(n2.func, ast.Attribute)
                    and n2.func.attr in ("upper", "lower") and not n2.args and not n2.keywords):
                new_attr = "isupper" if n2.func.attr == "upper" else "islower"
                fs, fe = _span(source, n2.func)
                attr_start = fe - len(n2.func.attr)
                new_src = source[:attr_start] + new_attr + source[fe:]
                if new_src != source:
                    out.append(new_src)
    return out


def _wrap_bare_check_attr(source):
    """A bare `X.isupper`/`X.islower` (method reference, never called) used as a
    truthy condition should actually be called: `X.isupper()`/`X.islower()`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    call_func_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            call_func_ids.add(id(node.func))
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr in ("isupper", "islower")
                and id(node) not in call_func_ids):
            s, e = _span(source, node)
            new_src = source[:e] + "()" + source[e:]
            if new_src != source:
                out.append(new_src)
    return out


def _add_len_one_clause(source):
    """An `if` test that checks case-related conditions (isupper/islower/swapcase)
    but forgets the single-letter special case should also accept `len(x) == 1`."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        ts, te = _span(source, test)
        test_src = source[ts:te]
        if "len(" in test_src:
            continue
        if not any(kw in test_src for kw in ("isupper", "islower", "swapcase")):
            continue
        var = None
        for n2 in ast.walk(test):
            if isinstance(n2, ast.Name):
                var = n2.id
                break
        if var is None:
            continue
        new_test = f"({test_src}) or len({var}) == 1"
        new_src = _splice(source, test, new_test)
        if new_src != source:
            out.append(new_src)
    return out


def _add_else_original(source):
    """An `if` (no `else`) that builds a fresh result variable from the input word
    is missing the branch that keeps the word unchanged otherwise."""
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    input_var = None
    for n2 in ast.walk(tree):
        if (isinstance(n2, ast.Assign) and isinstance(n2.value, ast.Call)
                and isinstance(n2.value.func, ast.Name) and n2.value.func.id == "input"
                and n2.targets and isinstance(n2.targets[0], ast.Name)):
            input_var = n2.targets[0].id
            break
    if input_var is None:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and not node.orelse:
            target = None
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and stmt.targets and isinstance(stmt.targets[0], ast.Name):
                    target = stmt.targets[0].id
                    break
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                    target = stmt.target.id
                    break
            if target is None or target == input_var:
                continue
            s, e = _span(source, node)
            indent = " " * node.col_offset
            new_else = f"\n{indent}else:\n{indent}    {target} = {input_var}"
            new_src = source[:e] + new_else + source[e:]
            if new_src != source:
                out.append(new_src)
    return out


class Fixer:
    def rules(self):
        return [
            Rule(
                name="capitalize_to_swapcase",
                apply=_capitalize_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="capitalize_to_upper",
                apply=_capitalize_to_upper,
                symptoms=("wrong",),
            ),
            Rule(
                name="title_to_swapcase",
                apply=_title_to_swapcase,
                symptoms=("wrong",),
            ),
            Rule(
                name="condition_transform_should_be_check",
                apply=_fix_condition_transform_as_check,
                symptoms=("wrong",),
            ),
            Rule(
                name="bare_check_attr_missing_call",
                apply=_wrap_bare_check_attr,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_len_one_clause",
                apply=_add_len_one_clause,
                symptoms=("wrong",),
            ),
            Rule(
                name="missing_else_keep_original",
                apply=_add_else_original,
                symptoms=("wrong", "err:NameError"),
            ),
        ]