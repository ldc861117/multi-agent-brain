"""Offline smoke tests to ensure core modules import correctly."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.smoke


@pytest.mark.parametrize(
    "module_name",
    (
        "agents.coordination.agent",
        "agents.shared_memory",
        "utils.config_manager",
        "utils.openai_client",
        "utils.observability",
    ),
)
def test_module_imports(module_name: str) -> None:
    """Verify that critical modules import without accessing external services."""
    module = importlib.import_module(module_name)
    assert module is not None


@pytest.mark.parametrize(
    "symbol_path",
    (
        "agents.coordination.agent.CoordinationAgent",
        "agents.shared_memory.SharedMemory",
        "utils.config_manager.ConfigManager",
        "utils.openai_client.OpenAIClientWrapper",
        "utils.observability.metrics_registry",
    ),
)
def test_symbol_resolution(symbol_path: str) -> None:
    """Ensure important symbols are available after import."""
    module_name, attribute_name = symbol_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    assert getattr(module, attribute_name) is not None
