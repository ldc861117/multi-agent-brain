"""Smoke tests for configuration loading behavior."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from utils.config_manager import ConfigManager

pytestmark = pytest.mark.smoke


@pytest.fixture
def base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide minimal environment variables required for config loading."""
    monkeypatch.setenv("CHAT_API_KEY", "test-chat-key")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")


def _write_yaml_config(tmp_path: Path, raw_yaml: str) -> Path:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(textwrap.dedent(raw_yaml))
    return config_path


def test_yaml_defaults_apply_without_env_models(tmp_path: Path, base_env: None) -> None:
    """YAML defaults should populate model names when env vars are absent."""
    config_path = _write_yaml_config(
        tmp_path,
        """
        api_config:
          chat_api:
            provider: openai
            model: yaml-chat-model
            timeout: 15
          embedding_api:
            provider: openai
            model: yaml-embedding-model
            dimension: 768
        """,
    )

    manager = ConfigManager(config_path=str(config_path))
    config = manager.get_global_config()

    assert config.chat_api.model == "yaml-chat-model"
    assert config.embedding_api.model == "yaml-embedding-model"
    assert config.embedding_api.dimension == 768


def test_environment_overrides_take_priority(tmp_path: Path, base_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit environment variables should override YAML defaults."""
    monkeypatch.setenv("CHAT_API_MODEL", "env-priority-chat")
    monkeypatch.setenv("EMBEDDING_API_MODEL", "env-priority-embed")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "1024")

    config_path = _write_yaml_config(
        tmp_path,
        """
        api_config:
          chat_api:
            provider: openai
            model: yaml-chat-model
          embedding_api:
            provider: openai
            model: yaml-embedding-model
            dimension: 256
        """,
    )

    manager = ConfigManager(config_path=str(config_path))
    config = manager.get_global_config()

    assert config.chat_api.model == "env-priority-chat"
    assert config.embedding_api.model == "env-priority-embed"
    assert config.embedding_api.dimension == 1024


def test_agent_override_applied_on_top_of_global(tmp_path: Path, base_env: None) -> None:
    """Agent-specific overrides should tailor models without mutating global config."""
    config_path = _write_yaml_config(
        tmp_path,
        """
        api_config:
          chat_api:
            provider: openai
            model: yaml-chat-model
          embedding_api:
            provider: openai
            model: yaml-embedding-model
            dimension: 768
          agent_overrides:
            coordination:
              chat_model: coordinator-override-chat
              embedding_model: coordinator-override-embed
              embedding_dimension: 384
        """,
    )

    manager = ConfigManager(config_path=str(config_path))
    global_config = manager.get_global_config()
    coordination_config = manager.get_agent_config("coordination")

    assert global_config.chat_api.model == "yaml-chat-model"
    assert global_config.embedding_api.model == "yaml-embedding-model"

    assert coordination_config.chat_api.model == "coordinator-override-chat"
    assert coordination_config.embedding_api.model == "coordinator-override-embed"
    assert coordination_config.embedding_api.dimension == 384
