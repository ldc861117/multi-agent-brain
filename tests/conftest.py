"""Project-wide pytest fixtures for deterministic test environments."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Iterable

import pytest

from tests.fixtures.fakes import (
    DummyMetrics,
    FakeOpenAIClient,
    FakeSharedMemory,
    build_fake_registry,
    build_stub_openai_config,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_ISOLATED_ENV_KEYS: Iterable[str] = (
    "CHAT_API_KEY",
    "CHAT_API_BASE_URL",
    "CHAT_API_MODEL",
    "CHAT_API_PROVIDER",
    "CHAT_API_TIMEOUT",
    "CHAT_API_MAX_RETRIES",
    "CHAT_API_RETRY_DELAY",
    "CHAT_API_MAX_RETRY_DELAY",
    "EMBEDDING_API_KEY",
    "EMBEDDING_API_BASE_URL",
    "EMBEDDING_API_MODEL",
    "EMBEDDING_API_PROVIDER",
    "EMBEDDING_API_TIMEOUT",
    "EMBEDDING_API_MAX_RETRIES",
    "EMBEDDING_API_RETRY_DELAY",
    "EMBEDDING_API_MAX_RETRY_DELAY",
    "EMBEDDING_DIMENSION",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_TIMEOUT",
    "OPENAI_MAX_RETRIES",
    "OPENAI_RETRY_DELAY",
    "OPENAI_MAX_RETRY_DELAY",
    "MILVUS_URI",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_DIAGNOSE",
    "ENABLE_METRICS",
    "METRICS_PORT",
    "METRICS_HOST",
    "RUN_ID",
    "DEBUG",
)


@pytest.fixture(autouse=True)
def deterministic_seeds() -> None:
    """Ensure deterministic randomness across the test suite."""

    random.seed(1337)


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ISOLATED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    try:
        import dotenv
    except ImportError:  # pragma: no cover - dependency is optional at runtime
        pass
    else:
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *_, **__: False, raising=False)

    try:
        import utils.openai_client as openai_client
    except Exception:  # pragma: no cover - module import tested elsewhere
        return
    monkeypatch.setattr(openai_client, "load_dotenv", lambda *_, **__: False, raising=False)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically categorize tests based on their directory."""
    root = Path(__file__).resolve().parent
    unit_dir = root / "unit"
    integration_dir = root / "integration"
    e2e_dir = root / "e2e"

    for item in items:
        path = Path(str(item.fspath)).resolve()
        if unit_dir in path.parents:
            item.add_marker("unit")
        elif integration_dir in path.parents:
            item.add_marker("integration")
        elif e2e_dir in path.parents:
            item.add_marker("e2e")


@pytest.fixture
def fake_registry():
    """Return a registry populated with scaffold experts."""

    return build_fake_registry()


@pytest.fixture
def fake_shared_memory() -> FakeSharedMemory:
    """Return an isolated in-memory SharedMemory stub."""

    return FakeSharedMemory()


@pytest.fixture
def fake_openai_client_class() -> type[FakeOpenAIClient]:
    """Expose FakeOpenAIClient for monkeypatching OpenAI wrappers."""

    return FakeOpenAIClient


@pytest.fixture
def dummy_metrics() -> DummyMetrics:
    """Provide a metrics sink capturing invocation details."""

    return DummyMetrics()


@pytest.fixture
def stub_agent_settings(monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch configuration helpers to return deterministic settings."""

    config = build_stub_openai_config()
    monkeypatch.setattr(
        "utils.config_manager.ConfigManager.get_agent_config",
        lambda self, *_: config,
    )
    monkeypatch.setattr("utils.config_manager.get_agent_config", lambda *_: config)
    monkeypatch.setattr(
        "utils.config_manager.ConfigManager.get_agent_answer_verbose",
        lambda self, *_: False,
    )
    monkeypatch.setattr("utils.config_manager.get_agent_answer_verbose", lambda *_: False)
    return config
