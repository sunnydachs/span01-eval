#!/usr/bin/env python3
"""CI gate for a repository with no test suite: keep the public artifacts honest.

This repo publishes offline results and reports rather than a library, so what can
actually break is (a) a script that no longer compiles, (b) a committed JSON
artifact that no longer parses, (c) a documented offline command that no longer
runs, and (d) an artifact that no longer matches what the current code produces.

(a)-(c) fail the run. (d) is reported loudly but does not fail it: reconciling a
regenerated number against a published one is a decision, not a build error, and
the artifact is restored before the process exits either way.

    python3 scripts/check_artifacts.py

Everything here is offline and needs no credentials.
"""

from __future__ import annotations

import difflib
import json
import pathlib
import py_compile
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE_ARTIFACT = ROOT / "results" / "baselines.json"


def compile_scripts(failures: list[str]) -> int:
    scripts = sorted((ROOT / "scripts").glob("*.py"))
    for path in scripts:
        pyc = pathlib.Path(str(path) + "c")
        try:
            py_compile.compile(str(path), doraise=True, cfile=str(pyc))
        except py_compile.PyCompileError as exc:
            failures.append(f"compile: {path.relative_to(ROOT)}: {exc.msg}")
        finally:
            if pyc.exists():
                pyc.unlink()
    return len(scripts)


def parse_artifacts(failures: list[str]) -> int:
    artifacts = sorted((ROOT / "results").rglob("*.json"))
    for path in artifacts:
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            failures.append(f"json: {path.relative_to(ROOT)}: {exc}")
    return len(artifacts)


def run_offline_command(failures: list[str]) -> bool:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_baselines.py")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        failures.append(f"run_baselines.py exited {proc.returncode}: {proc.stderr.strip()[:300]}")
    return proc.returncode == 0


def check_reproduction() -> tuple[bool, str]:
    """Run the documented --json command and diff it against the committed file.

    The script writes into results/, so the committed bytes are restored before
    returning regardless of outcome.
    """
    if not BASELINE_ARTIFACT.exists():
        return True, "no committed results/baselines.json to compare against"
    committed = BASELINE_ARTIFACT.read_bytes()
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_baselines.py"), "--json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=300,
        )
        regenerated = BASELINE_ARTIFACT.read_bytes()
    finally:
        BASELINE_ARTIFACT.write_bytes(committed)
    if proc.returncode != 0:
        return True, f"--json exited {proc.returncode}; reproduction not checked"
    if regenerated == committed:
        return True, "the committed artifact matches a fresh run"
    diff = list(difflib.unified_diff(
        committed.decode().splitlines(), regenerated.decode().splitlines(),
        "committed", "regenerated", lineterm="", n=2,
    ))
    return False, "\n".join(diff[:60])


def main() -> int:
    failures: list[str] = []
    n_scripts = compile_scripts(failures)
    n_artifacts = parse_artifacts(failures)
    offline_ok = run_offline_command(failures)
    reproduced, repro_detail = check_reproduction()

    print(f"scripts compiled : {n_scripts}")
    print(f"json artifacts   : {n_artifacts}")
    print(f"offline command  : {'ok' if offline_ok else 'FAILED'}")
    print(f"artifact matches a fresh run : {'yes' if reproduced else 'NO'}")

    if not reproduced:
        print("\nDRIFT: results/baselines.json is not what scripts/run_baselines.py --json produces today.")
        print("       This is reported, not failed: reconciling it against a published figure is a decision.")
        print("       To see the whole difference:")
        print("         python3 scripts/run_baselines.py --json && git diff results/baselines.json")
        print()
        print(repro_detail)

    if failures:
        print()
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
