"""Smoke tests for the demo runner CLI entry point."""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest

pytestmark = pytest.mark.smoke


def test_demo_runner_module_importable() -> None:
    module = importlib.import_module("demo_runner")
    assert hasattr(module, "MultiAgentDemo")
    assert callable(module.main)


def test_demo_runner_cli_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_run(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(asyncio, "run", fake_run)
    sys.modules.pop("demo_runner", None)

    module = importlib.import_module("demo_runner")
    assert hasattr(module, "main")
    assert calls == []
