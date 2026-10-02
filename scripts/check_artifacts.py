#!/usr/bin/env python3
"""CI gate for a repository with no test suite: keep the public artifacts honest.

This repo publishes offline results and reports rather than a library, so the
things that can actually break are (a) a script that no longer compiles, (b) a
committed JSON artifact that no longer parses, and (c) a documented offline
command that no longer runs. Everything here is offline and needs no credentials.

    python3 scripts/check_artifacts.py
    python3 scripts/run_baselines.py --json   # the README's offline command

Exit code 0 means every public artifact is still readable and every script still
compiles.
"""

from __future__ import annotations

import json
import pathlib
import py_compile
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    failures: list[str] = []

    scripts = sorted((ROOT / "scripts").glob("*.py"))
    for path in scripts:
        try:
            py_compile.compile(str(path), doraise=True, cfile=str(path) + ".pyc")
        except py_compile.PyCompileError as exc:
            failures.append(f"compile: {path.relative_to(ROOT)}: {exc.msg}")
        finally:
            pyc = pathlib.Path(str(path) + ".pyc")
            if pyc.exists():
                pyc.unlink()

    artifacts = sorted((ROOT / "results").rglob("*.json"))
    for path in artifacts:
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            failures.append(f"json: {path.relative_to(ROOT)}: {exc}")

    # the README's offline reproduction command, run from a clean cwd
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_baselines.py")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        failures.append(f"run_baselines.py exited {proc.returncode}: {proc.stderr.strip()[:300]}")

    print(f"scripts compiled : {len(scripts)}")
    print(f"json artifacts   : {len(artifacts)}")
    print(f"offline baseline : {'ok' if proc.returncode == 0 else 'FAILED'}")
    if failures:
        print()
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
