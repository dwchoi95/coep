#!/usr/bin/env python3
"""CoEP entrypoint.

Dispatch only: every subcommand forwards to a driver in ``src/experiments/``.
No experiment logic lives here, so drivers stay independently runnable and
testable.

    python run.py build    --problem refactory_q1 [--model claude-sonnet-5 gpt-5.4-mini]
    python run.py repair   --problem refactory_q1 --model claude-sonnet-5 --file bug.py
    python run.py evaluate --problem refactory_q1 --model claude-sonnet-5 [--fallback --learn]
    python run.py --list
"""
from __future__ import annotations

import argparse
import importlib
import sys

# subcommand -> (module under src.experiments, entry function)
COMMANDS = {
    "build": ("build", "main"),        # synthesize tools/<p_id>/<model>/fixer.py
    "repair": ("repair", "main"),      # repair one submission (tool + fallback)
    "evaluate": ("evaluate", "main"),  # single-arm evaluation
    "compare": ("compare", "main"),    # one pass, CoEP_L and CoEP_LF
    "stats": ("stats_report", "main"),  # Wilson intervals + exact McNemar
    "tables": ("tables", "main"),       # regenerate the paper's LaTeX bodies
    "numbers": ("numbers", "main"),     # regenerate paper/numbers.tex
    "figures": ("figures", "main"),     # regenerate paper/figures/*.pdf
    "pydex": ("pydex_run", "main"),    # PyDex + PyDex_PC baseline arms
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="run.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=sorted(COMMANDS),
                    help="stage to run")
    ap.add_argument("--list", action="store_true", help="list available drivers")
    args, rest = ap.parse_known_args(argv)

    if args.list or not args.command:
        print("commands:")
        for name, (mod, fn) in sorted(COMMANDS.items()):
            status = "ready" if _importable(mod) else "not implemented yet"
            print(f"  {name:9s} -> src/experiments/{mod}.py:{fn}  [{status}]")
        return 0

    mod_name, fn_name = COMMANDS[args.command]
    try:
        mod = importlib.import_module(f"src.experiments.{mod_name}")
    except ModuleNotFoundError:
        print(f"driver src/experiments/{mod_name}.py does not exist yet",
              file=sys.stderr)
        return 2
    return int(getattr(mod, fn_name)(rest) or 0)


def _importable(mod: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(f"src.experiments.{mod}") is not None


if __name__ == "__main__":
    raise SystemExit(main())
