"""Evaluation metrics: RR, RPS, ATT, InT, OuT, Cost.

RPS follows the *reference implementation* of Refactory (Hu et al., ASE 2019),
not a paraphrase of the paper: patch size is the Zhang-Shasha tree edit
distance between the buggy and repaired ASTs, summed over the union of their
function names, and normalized by the AST node count of the buggy program.

    patch_size = sum_f  TED(AST(buggy.f), AST(repaired.f))     unit relabel cost
    patch_size = 1  if patch_size == 0 but the sources differ
    RPS        = patch_size / max(1, ast_size(buggy))

Node labels replicate Refactory's ``acc_str_node``: identifier / name /
argument / literal when present, else the AST class name, with ``Module``,
``Load`` and ``Store`` collapsed into their parent.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

try:
    from zss import Node, simple_distance
    _HAVE_ZSS = True
except ImportError:  # pragma: no cover - metrics degrade, harness still runs
    _HAVE_ZSS = False


# ------------------------------------------------------------------ RPS
def _label(node: ast.AST) -> str:
    for attr in ("id", "name", "arg"):
        if hasattr(node, attr):
            return str(getattr(node, attr))
    if isinstance(node, ast.Constant):
        v = node.value
        return f"'{v}'" if isinstance(v, str) else str(v)
    cls = node.__class__.__name__
    return "" if cls in ("Module", "Load", "Store") else cls


def _visit(node: ast.AST, parent: "Node") -> None:
    label = _label(node)
    target = parent if label == "" else Node(label)
    if label != "":
        parent.addkid(target)
    for _, value in ast.iter_fields(node):
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, ast.AST):
                _visit(item, target)


def _tree(src: str) -> "Node":
    root = Node("root")
    _visit(ast.parse(src), root)
    return root


def _size(node: "Node") -> int:
    return 1 + sum(_size(k) for k in node.children)


def func_map(src: str) -> dict[str, str]:
    """Top-level functions by name; module-level code under the key ``""``."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out, rest = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = ast.get_source_segment(src, node) or ""
        else:
            seg = ast.get_source_segment(src, node)
            if seg:
                rest.append(seg)
    if rest:
        out[""] = "\n".join(rest)
    return out


def ast_size(src: str) -> int:
    """Node count per Refactory's ``zss_ast_size``.

    The synthetic ``root`` node is *counted*, matching the reference
    implementation (verified against it case by case).
    """
    total = 0
    for code in func_map(src).values():
        try:
            total += _size(_tree(code))
        except SyntaxError:
            continue
    return total


def rps(buggy: str, repaired: str) -> float:
    """Relative patch size, per Refactory's reference implementation."""
    if not _HAVE_ZSS:
        raise RuntimeError("zss is required for RPS; pip install zss")
    a, b = func_map(buggy), func_map(repaired)
    total = 0
    for name in set(a) | set(b):
        ca, cb = a.get(name, ""), b.get(name, "")
        try:
            ta = _tree(ca) if ca.strip() else Node("root")
            tb = _tree(cb) if cb.strip() else Node("root")
        except SyntaxError:
            return 1.0
        total += simple_distance(ta, tb, label_dist=lambda x, y: 0 if x == y else 1)
    if total == 0 and buggy != repaired:
        total = 1
    return total / max(1, ast_size(buggy))


# ------------------------------------------------------------------ tokens
_CHARS_PER_TOKEN = 3.6
MODE = "approx-chars/3.6"

try:  # exact counts when a tokenizer is available offline
    import tiktoken as _tk
    _ENC = _tk.get_encoding("cl100k_base")
    MODE = "tiktoken/cl100k_base"
except Exception:  # pragma: no cover
    _ENC = None


def count_tokens(text: str) -> int:
    if _ENC is not None:
        return len(_ENC.encode(text))
    return int(len(text) / _CHARS_PER_TOKEN + 0.5)


# ------------------------------------------------------------------ cost
PRICES = {  # USD per million tokens, (input, output)
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (1.00, 5.00),        # Claude Haiku 4.5
    "gpt-nano": (0.05, 0.40),            # GPT-5.4-nano  (TODO: confirm vs pricing page)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "qwen2.5-coder-7b-local": (0.0, 0.0),  # self-hosted: measured separately
}
CACHE_READ_MULT, CACHE_WRITE_MULT = 0.1, 1.25


def cost_usd(in_tokens: int, out_tokens: int, model: str = "claude-sonnet",
             cache_read: int = 0, cache_write: int = 0) -> float:
    """Provider-aware billing. Anthropic reports input_tokens EXCLUDING cache
    reads/writes (separate fields, write 1.25x / read 0.1x); OpenAI reports
    prompt_tokens INCLUDING cached_tokens (reads 0.1x, writes free pre-5.6)."""
    pin, pout = PRICES[model]
    if model.startswith("gpt"):
        uncached = max(0, in_tokens - cache_read)
        return ((uncached + cache_read * CACHE_READ_MULT) * pin
                + out_tokens * pout) / 1e6
    return ((in_tokens + cache_read * CACHE_READ_MULT + cache_write * CACHE_WRITE_MULT) * pin
            + out_tokens * pout) / 1e6


# ------------------------------------------------------------------ arm-level
@dataclass
class ArmSummary:
    """Aggregate of one experimental arm over a problem's evaluation set."""
    n: int = 0
    repaired: int = 0
    rps_sum: float = 0.0
    seconds_sum: float = 0.0
    in_tokens: int = 0
    out_tokens: int = 0
    usd: float = 0.0

    def add(self, repaired: bool, seconds: float, patch_rps: float | None = None,
            in_tokens: int = 0, out_tokens: int = 0, usd: float = 0.0) -> None:
        self.n += 1
        self.seconds_sum += seconds
        self.in_tokens += in_tokens
        self.out_tokens += out_tokens
        self.usd += usd
        if repaired:
            self.repaired += 1
            if patch_rps is not None:
                self.rps_sum += patch_rps

    @property
    def RR(self) -> float:
        """Repair rate (%): fraction of evaluation programs repaired."""
        return 100.0 * self.repaired / self.n if self.n else 0.0

    @property
    def RPS(self) -> float:
        """Mean relative patch size over repaired programs."""
        return self.rps_sum / self.repaired if self.repaired else 0.0

    @property
    def ATT(self) -> float:
        """Average time taken per buggy program, end to end (local + API), sec."""
        return self.seconds_sum / self.n if self.n else 0.0

    @property
    def InT(self) -> float:
        return self.in_tokens / self.n if self.n else 0.0

    @property
    def OuT(self) -> float:
        return self.out_tokens / self.n if self.n else 0.0

    @property
    def Cost(self) -> float:
        """USD per buggy program."""
        return self.usd / self.n if self.n else 0.0

    def as_dict(self) -> dict:
        return {"n": self.n, "RR": round(self.RR, 2), "RPS": round(self.RPS, 4),
                "ATT": round(self.ATT, 3), "InT": round(self.InT, 1),
                "OuT": round(self.OuT, 1), "Cost": self.Cost}


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (100 * max(0.0, c - h), 100 * min(1.0, c + h))
