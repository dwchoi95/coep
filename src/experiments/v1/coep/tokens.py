"""Token counting for cost accounting.

Uses tiktoken's cl100k_base as a model-agnostic proxy tokenizer (offline,
deterministic). If the encoding files are unavailable, falls back to a
chars/3.6 heuristic; the active mode is recorded so results state which
counter produced them.
"""
from __future__ import annotations

_enc = None
MODE = "approx-chars/3.6"
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    MODE = "tiktoken-cl100k_base"
except Exception:
    _enc = None


def count(text: str) -> int:
    if _enc is not None:
        return len(_enc.encode(text, disallowed_special=()))
    return max(1, round(len(text) / 3.6))
