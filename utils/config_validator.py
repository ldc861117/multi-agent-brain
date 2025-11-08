"""Configuration validation utilities for multi-agent-brain.

This module validates the shape of ``config.yaml`` before the demo or
OpenAgents network is started. It focuses on the two critical sections
required by OpenAgents and the local agent stack:

* ``network`` – transport ports, workspace mods, discovery settings
* ``api_config`` – chat/embedding providers and agent overrides

The validator provides actionable error messages and can optionally repair
an invalid configuration by copying ``config.default.yaml`` (after creating a
backup of the user's file).
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    message: str
    path: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = {"message": self.message}
        if self.path:
            payload["path"] = self.path
        return payload


@dataclass
class ValidationResult:
    """Aggregated validation outcome."""

    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    missing_keys: List[str] = field(default_factory=list)

    def raise_for_errors(self) -> None:
        if not self.is_valid:
            messages = "\n".join(f"- {issue.message}" for issue in self.errors)
            raise ConfigValidationError(messages)

    def to_json(self) -> str:
        payload = {
            "valid": self.is_valid,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "suggestions": self.suggestions,
            "missing_keys": self.missing_keys,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)


class ConfigValidator:
    """Validate the structure of config.yaml against project expectations."""

    REQUIRED_NETWORK_FIELDS: Iterable[str] = (
        "name",
        "mode",
        "transports",
        "manifest_transport",
        "recommended_transport",
        "mods",
    )

    REQUIRED_NETWORK_PROFILE_FIELDS: Iterable[str] = (
        "host",
        "port",
    )

    REQUIRED_CHAT_FIELDS: Iterable[str] = (
        "provider",
        "model",
        "timeout",
        "max_retries",
        "retry_delay",
        "max_retry_delay",
    )

    REQUIRED_EMBEDDING_FIELDS: Iterable[str] = (
        "provider",
        "model",
        "dimension",
        "timeout",
        "max_retries",
        "retry_delay",
        "max_retry_delay",
    )

    WORKSPACE_MOD_NAMES: Iterable[str] = (
        "openagents.mods.workspace.default",
        "openagents.mods.workspace.messaging",
    )

    def __init__(self, config_path: Path | str = "config.yaml", default_path: Path | str = "config.default.yaml"):
        self.config_path = Path(config_path)
        self.default_path = Path(default_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def validate(self) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if not self.config_path.exists():
            result.is_valid = False
            result.errors.append(
                ValidationIssue(
                    message=f"Configuration file '{self.config_path}' does not exist."
                )
            )
            result.suggestions.append("Create the file from config.default.yaml or run the repair option.")
            return result

        config = self._load_yaml(self.config_path)
        if config is None:
            result.is_valid = False
            result.errors.append(
                ValidationIssue(
                    message=f"Configuration file '{self.config_path}' is empty or not valid YAML."
                )
            )
            result.suggestions.append("Replace the file with config.default.yaml or fix the YAML syntax.")
            return result

        default_config = self._load_yaml(self.default_path)

        self._validate_network(config, default_config, result)
        self._validate_api_config(config, default_config, result)

        if result.errors:
            result.is_valid = False

        return result

    def repair(self, overwrite: bool = True) -> Path:
        """Repair the configuration using the default template.

        Parameters
        ----------
        overwrite:
            Whether to overwrite the existing config. When True and ``config.yaml``
            already exists, a timestamped backup is created next to it before copying.

        Returns
        -------
        Path
            Path to the repaired configuration file.
        """
        if not self.default_path.exists():
            raise ConfigValidationError(
                f"Default configuration '{self.default_path}' was not found; cannot repair."
            )

        target = self.config_path

        if overwrite and target.exists():
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            backup_path = target.parent / f"{target.name}.bak.{timestamp}"
            shutil.copy2(target, backup_path)

        shutil.copy2(self.default_path, target)
        return target

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
                return data or {}
        except FileNotFoundError:
            return None
        except yaml.YAMLError as exc:  # pragma: no cover - passes through validation path
            raise ConfigValidationError(f"Failed to parse YAML file '{path}': {exc}") from exc

    def _validate_network(
        self,
        config: Dict[str, Any],
        default_config: Optional[Dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        network = config.get("network")
        if not isinstance(network, dict):
            result.errors.append(
                ValidationIssue(
                    message="Configuration file config.yaml must contain a 'network' section.",
                    path="network",
                )
            )
            if default_config and default_config.get("network"):
                missing = self._collect_missing_keys(default_config["network"], network, prefix="network")
                result.missing_keys.extend(missing)
            result.suggestions.append(
                "Copy the network section from config.default.yaml or run the repair command."
            )
            return

        for field in self.REQUIRED_NETWORK_FIELDS:
            if field not in network:
                result.errors.append(
                    ValidationIssue(
                        message=f"Missing required network setting '{field}'.",
                        path=f"network.{field}",
                    )
                )

        transports = network.get("transports")
        if not isinstance(transports, list) or not transports:
            result.errors.append(
                ValidationIssue(
                    message="The network.transports list must define at least an HTTP transport.",
                    path="network.transports",
                )
            )
        else:
            http_transports = [t for t in transports if str(t.get("type")).lower() == "http"]
            if not http_transports:
                result.errors.append(
                    ValidationIssue(
                        message="At least one HTTP transport with a defined port is required for OpenAgents.",
                        path="network.transports",
                    )
                )
            else:
                for transport in http_transports:
                    config_block = transport.get("config")
                    if not isinstance(config_block, dict) or "port" not in config_block:
                        result.errors.append(
                            ValidationIssue(
                                message="HTTP transport entries must declare a 'config.port' value.",
                                path="network.transports[].config.port",
                            )
                        )

        mods = network.get("mods", []) if isinstance(network, dict) else []
        mod_names = {mod.get("name") for mod in mods if isinstance(mod, dict)}
        missing_mods = [mod for mod in self.WORKSPACE_MOD_NAMES if mod not in mod_names]
        if missing_mods:
            result.errors.append(
                ValidationIssue(
                    message="Missing required workspace mods: " + ", ".join(missing_mods),
                    path="network.mods",
                )
            )

        if default_config and default_config.get("network"):
            missing = self._collect_missing_keys(default_config["network"], network, prefix="network")
            result.missing_keys.extend(missing)

        network_profile = config.get("network_profile")
        if not isinstance(network_profile, dict):
            result.errors.append(
                ValidationIssue(
                    message="Missing 'network_profile' section required by OpenAgents dashboards.",
                    path="network_profile",
                )
            )
        else:
            for field in self.REQUIRED_NETWORK_PROFILE_FIELDS:
                if field not in network_profile:
                    result.errors.append(
                        ValidationIssue(
                            message=f"Missing required network_profile field '{field}'.",
                            path=f"network_profile.{field}",
                        )
                    )

    def _validate_api_config(
        self,
        config: Dict[str, Any],
        default_config: Optional[Dict[str, Any]],
        result: ValidationResult,
    ) -> None:
        api_config = config.get("api_config")
        if not isinstance(api_config, dict):
            result.errors.append(
                ValidationIssue(
                    message="Configuration must include an 'api_config' section.",
                    path="api_config",
                )
            )
            if default_config and default_config.get("api_config"):
                result.missing_keys.extend(
                    self._collect_missing_keys(default_config["api_config"], api_config, prefix="api_config")
                )
            result.suggestions.append("Copy the api_config section from config.default.yaml and customise it.")
            return

        chat_api = api_config.get("chat_api")
        embedding_api = api_config.get("embedding_api")

        if not isinstance(chat_api, dict):
            result.errors.append(
                ValidationIssue(
                    message="api_config.chat_api must be defined as a mapping.",
                    path="api_config.chat_api",
                )
            )
        else:
            for field in self.REQUIRED_CHAT_FIELDS:
                if field not in chat_api:
                    result.errors.append(
                        ValidationIssue(
                            message=f"Missing chat API setting '{field}'.",
                            path=f"api_config.chat_api.{field}",
                        )
                    )

        if not isinstance(embedding_api, dict):
            result.errors.append(
                ValidationIssue(
                    message="api_config.embedding_api must be defined as a mapping.",
                    path="api_config.embedding_api",
                )
            )
        else:
            for field in self.REQUIRED_EMBEDDING_FIELDS:
                if field not in embedding_api:
                    result.errors.append(
                        ValidationIssue(
                            message=f"Missing embedding API setting '{field}'.",
                            path=f"api_config.embedding_api.{field}",
                        )
                    )

        overrides = api_config.get("agent_overrides")
        if overrides is not None and not isinstance(overrides, dict):
            result.errors.append(
                ValidationIssue(
                    message="api_config.agent_overrides must be a mapping when provided.",
                    path="api_config.agent_overrides",
                )
            )

        if default_config and default_config.get("api_config"):
            result.missing_keys.extend(
                self._collect_missing_keys(default_config["api_config"], api_config, prefix="api_config")
            )

    def _collect_missing_keys(
        self,
        reference: Any,
        candidate: Any,
        prefix: str,
    ) -> List[str]:
        missing: List[str] = []

        if isinstance(reference, dict):
            for key, value in reference.items():
                candidate_value = candidate.get(key) if isinstance(candidate, dict) else None
                qualified_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    if not isinstance(candidate_value, dict):
                        missing.append(qualified_key)
                    else:
                        missing.extend(self._collect_missing_keys(value, candidate_value, qualified_key))
                else:
                    if candidate_value is None:
                        missing.append(qualified_key)

        return missing


def _create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate multi-agent-brain config.yaml")
    parser.add_argument("--path", default="config.yaml", help="Path to the configuration file")
    parser.add_argument(
        "--default",
        default="config.default.yaml",
        dest="default_path",
        help="Path to the default configuration template",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Overwrite the config file with the default template after creating a backup",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output validation results in JSON format",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _create_argument_parser()
    args = parser.parse_args(argv)

    validator = ConfigValidator(config_path=args.path, default_path=args.default_path)

    if args.repair:
        repaired_path = validator.repair(overwrite=True)
        print(f"Repaired configuration written to {repaired_path}")
        return 0

    try:
        result = validator.validate()
    except ConfigValidationError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(result.to_json())
    else:
        if result.is_valid:
            print(f"✅ Configuration '{args.path}' is valid.")
        else:
            print(f"❌ Configuration '{args.path}' is invalid:")
            for issue in result.errors:
                location = f" ({issue.path})" if issue.path else ""
                print(f"  - {issue.message}{location}")
            if result.missing_keys:
                print("\nMissing keys compared to default template:")
                for key in sorted(set(result.missing_keys)):
                    print(f"  * {key}")
            if result.suggestions:
                print("\nSuggested fixes:")
                for suggestion in result.suggestions:
                    print(f"  • {suggestion}")
    return 0 if result.is_valid else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
