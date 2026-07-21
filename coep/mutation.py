"""AST-based mutation engine for generating buggy program variants.

Implements a taxonomy of common novice-programmer faults (operator misuse,
off-by-one, wrong boolean logic, bad initialization, boundary errors, swapped
arguments). Mutations are enumerated deterministically over the AST; a seeded
RNG selects which sites to mutate, so benchmark generation is reproducible.
"""
from __future__ import annotations

import ast
import copy
import random

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
            ast.FloorDiv: ast.Mult, ast.Mod: ast.FloorDiv}
BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


def _sites(tree: ast.AST) -> list[tuple[str, int]]:
    """Enumerate mutation sites as (kind, occurrence_index) pairs."""
    sites = []
    counters: dict[str, int] = {}

    def emit(kind: str):
        i = counters.get(kind, 0)
        counters[kind] = i + 1
        sites.append((kind, i))

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMP_SWAP:
            emit("cmp")
        if isinstance(node, ast.BinOp) and type(node.op) in BIN_SWAP:
            emit("bin")
        if isinstance(node, ast.BoolOp) and type(node.op) in BOOL_SWAP:
            emit("bool")
        if isinstance(node, ast.AugAssign) and type(node.op) in BIN_SWAP:
            emit("aug")
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            emit("int+1")
            emit("int-1")
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            emit("boolconst")
        if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.expr)
                and not isinstance(node.slice, ast.Slice)):
            emit("idx")
        if isinstance(node, ast.Call) and len(node.args) == 2 and not node.keywords:
            emit("swapargs")
    return sites


class _Mutator(ast.NodeTransformer):
    def __init__(self, targets: set[tuple[str, int]]):
        self.targets = targets
        self.counters: dict[str, int] = {}

    def _hit(self, kind: str) -> bool:
        i = self.counters.get(kind, 0)
        self.counters[kind] = i + 1
        return (kind, i) in self.targets

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in CMP_SWAP and self._hit("cmp"):
            node.ops[0] = CMP_SWAP[type(node.ops[0])]()
        return node

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in BIN_SWAP and self._hit("bin"):
            node.op = BIN_SWAP[type(node.op)]()
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if type(node.op) in BOOL_SWAP and self._hit("bool"):
            node.op = BOOL_SWAP[type(node.op)]()
        return node

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        if type(node.op) in BIN_SWAP and self._hit("aug"):
            node.op = BIN_SWAP[type(node.op)]()
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, bool):
            if self._hit("boolconst"):
                return ast.Constant(value=not node.value)
            return node
        if isinstance(node.value, int):
            plus = self._hit("int+1")
            minus = self._hit("int-1")
            if plus:
                return ast.Constant(value=node.value + 1)
            if minus:
                return ast.Constant(value=node.value - 1)
        return node

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if (isinstance(node.slice, ast.expr) and not isinstance(node.slice, ast.Slice)
                and self._hit("idx")):
            node.slice = ast.BinOp(left=node.slice, op=ast.Add(), right=ast.Constant(value=1))
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if len(node.args) == 2 and not node.keywords and self._hit("swapargs"):
            node.args = [node.args[1], node.args[0]]
        return node


def mutate(source: str, targets: list[tuple[str, int]]) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    mutated = _Mutator(set(targets)).visit(copy.deepcopy(tree))
    ast.fix_missing_locations(mutated)
    try:
        return ast.unparse(mutated)
    except Exception:
        return None


def generate_mutants(source: str, n_wanted: int, rng: random.Random,
                     max_faults: int = 2, max_attempts: int = 400) -> list[dict]:
    """Generate up to n_wanted syntactically-valid distinct mutants.

    Returns dicts {source, faults, sites}; caller must still filter for
    'actually fails at least one test'.
    """
    tree = ast.parse(source)
    sites = _sites(tree)
    if not sites:
        return []
    seen = {source}
    out = []
    for _ in range(max_attempts):
        if len(out) >= n_wanted:
            break
        k = 1 if rng.random() < 0.7 else min(max_faults, 2)
        chosen = rng.sample(sites, k=min(k, len(sites)))
        m = mutate(source, chosen)
        if m is None or m in seen:
            continue
        try:
            compile(m, "<mutant>", "exec")
        except SyntaxError:
            continue
        seen.add(m)
        out.append({"source": m, "faults": len(chosen), "sites": chosen})
    return out
