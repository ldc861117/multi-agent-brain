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
                else:
                    self._yaml_config = {}
                    logger.warning(f"Configuration file {self.config_path} not found, using defaults")
            except Exception as e:
                logger.error(f"Failed to load configuration from {self.config_path}: {e}")
                self._yaml_config = {}
        
        return self._yaml_config
    
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


def reload_config():
    """Reload the global configuration."""
    if _global_config_manager:
        _global_config_manager.reload_config()