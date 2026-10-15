"""
Repair module for the "Duplicate elimination" (remove_extras) assignment.

Each Rule below targets one structural misconception observed across the
buggy submissions and performs a small, local, AST-span based text edit.
Rules are pure candidate generators: they never mutate state and never
claim correctness themselves -- the harness validates candidates.
"""

import ast

from src.core.repair import Rule


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------

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


def _unwrap_index(node):
    """Handle the (removed) ast.Index wrapper used on old Pythons."""
    idx_t = getattr(ast, "Index", None)
    if idx_t is not None and isinstance(node, idx_t):
        return node.value
    return node


def _safe_parse(source):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ----------------------------------------------------------------------
# Rule: swapped for-loop header (target/iter reversed, shadowing a name)
#   for lst in new_lst:        ->   for i in lst:
#       if i not in lst:                 if i not in lst:
#           new_lst += [i,]                   new_lst += [i,]
# ----------------------------------------------------------------------

def _find_swapped_header(node):
    if not (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
            and isinstance(node.iter, ast.Name)):
        return None
    T = node.target.id
    ACC = node.iter.id
    if T == ACC:
        return None
    for cmp in ast.walk(node):
        if isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 \
           and isinstance(cmp.ops[0], (ast.In, ast.NotIn)):
            left = cmp.left
            right = cmp.comparators[0]
            if isinstance(right, ast.Name) and right.id == T \
               and isinstance(left, ast.Name) and left.id != T and left.id != ACC:
                V = left.id
                for s2 in ast.walk(node):
                    if isinstance(s2, ast.AugAssign) and isinstance(s2.target, ast.Name) \
                       and s2.target.id == ACC:
                        return V, T
                    if isinstance(s2, ast.Call) and isinstance(s2.func, ast.Attribute) \
                       and s2.func.attr == "append" and isinstance(s2.func.value, ast.Name) \
                       and s2.func.value.id == ACC:
                        return V, T
    return None


def swapped_for_header(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            m = _find_swapped_header(node)
            if m:
                V, T = m
                t_s, t_e = _span(source, node.target)
                i_s, i_e = _span(source, node.iter)
                new_src = source[:t_s] + V + source[t_e:i_s] + T + source[i_e:]
                out.append(new_src)
    return out


# ----------------------------------------------------------------------
# Rule: membership test checks container/iterable name instead of the
# loop variable: `for i in lst: if lst not in new_lst:` -> `if i not in ...`
# ----------------------------------------------------------------------

def wrong_name_in_membership_test(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name) \
           and isinstance(node.iter, ast.Name):
            T = node.target.id
            SRC = node.iter.id
            if T == SRC:
                continue
            for cmp in ast.walk(node):
                if isinstance(cmp, ast.Compare) and len(cmp.ops) == 1 \
                   and isinstance(cmp.ops[0], (ast.In, ast.NotIn)):
                    left = cmp.left
                    if isinstance(left, ast.Name) and left.id == SRC:
                        s, e = _span(source, left)
                        out.append(source[:s] + T + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: function returns the original parameter instead of the
# accumulator it built.
# ----------------------------------------------------------------------

def return_wrong_variable(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = {a.arg for a in fn.args.args}
        acc = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
               and node.func.attr == "append" and isinstance(node.func.value, ast.Name):
                acc.add(node.func.value.id)
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                acc.add(node.target.id)
        acc -= params
        if len(acc) != 1:
            continue
        accumulator = next(iter(acc))
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) \
               and node.value.id in params:
                s, e = _span(source, node.value)
                out.append(source[:s] + accumulator + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: method call written with brackets instead of parentheses, e.g.
# result.append[element]  -> result.append(element)
# ----------------------------------------------------------------------

def bracket_call_to_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            if node.value.attr in ("append", "count", "remove", "add"):
                val_s, val_e = _span(source, node.value)
                idx = _unwrap_index(node.slice)
                idx_s, idx_e = _span(source, idx)
                full_s, full_e = _span(source, node)
                new_text = source[full_s:val_e] + "(" + source[idx_s:idx_e] + ")"
                out.append(source[:full_s] + new_text + source[full_e:])
    return out


# ----------------------------------------------------------------------
# Rule: `acc += loop_var` should wrap the element in a list:
# `acc += [loop_var]`
# ----------------------------------------------------------------------

def missing_list_wrap_augassign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            loop_var = node.target.id
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add) \
                   and isinstance(stmt.value, ast.Name) and stmt.value.id == loop_var:
                    s, e = _span(source, stmt.value)
                    out.append(source[:s] + "[" + loop_var + "]" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: accumulator seeded from the first element (`[x[0]]` / `(x[0],)`)
# causing an off-by-one / IndexError-on-empty bug. Reset the seed to an
# empty collection (always also offer a plain `[]` candidate so a
# downstream tuple->list fix stays type-consistent).
# ----------------------------------------------------------------------

def seed_from_index_zero(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.List, ast.Tuple)) \
           and len(node.value.elts) == 1:
            elt = node.value.elts[0]
            if isinstance(elt, ast.Subscript):
                idx = _unwrap_index(elt.slice)
                if isinstance(idx, ast.Constant) and idx.value == 0:
                    if isinstance(node.value, ast.List):
                        out.append(_splice(source, node.value, "[]"))
                    else:
                        out.append(_splice(source, node.value, "()"))
                        out.append(_splice(source, node.value, "[]"))
    return out


# ----------------------------------------------------------------------
# Rule: tuple-based "concatenation" accumulator (`seq = seq + (x,)`)
# converted to list concatenation.
# ----------------------------------------------------------------------

def tuple_concat_to_list(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            right = node.right
            if isinstance(right, ast.Tuple) and len(right.elts) >= 1:
                parts = []
                for e in right.elts:
                    s, ee = _span(source, e)
                    parts.append(source[s:ee])
                new_list = "[" + ", ".join(parts) + "]"
                out.append(_splice(source, right, new_list))
    return out


# ----------------------------------------------------------------------
# Rule: `x = y.copy` missing call parentheses.
# ----------------------------------------------------------------------

def copy_missing_call(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) \
           and node.value.attr == "copy":
            s, e = _span(source, node.value)
            out.append(source[:e] + "()" + source[e:])
    return out


# ----------------------------------------------------------------------
# Rule: a bare `a == b` statement that should be an assignment
# (misconception: `==` instead of `=`).
# ----------------------------------------------------------------------

def eq_statement_to_assign(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Compare):
            cmp = node.value
            if len(cmp.ops) == 1 and isinstance(cmp.ops[0], ast.Eq):
                ls, le = _span(source, cmp.left)
                rs, re_ = _span(source, cmp.comparators[0])
                new_stmt = source[ls:le] + " = " + source[rs:re_]
                out.append(_splice(source, node, new_stmt))
    return out


# ----------------------------------------------------------------------
# Rule: `x = x.append(y)` reassigns the accumulator to None (append's
# return value). Drop the reassignment, keep the bare call.
# ----------------------------------------------------------------------

def drop_append_reassignment(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
            val = node.value
            if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) \
               and val.func.attr == "append" and isinstance(val.func.value, ast.Name) \
               and val.func.value.id == tgt:
                vs, ve = _span(source, val)
                out.append(_splice(source, node, source[vs:ve]))
    return out


# ----------------------------------------------------------------------
# Rule: while-loop that rebuilds the list by filtering out ALL
# occurrences of the current element instead of keeping the first one.
# Insert a "kept" flag so only later duplicates are skipped.
# ----------------------------------------------------------------------

def _is_append_like(stmt):
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        f = stmt.value.func
        if isinstance(f, ast.Attribute) and f.attr == "append":
            return True
    return False


def _match_filter_all(for_node):
    body = for_node.body
    for idx, stmt in enumerate(body):
        if isinstance(stmt, ast.If) and len(stmt.body) == 1 \
           and isinstance(stmt.body[0], ast.Continue):
            test = stmt.test
            if isinstance(test, ast.Compare) and len(test.ops) == 1 \
               and isinstance(test.ops[0], ast.Eq):
                if idx + 1 < len(body) and _is_append_like(body[idx + 1]):
                    return stmt
    return None


def filter_all_duplicates_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        for inner in node.body:
            if isinstance(inner, ast.For):
                if_stmt = _match_filter_all(inner)
                if if_stmt is None:
                    continue
                flag = "_dedup_kept"
                if flag in source:
                    flag = "_dedup_kept_x"
                indent = " " * if_stmt.col_offset
                ts, te = _span(source, if_stmt.test)
                test_src = source[ts:te]
                new_if = (
                    "if " + test_src + ":\n"
                    + indent + "    if " + flag + ":\n"
                    + indent + "        continue\n"
                    + indent + "    " + flag + " = True"
                )
                inner_s, _inner_e = _span(source, inner)
                if_s, if_e = _span(source, if_stmt)
                init_line = flag + " = False\n" + " " * inner.col_offset
                new_source = (source[:inner_s] + init_line
                              + source[inner_s:if_s] + new_if + source[if_e:])
                out.append(new_source)
    return out


# ----------------------------------------------------------------------
# Rule: double nested loop that mutates `lst` with `.remove()` while
# iterating a suffix slice -- fundamentally unsound. Replace with a
# reverse index scan that checks only the earlier slice.
# ----------------------------------------------------------------------

def _match_range_len_minus_1(iter_node):
    if not (isinstance(iter_node, ast.Call) and isinstance(iter_node.func, ast.Name)
            and iter_node.func.id == "range" and len(iter_node.args) == 1):
        return None
    arg = iter_node.args[0]
    if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub)
            and isinstance(arg.right, ast.Constant) and arg.right.value == 1):
        return None
    lenc = arg.left
    if not (isinstance(lenc, ast.Call) and isinstance(lenc.func, ast.Name)
            and lenc.func.id == "len" and len(lenc.args) == 1
            and isinstance(lenc.args[0], ast.Name)):
        return None
    return lenc.args[0].id


def _match_double_remove(outer):
    if not (isinstance(outer, ast.For) and isinstance(outer.target, ast.Name)):
        return None
    I = outer.target.id
    LST = _match_range_len_minus_1(outer.iter)
    if LST is None:
        return None
    inner = None
    for stmt in outer.body:
        if isinstance(stmt, ast.For):
            inner = stmt
            break
    if inner is None or not isinstance(inner.target, ast.Name):
        return None
    J = inner.target.id
    iiter = inner.iter
    if not (isinstance(iiter, ast.Subscript) and isinstance(iiter.value, ast.Name)
            and iiter.value.id == LST):
        return None
    sl = _unwrap_index(iiter.slice)
    if not (isinstance(sl, ast.Slice) and sl.upper is None and sl.lower is not None):
        return None
    low = sl.lower
    if not (isinstance(low, ast.BinOp) and isinstance(low.op, ast.Add)
            and isinstance(low.left, ast.Name) and low.left.id == I
            and isinstance(low.right, ast.Constant) and low.right.value == 1):
        return None
    if_stmt = None
    for stmt in inner.body:
        if isinstance(stmt, ast.If):
            if_stmt = stmt
            break
    if if_stmt is None:
        return None
    test = if_stmt.test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)):
        return None
    left, right = test.left, test.comparators[0]
    if not (isinstance(left, ast.Name) and left.id == J):
        return None
    if not (isinstance(right, ast.Subscript) and isinstance(right.value, ast.Name)
            and right.value.id == LST):
        return None
    rsl = _unwrap_index(right.slice)
    if not (isinstance(rsl, ast.Name) and rsl.id == I):
        return None
    for s2 in if_stmt.body:
        if isinstance(s2, ast.Expr) and isinstance(s2.value, ast.Call):
            f = s2.value.func
            if isinstance(f, ast.Attribute) and f.attr == "remove" \
               and isinstance(f.value, ast.Name) and f.value.id == LST:
                args = s2.value.args
                if len(args) == 1 and isinstance(args[0], ast.Name) and args[0].id == J:
                    return LST, I
    return None


def nested_double_remove_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            m = _match_double_remove(node)
            if m:
                LST, I = m
                indent = " " * node.col_offset
                new_code = (
                    "for " + I + " in range(len(" + LST + ") - 1, -1, -1):\n"
                    + indent + "    if " + LST + "[" + I + "] in " + LST + "[:" + I + "]:\n"
                    + indent + "        " + LST + ".pop(" + I + ")"
                )
                out.append(_splice(source, node, new_code))
    return out


# ----------------------------------------------------------------------
# Rule: single loop that checks membership against the WHOLE list minus
# current index (`lst[:i] + lst[i+1:]`) and pops in forward order. Fix:
# check only the earlier slice and scan indices in reverse order.
# ----------------------------------------------------------------------

def _is_lower_slice(n, LST, I):
    if not (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == LST):
        return False
    sl = _unwrap_index(n.slice)
    return isinstance(sl, ast.Slice) and sl.lower is None \
        and isinstance(sl.upper, ast.Name) and sl.upper.id == I


def _is_upper_slice(n, LST, I):
    if not (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == LST):
        return False
    sl = _unwrap_index(n.slice)
    return isinstance(sl, ast.Slice) and sl.upper is None \
        and isinstance(sl.lower, ast.BinOp) and isinstance(sl.lower.op, ast.Add) \
        and isinstance(sl.lower.left, ast.Name) and sl.lower.left.id == I


def _match_slice_offby(outer):
    if not (isinstance(outer, ast.For) and isinstance(outer.target, ast.Name)):
        return None
    I = outer.target.id
    LST = _match_range_len_minus_1(outer.iter)
    if LST is None:
        return None
    if_stmt = None
    for stmt in outer.body:
        if isinstance(stmt, ast.If):
            if_stmt = stmt
            break
    if if_stmt is None:
        return None
    test = if_stmt.test
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], ast.In)):
        return None
    left = test.left
    if not (isinstance(left, ast.Subscript) and isinstance(left.value, ast.Name)
            and left.value.id == LST):
        return None
    lsl = _unwrap_index(left.slice)
    if not (isinstance(lsl, ast.Name) and lsl.id == I):
        return None
    right = test.comparators[0]
    if not (isinstance(right, ast.BinOp) and isinstance(right.op, ast.Add)):
        return None
    a, b = right.left, right.right
    if not (_is_lower_slice(a, LST, I) and _is_upper_slice(b, LST, I)):
        return None
    return LST, I, right


def slice_membership_offbyone_fix(source):
    tree = _safe_parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            m = _match_slice_offby(node)
            if m:
                LST, I, right = m
                arg = node.iter.args[0]
                _arg_s, arg_e = _span(source, arg)
                right_s, right_e = _span(source, right)
                left_s, left_e = _span(source, right.left)
                lower_text = source[left_s:left_e]
                edits = [
                    (arg_e, arg_e, ", -1, -1"),
                    (right_s, right_e, lower_text),
                ]
                edits.sort(key=lambda t: t[0], reverse=True)
                new_source = source
                for s, e, rep in edits:
                    new_source = new_source[:s] + rep + new_source[e:]
                out.append(new_source)
    return out


# ----------------------------------------------------------------------

class Fixer:
    def rules(self):
        return [
            Rule(name="swapped_for_header", apply=swapped_for_header,
                 symptoms=("wrong", "timeout")),
            Rule(name="wrong_name_in_membership_test", apply=wrong_name_in_membership_test,
                 symptoms=("wrong",)),
            Rule(name="return_wrong_variable", apply=return_wrong_variable,
                 symptoms=("wrong",)),
            Rule(name="bracket_call_to_call", apply=bracket_call_to_call,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="missing_list_wrap_augassign", apply=missing_list_wrap_augassign,
                 symptoms=("wrong", "err:TypeError")),
            Rule(name="seed_from_index_zero", apply=seed_from_index_zero,
                 symptoms=("wrong", "err:IndexError")),
            Rule(name="tuple_concat_to_list", apply=tuple_concat_to_list,
                 symptoms=("wrong",)),
            Rule(name="copy_missing_call", apply=copy_missing_call,
                 symptoms=("err:AttributeError", "err:TypeError", "wrong")),
            Rule(name="eq_statement_to_assign", apply=eq_statement_to_assign,
                 symptoms=("err:TypeError", "wrong")),
            Rule(name="drop_append_reassignment", apply=drop_append_reassignment,
                 symptoms=("wrong",)),
            Rule(name="filter_all_duplicates_fix", apply=filter_all_duplicates_fix,
                 symptoms=("wrong",)),
            Rule(name="nested_double_remove_fix", apply=nested_double_remove_fix,
                 symptoms=("wrong",)),
            Rule(name="slice_membership_offbyone_fix", apply=slice_membership_offbyone_fix,
                 symptoms=("wrong",)),
        ]