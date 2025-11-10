#!/usr/bin/env python3
"""Run a focused pytest target with helpful defaults."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_TARGET = Path("tests/unit/test_env_config.py")


def _normalize_pytest_args(args: Sequence[str]) -> list[str]:
    extra = list(args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    return extra


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        default=str(DEFAULT_TARGET),
        help="file or expression to execute (defaults to env config unit tests)",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="extra arguments forwarded to pytest",
    )

    args = parser.parse_args(argv)
    target = Path(args.target)

    if not target.exists():
        parser.error(f"target '{target}' does not exist")

    pytest_cmd = [sys.executable, "-m", "pytest", str(target)]
    pytest_cmd.extend(_normalize_pytest_args(args.pytest_args or ()))

    print("Executing:", " ".join(pytest_cmd))
    result = subprocess.run(pytest_cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
