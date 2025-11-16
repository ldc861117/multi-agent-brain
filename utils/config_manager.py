"""Configuration management for multi-agent scaffolding.

This module provides configuration loading and management with support for:
- Environment variable loading with fallback
- YAML configuration file support
- Per-agent model overrides
- Backward compatibility with existing configurations
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import yaml
from loguru import logger
from dotenv import load_dotenv

from .config_validator import ConfigValidator, ConfigValidationError
from .openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType, BrowserToolConfig


# Load environment variables from .env file
load_dotenv()


class ConfigManager:
    """Configuration manager with support for per-agent overrides."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Parameters
        ----------
        config_path:
            Path to the YAML configuration file. If not provided, uses default.
        """
        self.config_path = config_path or "config.yaml"
        self._yaml_config: Optional[Dict[str, Any]] = None
        self._agent_configs: Dict[str, OpenAIConfig] = {}
        self._browser_tool_configs: Dict[str, BrowserToolConfig] = {}
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load YAML configuration from file."""
        if self._yaml_config is None:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as f:
                        self._yaml_config = yaml.safe_load(f) or {}
                    logger.info(f"Loaded configuration from {self.config_path}")
                    self._log_validation_feedback()
                else:
                    # Try to create from default template
                    self._yaml_config = self._create_config_from_default()
                    logger.warning(
                        f"Configuration file {self.config_path} not found, "
                        f"created from default template. Please review and customize as needed."
                    )
                    self._log_validation_feedback()
            except Exception as e:
                logger.error(f"Failed to load configuration from {self.config_path}: {e}")
                self._yaml_config = {}
        
        return self._yaml_config
    
    def _create_config_from_default(self) -> Dict[str, Any]:
        """Create configuration from default template if config.yaml is missing.
        
        Returns
        -------
        Dict[str, Any]
            Default configuration loaded from config.default.yaml or hardcoded defaults.
        """
        default_config_path = "config.default.yaml"
        
        # Try to load from default template
        if os.path.exists(default_config_path):
            try:
                with open(default_config_path, 'r') as f:
                    default_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded default configuration from {default_config_path}")
                
                # Create config.yaml from default template (non-destructive operation)
                try:
                    with open(self.config_path, 'w') as f:
                        yaml.dump(default_config, f, default_flow_style=False, indent=2)
                    logger.info(f"Created {self.config_path} from default template")
                except Exception as e:
                    logger.warning(f"Failed to create {self.config_path}: {e}")
                
                return default_config
            except Exception as e:
                logger.error(f"Failed to load default configuration from {default_config_path}: {e}")
        
        # Fallback to hardcoded minimal configuration
        logger.warning("Using hardcoded minimal configuration as fallback")
        return {
            'api_config': {
                'chat_api': {
                    'provider': 'openai',
                    'model': 'gpt-3.5-turbo',
                    'timeout': 30,
                    'max_retries': 3,
                    'retry_delay': 1.0,
                    'max_retry_delay': 60.0,
                },
                'embedding_api': {
                    'provider': 'openai',
                    'model': 'text-embedding-3-small',
                    'dimension': 1536,
                    'timeout': 30,
                    'max_retries': 3,
                    'retry_delay': 1.0,
                    'max_retry_delay': 60.0,
                },
                'agent_overrides': {}
            },
            'channels': {},
            'routing': {
                'default_target': 'general',
                'escalations': {}
            }
        }
    
    def _log_validation_feedback(self) -> None:
        """Run schema validation and log actionable messages."""
        validator = ConfigValidator(config_path=self.config_path, default_path="config.default.yaml")
        try:
            result = validator.validate()
        except ConfigValidationError as exc:
            logger.error(f"Configuration validation failed: {exc}")
            return
    
        if not result.is_valid:
            for issue in result.errors:
                path = issue.path or "root"
                logger.error(
                    "Configuration schema error at {path}: {message}",
                    path=path,
                    message=issue.message,
                )
            if result.missing_keys:
                logger.warning(
                    "Missing configuration keys compared to template: {keys}",
                    keys=", ".join(sorted(set(result.missing_keys))),
                )
        elif result.missing_keys:
            logger.debug(
                "Configuration missing optional template keys: {keys}",
                keys=", ".join(sorted(set(result.missing_keys))),
            )
    
    @staticmethod
    def _env_override_active(*names: str) -> bool:
        """Return True if any provided environment variable is set to a non-empty value."""
        for name in names:
            value = os.getenv(name)
            if value is not None and value.strip() != "":
                return True
        return False
    
    def get_global_config(self) -> OpenAIConfig:
        """Get the global OpenAI configuration."""
        config = OpenAIConfig.from_env_with_fallback()
        yaml_config = self._load_yaml_config()
        api_config = yaml_config.get('api_config', {}) if isinstance(yaml_config, dict) else {}
        chat_settings = api_config.get('chat_api') or {}
        embedding_settings = api_config.get('embedding_api') or {}
        applied_fields: Dict[str, Any] = {}
        
        if chat_settings:
            if not self._env_override_active("CHAT_API_MODEL", "OPENAI_MODEL"):
                chat_model_value = chat_settings.get('model')
                if chat_model_value:
                    config.chat_api.model = str(chat_model_value)
                    applied_fields['chat_model'] = config.chat_api.model
            if not self._env_override_active("CHAT_API_PROVIDER"):
                provider_value = chat_settings.get('provider')
                if provider_value:
                    provider_candidate = str(provider_value).strip().lower()
                    if provider_candidate:
                        try:
                            config.chat_api.provider = ProviderType(provider_candidate)
                            applied_fields['chat_provider'] = config.chat_api.provider.value
                        except ValueError:
                            logger.warning(
                                "Ignoring unsupported chat provider in YAML configuration",
                                extra={"provider_raw": provider_value},
                            )
            for attr, env_names, caster, log_key in (
                ("timeout", ("CHAT_API_TIMEOUT",), int, "chat_timeout"),
                ("max_retries", ("CHAT_API_MAX_RETRIES",), int, "chat_max_retries"),
                ("retry_delay", ("CHAT_API_RETRY_DELAY",), float, "chat_retry_delay"),
                ("max_retry_delay", ("CHAT_API_MAX_RETRY_DELAY",), float, "chat_max_retry_delay"),
            ):
                if not self._env_override_active(*env_names):
                    yaml_value = chat_settings.get(attr)
                    if yaml_value is not None:
                        try:
                            setattr(config.chat_api, attr, caster(yaml_value))
                            applied_fields[log_key] = getattr(config.chat_api, attr)
                        except (TypeError, ValueError):
                            logger.warning(
                                "Invalid YAML value for chat API setting",
                                extra={"field": attr, "value": yaml_value},
                            )
        
        if embedding_settings:
            if not self._env_override_active("EMBEDDING_API_MODEL", "EMBEDDING_MODEL"):
                embedding_model_value = embedding_settings.get('model')
                if embedding_model_value:
                    config.embedding_api.model = str(embedding_model_value)
                    applied_fields['embedding_model'] = config.embedding_api.model
            if not self._env_override_active("EMBEDDING_API_PROVIDER"):
                embedding_provider_value = embedding_settings.get('provider')
                if embedding_provider_value:
                    provider_candidate = str(embedding_provider_value).strip().lower()
                    if provider_candidate:
                        try:
                            config.embedding_api.provider = ProviderType(provider_candidate)
                            applied_fields['embedding_provider'] = config.embedding_api.provider.value
                        except ValueError:
                            logger.warning(
                                "Ignoring unsupported embedding provider in YAML configuration",
                                extra={"provider_raw": embedding_provider_value},
                            )
            if not self._env_override_active("EMBEDDING_DIMENSION"):
                dimension_value = embedding_settings.get('dimension')
                if dimension_value is not None:
                    try:
                        config.embedding_api.dimension = int(dimension_value)
                        applied_fields['embedding_dimension'] = config.embedding_api.dimension
                    except (TypeError, ValueError):
                        logger.warning(
                            "Invalid YAML value for embedding dimension",
                            extra={"value": dimension_value},
                        )
            for attr, env_names, caster, log_key in (
                ("timeout", ("EMBEDDING_API_TIMEOUT",), int, "embedding_timeout"),
                ("max_retries", ("EMBEDDING_API_MAX_RETRIES",), int, "embedding_max_retries"),
                ("retry_delay", ("EMBEDDING_API_RETRY_DELAY",), float, "embedding_retry_delay"),
                ("max_retry_delay", ("EMBEDDING_API_MAX_RETRY_DELAY",), float, "embedding_max_retry_delay"),
            ):
                if not self._env_override_active(*env_names):
                    yaml_value = embedding_settings.get(attr)
                    if yaml_value is not None:
                        try:
                            setattr(config.embedding_api, attr, caster(yaml_value))
                            applied_fields[log_key] = getattr(config.embedding_api, attr)
                        except (TypeError, ValueError):
                            logger.warning(
                                "Invalid YAML value for embedding API setting",
                                extra={"field": attr, "value": yaml_value},
                            )
        
        if applied_fields:
            logger.debug(
                "Applied YAML defaults to global OpenAI configuration",
                extra={"applied_fields": applied_fields},
            )
        
        return config
    
    def get_agent_config(self, agent_name: str) -> OpenAIConfig:
        """Get OpenAI configuration for a specific agent with overrides.
        
        Parameters
        ----------
        agent_name:
            Name of the agent (e.g., "coordination", "python_expert")
            
        Returns
        -------
        OpenAIConfig
            Configuration with agent-specific overrides applied.
        """
        if agent_name in self._agent_configs:
            return self._agent_configs[agent_name]
        
        # Start with global configuration
        global_config = self.get_global_config()
        
        # Load YAML configuration
        yaml_config = self._load_yaml_config()
        
        # Check for agent overrides
        api_config = yaml_config.get('api_config', {})
        agent_overrides = api_config.get('agent_overrides', {})
        agent_override = agent_overrides.get(agent_name, {})
        
        if not agent_override:
            # No overrides, use global config
            self._agent_configs[agent_name] = global_config
            return global_config
        
        # Apply overrides with agent configuration taking precedence
        applied_agent_fields: Dict[str, Any] = {}
        
        chat_model = global_config.chat_api.model
        chat_override_value = agent_override.get('chat_model')
        if chat_override_value is not None:
            chat_model = str(chat_override_value)
            applied_agent_fields['chat_model'] = chat_model
        
        embedding_model = global_config.embedding_api.model
        embedding_override_value = agent_override.get('embedding_model')
        if embedding_override_value is not None:
            embedding_model = str(embedding_override_value)
            applied_agent_fields['embedding_model'] = embedding_model
            
        embedding_dimension = global_config.embedding_api.dimension
        dimension_override_value = agent_override.get('embedding_dimension')
        if dimension_override_value is not None:
            try:
                embedding_dimension = int(dimension_override_value)
                applied_agent_fields['embedding_dimension'] = embedding_dimension
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid agent embedding dimension override",
                    extra={"agent": agent_name, "value": dimension_override_value},
                )
        
        # TODO: Support per-agent overrides for retry/backoff settings if future use-cases require it.
        chat_config = ChatAPIConfig(
            api_key=global_config.chat_api.api_key,
            base_url=global_config.chat_api.base_url,
            model=chat_model,
            provider=global_config.chat_api.provider,
            timeout=global_config.chat_api.timeout,
            max_retries=global_config.chat_api.max_retries,
            retry_delay=global_config.chat_api.retry_delay,
            max_retry_delay=global_config.chat_api.max_retry_delay,
        )
        
        embedding_config = EmbeddingAPIConfig(
            api_key=global_config.embedding_api.api_key,
            base_url=global_config.embedding_api.base_url,
            model=embedding_model,
            provider=global_config.embedding_api.provider,
            dimension=embedding_dimension,
            timeout=global_config.embedding_api.timeout,
            max_retries=global_config.embedding_api.max_retries,
            retry_delay=global_config.embedding_api.retry_delay,
            max_retry_delay=global_config.embedding_api.max_retry_delay,
        )
        
        agent_config = OpenAIConfig(
            chat_api=chat_config,
            embedding_api=embedding_config
        )
        
        # Cache the result
        self._agent_configs[agent_name] = agent_config
        
        logger.info(
            "Applied configuration overrides for agent",
            extra={
                "agent": agent_name,
                "chat_model": agent_config.chat_api.model,
                "embedding_model": agent_config.embedding_api.model,
                "embedding_dimension": agent_config.embedding_api.dimension,
                "applied_fields": applied_agent_fields or None,
            }
        )
        
        return agent_config
    
    def get_agent_chat_model(self, agent_name: str) -> str:
        """Get the chat model for a specific agent.
        
        Parameters
        ----------
        agent_name:
            Name of the agent.
            
        Returns
        -------
        str
            The chat model name.
        """
        config = self.get_agent_config(agent_name)
        return config.chat_api.model
    
    def get_agent_embedding_model(self, agent_name: str) -> str:
        """Get the embedding model for a specific agent.
        
        Parameters
        ----------
        agent_name:
            Name of the agent.
            
        Returns
        -------
        str
            The embedding model name.
        """
        config = self.get_agent_config(agent_name)
        return config.embedding_api.model
    
    def get_agent_embedding_dimension(self, agent_name: str) -> int:
        """Get the embedding dimension for a specific agent.
        
        Parameters
        ----------
        agent_name:
            Name of the agent.
            
        Returns
        -------
        int
            The embedding dimension.
        """
        config = self.get_agent_config(agent_name)
        return config.embedding_api.dimension
    
    def get_agent_answer_verbose(self, agent_name: str) -> bool:
        """Get the answer verbosity setting for a specific agent.
        
        Parameters
        ----------
        agent_name:
            Name of the agent.
            
        Returns
        -------
        bool
            True if verbose answers are enabled, False for concise.
        """
        # Load YAML configuration
        yaml_config = self._load_yaml_config()
        
        # Check for agent overrides
        api_config = yaml_config.get('api_config', {})
        agent_overrides = api_config.get('agent_overrides', {})
        agent_override = agent_overrides.get(agent_name, {})
        
        # Return verbose setting if specified, default to False (concise)
        return agent_override.get('answer_verbose', False)
    
    def get_browser_tool_config(self, agent_name: str = "default") -> BrowserToolConfig:
        """Get browser tool configuration for a specific agent with overrides.
        
        Parameters
        ----------
        agent_name:
            Name of the agent (e.g., "coordination", "python_expert")
            
        Returns
        -------
        BrowserToolConfig
            Configuration with agent-specific overrides applied.
        """
        if agent_name in self._browser_tool_configs:
            return self._browser_tool_configs[agent_name]
        
        # Start with environment-based configuration
        config = BrowserToolConfig.from_env()
        
        # Load YAML configuration
        yaml_config = self._load_yaml_config()
        api_config = yaml_config.get('api_config', {})
        
        # Apply global browser_tool settings from YAML if no env override
        browser_tool_settings = api_config.get('browser_tool', {})
        if browser_tool_settings and isinstance(browser_tool_settings, dict):
            # Helper to check if env var is set
            def _has_env(var_name: str) -> bool:
                value = os.getenv(var_name)
                return value is not None and value.strip() != ""
            
            # Apply YAML settings only if corresponding env var is not set
            if not _has_env("BROWSER_TOOL_ENABLED"):
                config.enabled = browser_tool_settings.get('enabled', config.enabled)
            if not _has_env("BROWSER_SEARCH_PROVIDER"):
                config.search_provider = browser_tool_settings.get('search_provider', config.search_provider)
            if not _has_env("BROWSER_SEARCH_API_KEY") and not _has_env("TAVILY_API_KEY"):
                config.search_api_key = browser_tool_settings.get('search_api_key', config.search_api_key)
            if not _has_env("BROWSER_SEARCH_BASE_URL"):
                config.search_api_base_url = browser_tool_settings.get('search_api_base_url', config.search_api_base_url)
            if not _has_env("BROWSER_FALLBACK_PROVIDER"):
                config.fallback_provider = browser_tool_settings.get('fallback_provider', config.fallback_provider)
            if not _has_env("BROWSER_ENGINE"):
                config.browser_engine = browser_tool_settings.get('browser_engine', config.browser_engine)
            if not _has_env("BROWSER_HEADLESS"):
                config.headless = browser_tool_settings.get('headless', config.headless)
            if not _has_env("BROWSER_SEARCH_TIMEOUT"):
                config.search_timeout = browser_tool_settings.get('search_timeout', config.search_timeout)
            if not _has_env("BROWSER_NAVIGATION_TIMEOUT"):
                config.navigation_timeout = browser_tool_settings.get('navigation_timeout', config.navigation_timeout)
            if not _has_env("BROWSER_MAX_RETRIES"):
                config.max_retries = browser_tool_settings.get('max_retries', config.max_retries)
        
        # Check for agent-specific overrides
        agent_overrides = api_config.get('agent_overrides', {})
        agent_override = agent_overrides.get(agent_name, {})
        
        if agent_override and isinstance(agent_override, dict):
            browser_override = agent_override.get('browser_tool', {})
            if browser_override and isinstance(browser_override, dict):
                # Apply agent-specific browser tool overrides
                for key, value in browser_override.items():
                    if hasattr(config, key) and value is not None:
                        setattr(config, key, value)
                        logger.debug(
                            f"Applied browser_tool override for {agent_name}: {key}={value}"
                        )
        
        # Cache the config
        self._browser_tool_configs[agent_name] = config
        return config
    
    def get_registry_bootstrap(self) -> Dict[str, Dict[str, Any]]:
        """Return registry bootstrap definitions from configuration.
        
        The registry bootstrap is composed from multiple sources to maintain
        backward compatibility with legacy configurations:
        
        1. ``channels`` definitions provide entrypoints and descriptions.
        2. ``api_config.agent_overrides`` ensures known agents are registered
           even when explicit registry metadata is omitted.
        3. ``registry.bootstrap`` (mapping or list) can override and extend
           the automatically derived entries.
        
        Returns
        -------
        Dict[str, Dict[str, Any]]
            Normalised mapping keyed by canonical agent name.
        """
        yaml_config = self._load_yaml_config()
        definitions: Dict[str, Dict[str, Any]] = {}
        
        # Seed from channel definitions when available.
        channels = yaml_config.get('channels', {})
        if isinstance(channels, dict):
            for channel_name, channel_config in channels.items():
                if not isinstance(channel_config, dict):
                    continue
                canonical_name = str(channel_name).strip()
                if not canonical_name:
                    continue
                entry = definitions.setdefault(canonical_name, {})
                entry.setdefault('name', canonical_name)
                entrypoint = channel_config.get('entrypoint')
                if entrypoint:
                    entry.setdefault('entrypoint', entrypoint)
                description = channel_config.get('description')
                if description:
                    entry.setdefault('description', description)
                visibility = channel_config.get('visibility')
                targets = channel_config.get('targets')
                metadata = entry.setdefault('metadata', {})
                if isinstance(metadata, dict):
                    if visibility and 'visibility' not in metadata:
                        metadata['visibility'] = visibility
                    if targets and 'targets' not in metadata:
                        metadata['targets'] = list(targets)
        
        # Ensure agents listed in overrides exist in the mapping.
        api_config = yaml_config.get('api_config', {})
        overrides = api_config.get('agent_overrides', {})
        if isinstance(overrides, dict):
            for agent_name in overrides.keys():
                canonical_name = str(agent_name).strip()
                if not canonical_name:
                    continue
                entry = definitions.setdefault(canonical_name, {})
                entry.setdefault('name', canonical_name)
                # Record the override fragment for downstream consumers.
                override_payload = overrides.get(agent_name)
                if isinstance(override_payload, dict):
                    entry.setdefault('override', dict(override_payload))
        
        # Explicit registry bootstrap entries override previous data.
        registry_config = yaml_config.get('registry', {})
        bootstrap_config = None
        if isinstance(registry_config, dict):
            bootstrap_config = registry_config.get('bootstrap')
        
        def _merge_entry(name: str, payload: Dict[str, Any]) -> None:
            canonical_name = str(name).strip()
            if not canonical_name:
                return
            existing = definitions.setdefault(canonical_name, {})
            existing['name'] = canonical_name
            for key, value in payload.items():
                if value is None:
                    continue
                if key == 'aliases':
                    incoming = [str(item).strip() for item in value if str(item).strip()]
                    current = existing.get('aliases', [])
                    if not isinstance(current, list):
                        current = list(current) if current else []
                    merged = list(dict.fromkeys([*current, *incoming]))
                    existing['aliases'] = merged
                elif key == 'metadata' and isinstance(value, dict):
                    current_meta = existing.get('metadata', {})
                    if not isinstance(current_meta, dict):
                        current_meta = {}
                    merged_meta = {**current_meta, **value}
                    existing['metadata'] = merged_meta
                else:
                    existing[key] = value
        
        if isinstance(bootstrap_config, dict):
            for name, payload in bootstrap_config.items():
                if isinstance(payload, dict):
                    _merge_entry(name, dict(payload))
                else:
                    logger.warning(
                        "Ignoring registry.bootstrap entry with unsupported payload",
                        extra={"entry": name, "type": type(payload).__name__},
                    )
        elif isinstance(bootstrap_config, list):
            for item in bootstrap_config:
                if not isinstance(item, dict):
                    logger.warning(
                        "Ignoring non-mapping registry.bootstrap item",
                        extra={"type": type(item).__name__},
                    )
                    continue
                name = item.get('name')
                if not name:
                    logger.warning(
                        "Registry bootstrap item missing 'name' field; skipping",
                        extra={"item": item},
                    )
                    continue
                payload = dict(item)
                payload.pop('name', None)
                _merge_entry(str(name), payload)
        elif bootstrap_config is not None:
            logger.warning(
                "registry.bootstrap must be a mapping or list of mappings",
                extra={"provided_type": type(bootstrap_config).__name__},
            )
        
        return definitions
    
    def reload_config(self):
        """Reload configuration from file and clear cache."""
        self._yaml_config = None
        self._agent_configs.clear()
        self._browser_tool_configs.clear()
        logger.info("Configuration reloaded")


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance.
    
    Returns
    -------
    ConfigManager
        Global configuration manager.
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_agent_config(agent_name: str) -> OpenAIConfig:
    """Get OpenAI configuration for a specific agent.
    
    Parameters
    ----------
    agent_name:
        Name of the agent.
        
    Returns
    -------
    OpenAIConfig
        Configuration with agent-specific overrides applied.
    """
    return get_config_manager().get_agent_config(agent_name)


def get_agent_answer_verbose(agent_name: str) -> bool:
    """Get the answer verbosity setting for a specific agent.
    
    Parameters
    ----------
    agent_name:
        Name of the agent.
        
    Returns
    -------
    bool
        True if verbose answers are enabled, False for concise.
    """
    return get_config_manager().get_agent_answer_verbose(agent_name)


def get_registry_bootstrap() -> Dict[str, Dict[str, Any]]:
    """Return registry bootstrap definitions using the global manager."""
    return get_config_manager().get_registry_bootstrap()


def get_browser_tool_config(agent_name: str = "default") -> BrowserToolConfig:
    """Get browser tool configuration for a specific agent.
    
    Parameters
    ----------
    agent_name:
        Name of the agent.
        
    Returns
    -------
    BrowserToolConfig
        Configuration with agent-specific overrides applied.
    """
    return get_config_manager().get_browser_tool_config(agent_name)


def reload_config():
    """Reload the global configuration."""
    if _global_config_manager:
        _global_config_manager.reload_config()