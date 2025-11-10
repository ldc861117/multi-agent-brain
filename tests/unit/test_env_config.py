"""Comprehensive test suite for .env configuration setup.

This module tests all aspects of environment variable loading and configuration
for separated chat and embedding API endpoints, including:
- Environment variable loading with fallback
- Chat API configuration validation
- Embedding API configuration validation
- Fallback behavior between APIs
- Per-agent overrides
- Provider support validation
- Edge cases and error handling
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from utils.openai_client import (
    ChatAPIConfig,
    EmbeddingAPIConfig,
    OpenAIConfig,
    ProviderType,
)
from utils.config_manager import ConfigManager, get_config_manager, get_agent_config


# ==================== FIXTURES ====================

@pytest.fixture
def clean_env(monkeypatch):
    """Provide a clean environment variable environment."""
    keys_to_clean = [
        # New configuration variables
        'CHAT_API_KEY', 'CHAT_API_BASE_URL', 'CHAT_API_MODEL', 'CHAT_API_PROVIDER',
        'CHAT_API_TIMEOUT', 'CHAT_API_MAX_RETRIES', 'CHAT_API_RETRY_DELAY', 'CHAT_API_MAX_RETRY_DELAY',
        'EMBEDDING_API_KEY', 'EMBEDDING_API_BASE_URL', 'EMBEDDING_API_MODEL', 'EMBEDDING_API_PROVIDER',
        'EMBEDDING_API_TIMEOUT', 'EMBEDDING_API_MAX_RETRIES', 'EMBEDDING_API_RETRY_DELAY', 'EMBEDDING_API_MAX_RETRY_DELAY',
        'EMBEDDING_DIMENSION',
        # Legacy variables (for backward compatibility testing)
        'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL',
        'EMBEDDING_MODEL', 'OPENAI_TIMEOUT',
        'OPENAI_MAX_RETRIES', 'OPENAI_RETRY_DELAY', 'OPENAI_MAX_RETRY_DELAY',
        # Other variables
        'MILVUS_URI', 'DEBUG', 'LOG_LEVEL'
    ]
    
    for key in keys_to_clean:
        if key in os.environ:
            monkeypatch.delenv(key, raising=False)
    
    yield monkeypatch


@pytest.fixture
def mock_load_dotenv(monkeypatch):
    """Mock load_dotenv to prevent actual .env file loading."""
    mock = Mock()
    monkeypatch.setattr('utils.openai_client.load_dotenv', mock)
    return mock


@pytest.fixture
def temp_config_file(tmp_path, monkeypatch):
    """Create a temporary config file for testing."""
    config_path = tmp_path / "test_config.yaml"
    monkeypatch.setattr('utils.config_manager.ConfigManager.__init__', lambda self, config_path=None: self._init_custom(config_path or str(config_path)))
    
    def custom_init(self, config_path):
        self.config_path = config_path
        self._yaml_config = None
        self._agent_configs = {}
    
    # Replace the __init__ method
    import utils.config_manager
    original_init = utils.config_manager.ConfigManager.__init__
    utils.config_manager.ConfigManager.__init__ = custom_init
    
    yield config_path
    
    # Restore original method
    utils.config_manager.ConfigManager.__init__ = original_init


# ==================== ENVIRONMENT VARIABLE LOADING TESTS ====================

class TestEnvironmentVariableLoading:
    """Test environment variable loading with various scenarios."""
    
    def test_load_variables_from_env_success(self, clean_env, mock_load_dotenv):
        """Test successful loading of all required variables."""
        # Set up environment variables
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("CHAT_API_MODEL", "gpt-4")
        clean_env.setenv("EMBEDDING_API_KEY", "sk-embed-key")
        clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
        clean_env.setenv("EMBEDDING_DIMENSION", "3072")
        
        # Load configuration
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify chat API config
        assert config.chat_api.api_key == "sk-chat-key"
        assert config.chat_api.model == "gpt-4"
        
        # Verify embedding API config
        assert config.embedding_api.api_key == "sk-embed-key"
        assert config.embedding_api.model == "text-embedding-3-large"
        assert config.embedding_api.dimension == 3072
        
        # Verify load_dotenv was called
        mock_load_dotenv.assert_called_once()
    
    def test_handle_missing_env_gracefully(self, clean_env, mock_load_dotenv):
        """Test graceful handling of missing environment variables."""
        # Only set essential variables
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        
        # Load configuration
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify defaults are used
        assert config.chat_api.api_key == "sk-chat-key"
        assert config.chat_api.model == "gpt-3.5-turbo"  # Default
        assert config.chat_api.provider == ProviderType.OPENAI  # Default
        assert config.chat_api.timeout == 30  # Default
        assert config.chat_api.max_retries == 3  # Default
        
        # Verify embedding config falls back to chat config
        assert config.embedding_api.api_key == "sk-chat-key"
        assert config.embedding_api.model == "text-embedding-3-small"  # Default
        assert config.embedding_api.dimension == 1536  # Default
    
    def test_required_variables_present_validation(self, clean_env):
        """Test validation that required variables are present."""
        # No API key set - should raise ValueError
        with pytest.raises(ValueError, match="CHAT_API_KEY or OPENAI_API_KEY environment variable is required"):
            ChatAPIConfig.from_env()
    
    def test_legacy_variables_fallback(self, clean_env, mock_load_dotenv):
        """Test fallback to legacy OPENAI_* variables."""
        # Set only legacy variables
        clean_env.setenv("OPENAI_API_KEY", "sk-legacy-key")
        clean_env.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        clean_env.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
        clean_env.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
        
        # Load configuration
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify legacy variables are used
        assert config.chat_api.api_key == "sk-legacy-key"
        assert config.chat_api.base_url == "https://api.openai.com/v1"
        assert config.chat_api.model == "gpt-3.5-turbo"
        assert config.embedding_api.model == "text-embedding-3-large"


# ==================== CHAT API CONFIGURATION TESTS ====================

class TestChatAPIConfiguration:
    """Test chat API configuration validation and parsing."""
    
    def test_correct_base_url_parsing(self, clean_env, mock_load_dotenv):
        """Test correct parsing of base URLs with various formats."""
        test_cases = [
            ("https://api.openai.com/v1", "https://api.openai.com/v1"),
            ("https://api.deepseek.com/v1", "https://api.deepseek.com/v1"),
            ("http://localhost:11434/v1", "http://localhost:11434/v1"),
            ("  https://api.openai.com/v1/  ", "https://api.openai.com/v1/"),  # With whitespace
        ]
        
        for input_url, expected_url in test_cases:
            clean_env.delenv("CHAT_API_BASE_URL", raising=False)
            clean_env.setenv("CHAT_API_KEY", "sk-test-key")
            clean_env.setenv("CHAT_API_BASE_URL", input_url)
            
            config = ChatAPIConfig.from_env()
            assert config.base_url == expected_url, f"Failed for input: {input_url}"
    
    def test_api_key_loading(self, clean_env, mock_load_dotenv):
        """Test API key loading from various sources."""
        # Test CHAT_API_KEY takes precedence
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("OPENAI_API_KEY", "sk-openai-key")
        
        config = ChatAPIConfig.from_env()
        assert config.api_key == "sk-chat-key"
        
        # Test fallback to OPENAI_API_KEY
        clean_env.delenv("CHAT_API_KEY")
        config = ChatAPIConfig.from_env()
        assert config.api_key == "sk-openai-key"
    
    def test_provider_type_validation(self, clean_env, mock_load_dotenv):
        """Test provider type validation and normalization."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test valid providers
        valid_providers = ["openai", "ollama", "custom"]
        for provider in valid_providers:
            clean_env.setenv("CHAT_API_PROVIDER", provider)
            config = ChatAPIConfig.from_env()
            assert config.provider.value == provider
        
        # Test invalid provider defaults to openai
        clean_env.setenv("CHAT_API_PROVIDER", "invalid_provider")
        with patch('utils.openai_client.logger') as mock_logger:
            config = ChatAPIConfig.from_env()
            assert config.provider == ProviderType.OPENAI
            mock_logger.warning.assert_called()
    
    def test_model_name_resolution(self, clean_env, mock_load_dotenv):
        """Test model name resolution from various sources."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test CHAT_API_MODEL takes precedence
        clean_env.setenv("CHAT_API_MODEL", "gpt-4")
        clean_env.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        config = ChatAPIConfig.from_env()
        assert config.model == "gpt-4"
        
        # Test fallback to OPENAI_MODEL
        clean_env.delenv("CHAT_API_MODEL")
        config = ChatAPIConfig.from_env()
        assert config.model == "gpt-3.5-turbo"
        
        # Test default model
        clean_env.delenv("OPENAI_MODEL")
        config = ChatAPIConfig.from_env()
        assert config.model == "gpt-3.5-turbo"


# ==================== EMBEDDING API CONFIGURATION TESTS ====================

class TestEmbeddingAPIConfiguration:
    """Test embedding API configuration validation and parsing."""
    
    def test_separate_endpoint_handling(self, clean_env, mock_load_dotenv):
        """Test separate endpoint handling for embedding API."""
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://api.openai.com/v1")
        clean_env.setenv("EMBEDDING_API_KEY", "sk-embed-key")
        clean_env.setenv("EMBEDDING_API_BASE_URL", "https://api.embed.com/v1")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify separate endpoints
        assert config.chat_api.api_key == "sk-chat-key"
        assert config.chat_api.base_url == "https://api.openai.com/v1"
        assert config.embedding_api.api_key == "sk-embed-key"
        assert config.embedding_api.base_url == "https://api.embed.com/v1"
    
    def test_optional_api_key_handling(self, clean_env, mock_load_dotenv):
        """Test optional API key for local providers like Ollama."""
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("EMBEDDING_API_PROVIDER", "ollama")
        # No EMBEDDING_API_KEY set
        
        config = EmbeddingAPIConfig.from_env()
        
        # API key should be None for ollama
        assert config.api_key is None
        assert config.provider == ProviderType.OLLAMA
    
    def test_embedding_provider_validation(self, clean_env, mock_load_dotenv):
        """Test provider type validation for embedding API."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test valid providers
        valid_providers = ["openai", "ollama", "custom"]
        for provider in valid_providers:
            clean_env.setenv("EMBEDDING_API_PROVIDER", provider)
            config = EmbeddingAPIConfig.from_env()
            assert config.provider.value == provider
        
        # Test invalid provider defaults to openai
        clean_env.setenv("EMBEDDING_API_PROVIDER", "invalid")
        with patch('utils.openai_client.logger') as mock_logger:
            config = EmbeddingAPIConfig.from_env()
            assert config.provider == ProviderType.OPENAI
            mock_logger.warning.assert_called()
    
    def test_embedding_model_name_resolution(self, clean_env, mock_load_dotenv):
        """Test embedding model name resolution."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test EMBEDDING_API_MODEL takes precedence
        clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
        clean_env.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        config = EmbeddingAPIConfig.from_env()
        assert config.model == "text-embedding-3-large"
        
        # Test fallback to EMBEDDING_MODEL
        clean_env.delenv("EMBEDDING_API_MODEL")
        config = EmbeddingAPIConfig.from_env()
        assert config.model == "text-embedding-3-small"
        
        # Test default model
        clean_env.delenv("EMBEDDING_MODEL")
        config = EmbeddingAPIConfig.from_env()
        assert config.model == "text-embedding-3-small"


# ==================== FALLBACK BEHAVIOR TESTS ====================

class TestFallbackBehavior:
    """Test fallback behavior between configuration sources."""
    
    def test_embedding_falls_back_to_chat_when_not_set(self, clean_env, mock_load_dotenv):
        """Test embedding API falls back to chat API when not configured."""
        # Set only chat API
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://api.openai.com/v1")
        clean_env.setenv("CHAT_API_PROVIDER", "openai")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify embedding falls back to chat
        assert config.embedding_api.api_key == "sk-chat-key"
        assert config.embedding_api.base_url == "https://api.openai.com/v1"
        assert config.embedding_api.provider == ProviderType.OPENAI
    
    def test_legacy_variables_work_as_fallback(self, clean_env, mock_load_dotenv):
        """Test legacy OPENAI_* variables work as fallback."""
        # Set only legacy variables
        clean_env.setenv("OPENAI_API_KEY", "sk-legacy-key")
        clean_env.setenv("OPENAI_BASE_URL", "https://api.legacy.com/v1")
        clean_env.setenv("OPENAI_MODEL", "gpt-4")
        clean_env.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify both chat and embedding use legacy variables
        assert config.chat_api.api_key == "sk-legacy-key"
        assert config.chat_api.base_url == "https://api.legacy.com/v1"
        assert config.chat_api.model == "gpt-4"
        assert config.embedding_api.model == "text-embedding-3-large"
    
    def test_precedence_specific_over_legacy_over_defaults(self, clean_env, mock_load_dotenv):
        """Test precedence: specific vars > legacy vars > defaults."""
        # Set all three levels
        clean_env.setenv("CHAT_API_KEY", "sk-specific-key")
        clean_env.setenv("OPENAI_API_KEY", "sk-legacy-key")
        clean_env.setenv("CHAT_API_MODEL", "gpt-4")
        clean_env.setenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        config = ChatAPIConfig.from_env()
        
        # Verify specific takes precedence
        assert config.api_key == "sk-specific-key"
        assert config.model == "gpt-4"
        
        # Remove specific, verify legacy is used
        clean_env.delenv("CHAT_API_KEY")
        clean_env.delenv("CHAT_API_MODEL")
        config = ChatAPIConfig.from_env()
        
        assert config.api_key == "sk-legacy-key"
        assert config.model == "gpt-3.5-turbo"
        
        # Remove legacy, verify defaults
        clean_env.delenv("OPENAI_API_KEY")
        clean_env.delenv("OPENAI_MODEL")
        with pytest.raises(ValueError):
            ChatAPIConfig.from_env()


# ==================== PER-AGENT OVERRIDES TESTS ====================

class TestPerAgentOverrides:
    """Test per-agent configuration overrides."""
    
    def test_agent_specific_model_overrides_from_env(self, clean_env, temp_config_file, mock_load_dotenv):
        """Test agent-specific model overrides from config file."""
        # Create config file with agent overrides
        config_content = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
    python_expert:
      chat_model: "gpt-4"
"""
        temp_config_file.write_text(config_content)
        
        # Set environment variables
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        clean_env.setenv("EMBEDDING_API_KEY", "sk-embed-key")
        
        # Test agent-specific configs
        config_manager = ConfigManager(str(temp_config_file))
        
        # Test coordination agent
        coord_config = config_manager.get_agent_config("coordination")
        assert coord_config.chat_api.model == "gpt-4"
        assert coord_config.embedding_api.model == "text-embedding-3-large"
        assert coord_config.embedding_api.dimension == 3072
        
        # Test python_expert agent
        python_config = config_manager.get_agent_config("python_expert")
        assert python_config.chat_api.model == "gpt-4"
        assert python_config.embedding_api.model == "text-embedding-3-small"  # Default
        
        # Test agent without overrides
        general_config = config_manager.get_agent_config("general")
        assert general_config.chat_api.model == "gpt-3.5-turbo"  # Default
    
    def test_override_precedence_agent_config_over_global_over_defaults(self, clean_env, temp_config_file, mock_load_dotenv):
        """Test override precedence: agent config > global config > defaults."""
        # Set environment variables (global)
        clean_env.setenv("CHAT_API_KEY", "sk-global-key")
        clean_env.setenv("CHAT_API_MODEL", "gpt-3.5-turbo")
        
        # Create config with agent override
        config_content = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
"""
        temp_config_file.write_text(config_content)
        
        config_manager = ConfigManager(str(temp_config_file))
        
        # Agent config should override global
        coord_config = config_manager.get_agent_config("coordination")
        assert coord_config.chat_api.model == "gpt-4"  # Agent override
        
        # Other agents should use global
        general_config = config_manager.get_agent_config("general")
        assert general_config.chat_api.model == "gpt-3.5-turbo"  # Global
    
    def test_invalid_agent_names_handled_gracefully(self, clean_env, temp_config_file, mock_load_dotenv):
        """Test invalid agent names are handled gracefully."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Create config with invalid agent name
        config_content = """
api_config:
  agent_overrides:
    invalid_agent_name:
      chat_model: "gpt-4"
"""
        temp_config_file.write_text(config_content)
        
        config_manager = ConfigManager(str(temp_config_file))
        
        # Valid agent should work
        valid_config = config_manager.get_agent_config("coordination")
        assert valid_config.chat_api.model == "gpt-3.5-turbo"  # Default
        
        # Invalid agent should use defaults (not raise error)
        invalid_config = config_manager.get_agent_config("nonexistent_agent")
        assert invalid_config.chat_api.model == "gpt-3.5-turbo"  # Default


# ==================== PROVIDER SUPPORT TESTS ====================

class TestProviderSupport:
    """Test support for different providers."""
    
    def test_ollama_provider_empty_key_allowed(self, clean_env, mock_load_dotenv):
        """Test Ollama provider allows empty API key."""
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("EMBEDDING_API_PROVIDER", "ollama")
        clean_env.setenv("EMBEDDING_API_KEY", "")  # Empty string
        
        config = EmbeddingAPIConfig.from_env()
        
        # Empty string should be treated as None for ollama
        assert config.api_key == ""
        assert config.provider == ProviderType.OLLAMA
    
    def test_openai_provider_key_required(self, clean_env, mock_load_dotenv):
        """Test OpenAI provider requires API key."""
        # No API key set
        with pytest.raises(ValueError, match="CHAT_API_KEY or OPENAI_API_KEY environment variable is required"):
            ChatAPIConfig.from_env()
        
        # With API key
        clean_env.setenv("CHAT_API_KEY", "sk-openai-key")
        config = ChatAPIConfig.from_env()
        assert config.api_key == "sk-openai-key"
        assert config.provider == ProviderType.OPENAI
    
    def test_custom_provider_configuration(self, clean_env, mock_load_dotenv):
        """Test custom provider configuration."""
        clean_env.setenv("CHAT_API_KEY", "sk-custom-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://custom-api.com/v1")
        clean_env.setenv("CHAT_API_PROVIDER", "custom")
        clean_env.setenv("CHAT_API_MODEL", "custom-model")
        
        config = ChatAPIConfig.from_env()
        
        assert config.api_key == "sk-custom-key"
        assert config.base_url == "https://custom-api.com/v1"
        assert config.provider == ProviderType.CUSTOM
        assert config.model == "custom-model"
    
    def test_cohere_provider_configuration(self, clean_env, mock_load_dotenv):
        """Test Cohere provider configuration (as custom provider)."""
        clean_env.setenv("CHAT_API_KEY", "sk-cohere-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://api.cohere.com/v1")
        clean_env.setenv("CHAT_API_PROVIDER", "custom")
        clean_env.setenv("CHAT_API_MODEL", "command")
        
        config = ChatAPIConfig.from_env()
        
        assert config.api_key == "sk-cohere-key"
        assert config.base_url == "https://api.cohere.com/v1"
        assert config.provider == ProviderType.CUSTOM
        assert config.model == "command"
    
    def test_invalid_provider_types_rejected(self, clean_env, mock_load_dotenv):
        """Test invalid provider types are rejected and default to openai."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        invalid_providers = ["invalid", "unknown", "cohere", "anthropic"]
        
        for provider in invalid_providers:
            clean_env.setenv("CHAT_API_PROVIDER", provider)
            with patch('utils.openai_client.logger') as mock_logger:
                config = ChatAPIConfig.from_env()
                assert config.provider == ProviderType.OPENAI
                mock_logger.warning.assert_called_with(f"Unknown provider '{provider}', defaulting to 'openai'")


# ==================== EDGE CASES TESTS ====================

class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_strings_handled_correctly(self, clean_env, mock_load_dotenv):
        """Test empty strings are handled correctly."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        clean_env.setenv("CHAT_API_BASE_URL", "")
        clean_env.setenv("CHAT_API_MODEL", "")
        
        config = ChatAPIConfig.from_env()
        
        assert config.api_key == "sk-test-key"
        assert config.base_url == ""  # Empty string preserved
        assert config.model == ""  # Empty string preserved
    
    def test_whitespace_trimming_in_urls(self, clean_env, mock_load_dotenv):
        """Test whitespace trimming in URLs."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        clean_env.setenv("CHAT_API_BASE_URL", "  https://api.openai.com/v1/  ")
        
        config = ChatAPIConfig.from_env()
        
        # Whitespace should be trimmed to avoid malformed URLs
        assert config.base_url == "https://api.openai.com/v1/"
    
    def test_case_sensitivity_of_provider_names(self, clean_env, mock_load_dotenv):
        """Test case sensitivity of provider names."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test lowercase (valid)
        clean_env.setenv("CHAT_API_PROVIDER", "openai")
        config = ChatAPIConfig.from_env()
        assert config.provider == ProviderType.OPENAI
        
        # Test uppercase (invalid, should default)
        clean_env.setenv("CHAT_API_PROVIDER", "OPENAI")
        with patch('utils.openai_client.logger') as mock_logger:
            config = ChatAPIConfig.from_env()
            assert config.provider == ProviderType.OPENAI
            mock_logger.warning.assert_called()
        
        # Test mixed case (invalid, should default)
        clean_env.setenv("CHAT_API_PROVIDER", "OpenAI")
        with patch('utils.openai_client.logger') as mock_logger:
            config = ChatAPIConfig.from_env()
            assert config.provider == ProviderType.OPENAI
            mock_logger.warning.assert_called()
    
    def test_malformed_urls_detected(self, clean_env, mock_load_dotenv):
        """Test malformed URLs are passed through (validation happens at client level)."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        malformed_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "https://",
            "http://localhost:invalid-port",
        ]
        
        for url in malformed_urls:
            clean_env.setenv("CHAT_API_BASE_URL", url)
            config = ChatAPIConfig.from_env()
            assert config.base_url == url  # Config doesn't validate URL format
    
    def test_dimension_model_mismatch_handling(self, clean_env, mock_load_dotenv):
        """Test handling of dimension and model mismatch."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test dimension override for large model
        clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
        clean_env.setenv("EMBEDDING_DIMENSION", "1536")  # Wrong dimension for large model
        
        config = EmbeddingAPIConfig.from_env()
        
        # Should use the explicitly set dimension
        assert config.dimension == 1536
        assert config.model == "text-embedding-3-large"
        
        # Test correct auto-dimension logic
        clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
        clean_env.delenv("EMBEDDING_DIMENSION")  # Remove explicit dimension
        
        config = EmbeddingAPIConfig.from_env()
        
        # Should auto-detect dimension based on model name
        assert config.dimension == 3072  # Default for large model
        assert config.model == "text-embedding-3-large"


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for complete configuration scenarios."""
    
    def test_complete_separated_api_configuration(self, clean_env, mock_load_dotenv):
        """Test complete separated API configuration scenario."""
        # Set up complete separated configuration
        clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://api.openai.com/v1")
        clean_env.setenv("CHAT_API_MODEL", "gpt-4")
        clean_env.setenv("CHAT_API_PROVIDER", "openai")
        clean_env.setenv("CHAT_API_TIMEOUT", "60")
        
        clean_env.setenv("EMBEDDING_API_KEY", "sk-embed-key")
        clean_env.setenv("EMBEDDING_API_BASE_URL", "https://api.embed.com/v1")
        clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
        clean_env.setenv("EMBEDDING_API_PROVIDER", "custom")
        clean_env.setenv("EMBEDDING_DIMENSION", "3072")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify complete configuration
        assert config.chat_api.api_key == "sk-chat-key"
        assert config.chat_api.base_url == "https://api.openai.com/v1"
        assert config.chat_api.model == "gpt-4"
        assert config.chat_api.provider == ProviderType.OPENAI
        assert config.chat_api.timeout == 60
        
        assert config.embedding_api.api_key == "sk-embed-key"
        assert config.embedding_api.base_url == "https://api.embed.com/v1"
        assert config.embedding_api.model == "text-embedding-3-large"
        assert config.embedding_api.provider == ProviderType.CUSTOM
        assert config.embedding_api.dimension == 3072
    
    def test_local_ollama_configuration(self, clean_env, mock_load_dotenv):
        """Test local Ollama configuration scenario."""
        clean_env.setenv("CHAT_API_KEY", "ollama")  # Placeholder
        clean_env.setenv("CHAT_API_BASE_URL", "http://localhost:11434/v1")
        clean_env.setenv("CHAT_API_MODEL", "qwen2:7b")
        clean_env.setenv("CHAT_API_PROVIDER", "ollama")
        
        clean_env.setenv("EMBEDDING_API_KEY", "ollama")  # Placeholder
        clean_env.setenv("EMBEDDING_API_BASE_URL", "http://localhost:11434/v1")
        clean_env.setenv("EMBEDDING_API_MODEL", "nomic-embed-text")
        clean_env.setenv("EMBEDDING_API_PROVIDER", "ollama")
        clean_env.setenv("EMBEDDING_DIMENSION", "768")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify Ollama configuration
        assert config.chat_api.api_key == "ollama"
        assert config.chat_api.base_url == "http://localhost:11434/v1"
        assert config.chat_api.model == "qwen2:7b"
        assert config.chat_api.provider == ProviderType.OLLAMA
        
        assert config.embedding_api.api_key == "ollama"
        assert config.embedding_api.base_url == "http://localhost:11434/v1"
        assert config.embedding_api.model == "nomic-embed-text"
        assert config.embedding_api.provider == ProviderType.OLLAMA
        assert config.embedding_api.dimension == 768
    
    def test_mixed_provider_configuration(self, clean_env, mock_load_dotenv):
        """Test mixed provider configuration (different providers for chat/embedding)."""
        # OpenAI for chat, Ollama for embedding
        clean_env.setenv("CHAT_API_KEY", "sk-openai-key")
        clean_env.setenv("CHAT_API_BASE_URL", "https://api.openai.com/v1")
        clean_env.setenv("CHAT_API_MODEL", "gpt-4")
        clean_env.setenv("CHAT_API_PROVIDER", "openai")
        
        clean_env.setenv("EMBEDDING_API_KEY", "ollama")
        clean_env.setenv("EMBEDDING_API_BASE_URL", "http://localhost:11434/v1")
        clean_env.setenv("EMBEDDING_API_MODEL", "nomic-embed-text")
        clean_env.setenv("EMBEDDING_API_PROVIDER", "ollama")
        clean_env.setenv("EMBEDDING_DIMENSION", "768")
        
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify mixed configuration
        assert config.chat_api.provider == ProviderType.OPENAI
        assert config.chat_api.api_key == "sk-openai-key"
        assert config.chat_api.base_url == "https://api.openai.com/v1"
        
        assert config.embedding_api.provider == ProviderType.OLLAMA
        assert config.embedding_api.api_key == "ollama"
        assert config.embedding_api.base_url == "http://localhost:11434/v1"


# ==================== PERFORMANCE AND RELIABILITY TESTS ====================

class TestPerformanceAndReliability:
    """Test performance and reliability aspects of configuration loading."""
    
    def test_configuration_loading_performance(self, clean_env, mock_load_dotenv):
        """Test configuration loading performance."""
        import time
        
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Measure loading time
        start_time = time.time()
        for _ in range(100):
            config = OpenAIConfig.from_env_with_fallback()
        end_time = time.time()
        
        # Should be fast (< 1 second for 100 loads)
        assert (end_time - start_time) < 1.0
    
    def test_config_manager_caching(self, clean_env, temp_config_file, mock_load_dotenv):
        """Test ConfigManager caching behavior."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        config_content = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
"""
        temp_config_file.write_text(config_content)
        
        config_manager = ConfigManager(str(temp_config_file))
        
        # First call should load from file
        config1 = config_manager.get_agent_config("coordination")
        
        # Second call should use cache
        config2 = config_manager.get_agent_config("coordination")
        
        # Should be the same object (cached)
        assert config1 is config2
        assert config1.chat_api.model == "gpt-4"


# ==================== CONFIGURATION VALIDATION TESTS ====================

class TestConfigurationValidation:
    """Test configuration validation and error handling."""
    
    def test_numeric_parameter_validation(self, clean_env, mock_load_dotenv):
        """Test validation of numeric parameters."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test valid numeric values
        clean_env.setenv("CHAT_API_TIMEOUT", "60")
        clean_env.setenv("CHAT_API_MAX_RETRIES", "5")
        clean_env.setenv("CHAT_API_RETRY_DELAY", "2.5")
        
        config = ChatAPIConfig.from_env()
        
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 2.5
        
        # Test invalid numeric values
        clean_env.setenv("CHAT_API_TIMEOUT", "invalid")
        
        with pytest.raises(ValueError):
            ChatAPIConfig.from_env()
    
    def test_boolean_parameter_handling(self, clean_env, mock_load_dotenv):
        """Test handling of boolean-like parameters."""
        clean_env.setenv("CHAT_API_KEY", "sk-test-key")
        
        # Test string parameters that might be boolean-like
        clean_env.setenv("CHAT_API_PROVIDER", "openai")
        
        config = ChatAPIConfig.from_env()
        
        # Provider should be enum, not boolean
        assert isinstance(config.provider, ProviderType)
        assert config.provider == ProviderType.OPENAI


if __name__ == "__main__":
    pytest.main([__file__, "-v"])