#!/usr/bin/env python3
"""Run one problem's repairer on one buggy file; print a JSON result.

Executed as a subprocess by the evaluation harness so that a slow or crashing
repairer cannot take down the run. Usage:
    python3 scripts/run_repairer_one.py <pid> <bug_filename>
"""
import importlib.util
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

pid, bug = sys.argv[1], sys.argv[2]
pdir = ROOT / "benchmark" / "problems" / pid
source = (pdir / "buggy" / bug).read_text()

import os
spec = importlib.util.spec_from_file_location(f"repairer_{pid}", pdir / os.environ.get("COEP_REPAIRER", "repairer.py"))
mod = importlib.util.module_from_spec(spec)
t0 = time.monotonic()
try:
    spec.loader.exec_module(mod)
    patched = mod.repair(source)
    err = None
except BaseException as e:  # noqa: BLE001
    patched, err = None, f"{type(e).__name__}: {e}"
print(json.dumps({"patched": patched, "seconds": round(time.monotonic() - t0, 2),
                  "error": err}))
