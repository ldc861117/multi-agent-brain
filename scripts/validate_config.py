#!/usr/bin/env python3
"""Quick validation helper for configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

CONFIG_PATHS: tuple[Path, ...] = (
    Path(".env.example"),
    Path("utils/config_manager.py"),
    Path("utils/openai_client.py"),
    Path("config.yaml"),
)


def describe_file(path: Path) -> None:
    if not path.exists():
        print(f"❌ {path} missing")
        return

    print(f"✅ {path} exists")
    try:
        size = path.stat().st_size
    except OSError as exc:  # pragma: no cover - best effort helper
        print(f"   Failed to stat file: {exc}")
        return

    print(f"   Size: {size} bytes")


def main(targets: Iterable[Path] | None = None) -> int:
    print("Validating configuration files...")
    for path in targets or CONFIG_PATHS:
        describe_file(path)
    print("\nConfiguration structure validation complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
