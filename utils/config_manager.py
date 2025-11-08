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

from .config_validator import ConfigValidator, ConfigValidationError
from .openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType


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
    
    def get_global_config(self) -> OpenAIConfig:
        """Get the global OpenAI configuration."""
        return OpenAIConfig.from_env_with_fallback()
    
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
        
        # Apply overrides with environment variable precedence
        # Environment variables should take precedence, but YAML overrides should work when env vars are not set
        
        # For chat model: check if environment variable is different from global default
        chat_model = global_config.chat_api.model
        if (chat_model == "gpt-3.5-turbo" and  # Using default
            agent_override.get('chat_model') and 
            agent_override.get('chat_model') != "gpt-3.5-turbo"):  # YAML has non-default
            # No environment override, use YAML override
            chat_model = agent_override.get('chat_model')
        
        # For embedding model: same logic
        embedding_model = global_config.embedding_api.model
        if (embedding_model == "text-embedding-3-small" and  # Using default
            agent_override.get('embedding_model') and 
            agent_override.get('embedding_model') != "text-embedding-3-small"):  # YAML has non-default
            # No environment override, use YAML override
            embedding_model = agent_override.get('embedding_model')
            
        # For embedding dimension: same logic
        embedding_dimension = global_config.embedding_api.dimension
        if (embedding_dimension == 1536 and  # Using default
            agent_override.get('embedding_dimension') and 
            agent_override.get('embedding_dimension') != 1536):  # YAML has non-default
            # No environment override, use YAML override
            embedding_dimension = agent_override.get('embedding_dimension')
        
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
            f"Applied configuration overrides for agent '{agent_name}'",
            extra={
                "agent": agent_name,
                "chat_model": agent_config.chat_api.model,
                "embedding_model": agent_config.embedding_api.model,
                "embedding_dimension": agent_config.embedding_api.dimension,
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
    
    def reload_config(self):
        """Reload configuration from file and clear cache."""
        self._yaml_config = None
        self._agent_configs.clear()
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


def reload_config():
    """Reload the global configuration."""
    if _global_config_manager:
        _global_config_manager.reload_config()