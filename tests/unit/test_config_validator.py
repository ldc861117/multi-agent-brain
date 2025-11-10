import textwrap
from pathlib import Path

from utils.config_validator import ConfigValidator


MINIMAL_DEFAULT = textwrap.dedent(
    """
    network:
      name: "multi-agent-brain"
      mode: "centralized"
      node_id: "test-node"
      transports:
        - type: "http"
          config:
            port: 8700
      manifest_transport: "http"
      recommended_transport: "http"
      mods:
        - name: "openagents.mods.workspace.messaging"
          enabled: true
        - name: "openagents.mods.workspace.default"
          enabled: true
    network_profile:
      host: "127.0.0.1"
      port: 8700
    api_config:
      chat_api:
        provider: "openai"
        model: "gpt-3.5-turbo"
        timeout: 30
        max_retries: 3
        retry_delay: 1.0
        max_retry_delay: 60.0
      embedding_api:
        provider: "openai"
        model: "text-embedding-3-small"
        dimension: 1536
        timeout: 30
        max_retries: 3
        retry_delay: 1.0
        max_retry_delay: 60.0
      agent_overrides: {}
    """
)


def write_config(tmp_path: Path, config_text: str, default_text: str = MINIMAL_DEFAULT) -> ConfigValidator:
    config_path = tmp_path / "config.yaml"
    default_path = tmp_path / "config.default.yaml"

    config_path.write_text(textwrap.dedent(config_text), encoding="utf-8")
    default_path.write_text(textwrap.dedent(default_text), encoding="utf-8")

    return ConfigValidator(config_path=config_path, default_path=default_path)


def test_validator_accepts_valid_configuration(tmp_path: Path) -> None:
    validator = write_config(
        tmp_path,
        config_text="""
        network:
          name: "multi-agent-brain"
          mode: "centralized"
          transports:
            - type: "http"
              config:
                port: 8700
          manifest_transport: "http"
          recommended_transport: "http"
          mods:
            - name: "openagents.mods.workspace.messaging"
              enabled: true
            - name: "openagents.mods.workspace.default"
              enabled: true
        network_profile:
          host: "127.0.0.1"
          port: 8700
        api_config:
          chat_api:
            provider: "openai"
            model: "gpt-3.5-turbo"
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
          embedding_api:
            provider: "openai"
            model: "text-embedding-3-small"
            dimension: 1536
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
        """,
    )

    result = validator.validate()
    assert result.is_valid, f"Expected valid configuration, got errors: {[e.message for e in result.errors]}"


def test_validator_rejects_missing_network(tmp_path: Path) -> None:
    validator = write_config(
        tmp_path,
        config_text="""
        api_config:
          chat_api:
            provider: "openai"
            model: "gpt-3.5-turbo"
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
          embedding_api:
            provider: "openai"
            model: "text-embedding-3-small"
            dimension: 1536
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
        """,
    )

    result = validator.validate()
    assert not result.is_valid
    messages = [issue.message for issue in result.errors]
    assert any("'network'" in message for message in messages)


def test_validator_requires_http_port(tmp_path: Path) -> None:
    validator = write_config(
        tmp_path,
        config_text="""
        network:
          name: "multi-agent-brain"
          mode: "centralized"
          transports:
            - type: "http"
          manifest_transport: "http"
          recommended_transport: "http"
          mods:
            - name: "openagents.mods.workspace.messaging"
              enabled: true
            - name: "openagents.mods.workspace.default"
              enabled: true
        network_profile:
          host: "127.0.0.1"
          port: 8700
        api_config:
          chat_api:
            provider: "openai"
            model: "gpt-3.5-turbo"
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
          embedding_api:
            provider: "openai"
            model: "text-embedding-3-small"
            dimension: 1536
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
        """,
    )

    result = validator.validate()
    assert not result.is_valid
    messages = [issue.message for issue in result.errors]
    assert any("HTTP transport" in message for message in messages)


def test_validator_requires_embedding_dimension(tmp_path: Path) -> None:
    validator = write_config(
        tmp_path,
        config_text="""
        network:
          name: "multi-agent-brain"
          mode: "centralized"
          transports:
            - type: "http"
              config:
                port: 8700
          manifest_transport: "http"
          recommended_transport: "http"
          mods:
            - name: "openagents.mods.workspace.messaging"
              enabled: true
            - name: "openagents.mods.workspace.default"
              enabled: true
        network_profile:
          host: "127.0.0.1"
          port: 8700
        api_config:
          chat_api:
            provider: "openai"
            model: "gpt-3.5-turbo"
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
          embedding_api:
            provider: "openai"
            model: "text-embedding-3-small"
            timeout: 30
            max_retries: 3
            retry_delay: 1.0
            max_retry_delay: 60.0
        """,
    )

    result = validator.validate()
    assert not result.is_valid
    messages = [issue.message for issue in result.errors]
    assert any("embedding API setting 'dimension'" in message for message in messages)


def test_repair_copies_default_and_creates_backup(tmp_path: Path) -> None:
    validator = write_config(
        tmp_path,
        config_text="""
        invalid: true
        """,
    )

    config_path = tmp_path / "config.yaml"
    default_path = tmp_path / "config.default.yaml"

    original_content = config_path.read_text(encoding="utf-8")
    assert "invalid" in original_content

    repaired_path = validator.repair()
    assert repaired_path == config_path
    assert config_path.read_text(encoding="utf-8") == default_path.read_text(encoding="utf-8")

    backups = list(tmp_path.glob("config.yaml.bak.*"))
    assert backups, "Expected a backup file to be created before repair"
    assert backups[0].read_text(encoding="utf-8") == original_content
