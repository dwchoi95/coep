"""Shared helpers for the experiment drivers (data loading, .env, arg parsing)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def load_env(path: str = ".env") -> None:
    """Load KEY=VALUE lines from .env into os.environ (llm.py reads os.environ)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_problem(pid: str, root: str = "data") -> dict:
    return json.loads((Path(root) / pid / "problem.json").read_text())


def load_pool(pid: str, kind: str, root: str = "data") -> list[str]:
    """Read every .py under data/<pid>/<kind> (kind = 'buggy' | 'correct')."""
    d = Path(root) / pid / kind
    return [f.read_text() for f in sorted(d.glob("*.py"))]


def tool_path(pid: str, model: str, root: str = "tools") -> Path:
    from src.core.synthesis import backend_of
    return Path(root) / pid / backend_of(model) / "fixer.py"
