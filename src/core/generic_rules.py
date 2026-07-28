"""A shared library of generic small-edit repair operators.

Every tool includes these regardless of what the builder wrote, so the common
CS1 slips — a strict/non-strict comparison, an off-by-one on a ``range`` bound,
an index shifted by one — are always covered even when the build sample happened
not to show them. These are pure *candidate generators*: each emits edited
program sources, and the harness validates them against the tests. They locate on
the AST and splice on the original source (no ``ast.unparse``), like the builder
rules: the always-on operators every synthesized tool carries.
"""
from __future__ import annotations

import ast

from src.core.repair import Rule


def _span(source: str, node: ast.AST) -> tuple[int, int]:
    lines = source.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    return (starts[node.lineno - 1] + node.col_offset,
            starts[node.end_lineno - 1] + node.end_col_offset)


def _seg(source: str, node: ast.AST) -> str:
    s, e = _span(source, node)
    return source[s:e]


def _parse(source: str):
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# --------------------------------------------------------------- comparison flip
# adjacent comparison operators worth trying as one-token slips
_CMP = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
        ast.Eq: "==", ast.NotEq: "!="}
_FLIP = {
    ast.Lt: ["<=", ">"], ast.LtE: ["<", ">="],
    ast.Gt: [">=", "<"], ast.GtE: [">", "<="],
    ast.Eq: ["!=", "<=", ">="], ast.NotEq: ["=="],
}


def flip_compare(source: str) -> list[str]:
    """Swap a single comparison operator to an adjacent one (``<``↔``<=``, …)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and type(node.ops[0]) in _FLIP):
            left, right = node.left, node.comparators[0]
            ls, le = _span(source, left)
            rs, re_ = _span(source, right)
            s, e = _span(source, node)
            for op in _FLIP[type(node.ops[0])]:
                out.append(source[:s] + f"{source[ls:le]} {op} {source[rs:re_]}"
                           + source[e:])
    return out


# --------------------------------------------------------------- range bounds
def _replace(source: str, node: ast.AST, new: str) -> str:
    s, e = _span(source, node)
    return source[:s] + new + source[e:]


def shift_range(source: str) -> list[str]:
    """Nudge a ``range(...)`` bound by one, the classic loop off-by-one."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "range" and node.args):
            continue
        stop = node.args[-1]                       # the exclusive bound
        seg = _seg(source, stop)
        for delta in (" - 1", " + 1"):
            out.append(_replace(source, stop, f"({seg}){delta}"))
        # range(a, b) <-> range(b): try dropping a leading 0/1 start
        if len(node.args) == 2 and _seg(source, node.args[0]) in ("0", "1"):
            out.append(_replace(source, node, f"range({_seg(source, stop)})"))
    return out


# --------------------------------------------------------------- index shift
def shift_index(source: str) -> list[str]:
    """Shift a subscript index by one (``seq[i]`` ↔ ``seq[i+1]`` / ``seq[i-1]``)."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        idx = node.slice
        if isinstance(idx, ast.Slice):             # not a scalar index
            continue
        seg = _seg(source, idx)
        # if it is already i+1 / i-1, also try the bare form
        variants = [f"({seg}) - 1", f"({seg}) + 1"]
        if isinstance(idx, ast.BinOp) and isinstance(idx.op, (ast.Add, ast.Sub)):
            variants.append(_seg(source, idx.left))
        for v in variants:
            out.append(_replace(source, idx, v))
    return out


# --------------------------------------------------------------- boolean op
def flip_bool_op(source: str) -> list[str]:
    """Swap ``and`` ↔ ``or`` in a single boolean expression."""
    tree = _parse(source)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            s, e = _span(source, node)
            seg = source[s:e]
            if isinstance(node.op, ast.And) and " and " in seg:
                out.append(source[:s] + seg.replace(" and ", " or ", 1) + source[e:])
            elif isinstance(node.op, ast.Or) and " or " in seg:
                out.append(source[:s] + seg.replace(" or ", " and ", 1) + source[e:])
    return out


def generic_rules() -> list[Rule]:
    """The always-on small-edit operators, ordered cheapest-first."""
    return [
        Rule("generic_flip_compare", flip_compare, symptoms=("wrong",)),
        Rule("generic_shift_range", shift_range, symptoms=("wrong", "err:IndexError")),
        Rule("generic_shift_index", shift_index, symptoms=("wrong", "err:IndexError")),
        Rule("generic_flip_bool_op", flip_bool_op, symptoms=("wrong",)),
    ]
