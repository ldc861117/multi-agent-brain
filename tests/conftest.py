"""Project-wide pytest fixtures for deterministic test environments."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import pytest

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
    "DEBUG",
)


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
