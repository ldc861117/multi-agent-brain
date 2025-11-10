#!/usr/bin/env python3
"""Utility helpers for inspecting and running the consolidated pytest suite."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_TESTS: Sequence[Path] = (
    Path("tests/unit/test_env_config.py"),
    Path("tests/unit/test_openai_client.py"),
    Path("tests/unit/test_shared_memory.py"),
)


def _count_items(path: Path) -> tuple[int, int]:
    source = path.read_text(encoding="utf-8")
    classes = re.findall(r"^\s*class\s+(Test\w+)", source, flags=re.MULTILINE)
    methods = re.findall(r"^\s*def\s+(test_[\w_]+)", source, flags=re.MULTILINE)
    return len(classes), len(methods)


def _print_overview(test_files: Iterable[Path]) -> None:
    print("=== Test Suite Overview ===\n")
    for path in test_files:
        status = "✅" if path.exists() else "❌"
        print(f"{status} {path}")
        if not path.exists():
            continue
        size = path.stat().st_size
        classes, methods = _count_items(path)
        print(f"    size: {size:,} bytes")
        print(f"    classes: {classes}")
        print(f"    tests: {methods}\n")


def _run_pytest(targets: Sequence[Path], extra_args: Sequence[str]) -> int:
    args = [sys.executable, "-m", "pytest"]
    if targets:
        args.extend(str(path) for path in targets)
    args.extend(extra_args)
    print("Executing:", " ".join(args))
    completed = subprocess.run(args, check=False)
    return completed.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help="execute pytest after displaying the overview",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="TEST",
        help="specific test file or expression to run (can be passed multiple times)",
    )
    parser.add_argument(
        "--",
        dest="pytest_args",
        nargs=argparse.REMAINDER,
        help="additional arguments forwarded to pytest",
    )

    args = parser.parse_args(argv)

    test_files = [Path(t) for t in args.target] if args.target else list(DEFAULT_TESTS)
    _print_overview(test_files)

    if not args.run:
        return 0

    extra = args.pytest_args or []
    exit_code = _run_pytest(tuple(test_files), extra)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
