"""Evaluation metrics: functional correctness and relative patch size (RPS).

RPS follows the definition used in APR-for-education work (e.g. Refactory):
token-level tree/sequence edit distance between the buggy program and the
patch, normalized by the size of the buggy program. We use token-sequence
Levenshtein distance over Python lexical tokens.
"""
from __future__ import annotations

import io
import re
import token as tokmod
import tokenize


def tokens_of(source: str) -> list[str]:
    try:
        toks = []
        for t in tokenize.generate_tokens(io.StringIO(source).readline):
            if t.type in (tokmod.NEWLINE, tokmod.NL, tokmod.INDENT, tokmod.DEDENT,
                          tokmod.ENCODING, tokmod.ENDMARKER, tokmod.COMMENT):
                continue
            toks.append(t.string)
        return toks
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        return re.findall(r"\w+|[^\w\s]", source)


def levenshtein(a: list[str], b: list[str]) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def rps(buggy: str, patched: str) -> float:
    """Relative patch size: token edit distance / #tokens of buggy program."""
    tb, tp = tokens_of(buggy), tokens_of(patched)
    if not tb:
        return 1.0
    return levenshtein(tb, tp) / len(tb)
