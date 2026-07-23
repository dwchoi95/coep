"""Parsing helpers for LLM responses."""
from __future__ import annotations

import re

_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_python_block(text: str) -> str | None:
    """Return the largest fenced python code block in `text` (or None)."""
    blocks = _BLOCK.findall(text)
    if not blocks:
        return None
    return max(blocks, key=len).strip() + "\n"
