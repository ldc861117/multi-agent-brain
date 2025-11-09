"""Test suite for OpenAI client wrapper using pytest monkeypatch.

This module provides focused tests for the core issue that was failing.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from utils.openai_client import (
    ChatAPIConfig,
    EmbeddingAPIConfig,
    OpenAIConfig,
    OpenAIClientWrapper,
    ChatMessage,
    OpenAIError,
    ProviderType,
    get_openai_client,
    reset_openai_client,
)


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
    """Mock load_dotenv() to prevent loading .env files."""
    with patch('utils.openai_client.load_dotenv') as mock:
        mock.return_value = None
        yield mock


@pytest.fixture(autouse=True)
def reset_global_state():
    """Auto-reset global state between tests to prevent pollution."""
    yield
    reset_openai_client()


# ==================== TEST CLASSES ====================

class TestOpenAIConfig:
    """Configuration loading tests with proper environment isolation."""
    
    def test_from_env_defaults(self, clean_env, mock_load_dotenv):
        """
        Test default configuration loading with clean environment.
        
        This is the updated version for the new configuration structure.
        """
        # Set only the required API key (legacy for backward compatibility)
        clean_env.setenv('OPENAI_API_KEY', 'sk-test-key')
        
        # Load configuration
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify chat API defaults
        assert config.chat_api.api_key == 'sk-test-key'
        assert config.chat_api.base_url is None
        assert config.chat_api.model == 'gpt-3.5-turbo'
        assert config.chat_api.provider == ProviderType.OPENAI
        assert config.chat_api.timeout == 30
        assert config.chat_api.max_retries == 3
        assert config.chat_api.retry_delay == 1.0
        assert config.chat_api.max_retry_delay == 60.0
        
        # Verify embedding API defaults (fallback to chat API)
        assert config.embedding_api.api_key == 'sk-test-key'
        assert config.embedding_api.base_url is None
        assert config.embedding_api.model == 'text-embedding-3-small'
        assert config.embedding_api.provider == ProviderType.OPENAI
        assert config.embedding_api.dimension == 1536
        assert config.embedding_api.timeout == 30
        assert config.embedding_api.max_retries == 3
        assert config.embedding_api.retry_delay == 1.0
        assert config.embedding_api.max_retry_delay == 60.0
        
        # Verify legacy properties
        assert config.api_key == 'sk-test-key'
        assert config.base_url is None
        assert config.default_model == 'gpt-3.5-turbo'
        assert config.embedding_model == 'text-embedding-3-small'
        assert config.embedding_dimension == 1536
    
    def test_from_env_custom_base_url(self, clean_env, mock_load_dotenv):
        """Test custom base_url configuration."""
        clean_env.setenv('OPENAI_API_KEY', 'key')
        clean_env.setenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
        clean_env.setenv('OPENAI_MODEL', 'deepseek-chat')
        
        config = OpenAIConfig.from_env()
        
        assert config.api_key == 'key'
        assert config.base_url == 'https://api.deepseek.com/v1'
        assert config.default_model == 'deepseek-chat'
    
    def test_separate_chat_embedding_config(self, clean_env, mock_load_dotenv):
        """Test separate configuration for chat and embedding APIs."""
        # Set separate configurations
        clean_env.setenv('CHAT_API_KEY', 'sk-chat-key')
        clean_env.setenv('CHAT_API_BASE_URL', 'https://api.openai.com/v1')
        clean_env.setenv('CHAT_API_MODEL', 'gpt-4')
        clean_env.setenv('CHAT_API_PROVIDER', 'openai')
        
        clean_env.setenv('EMBEDDING_API_KEY', 'sk-embedding-key')
        clean_env.setenv('EMBEDDING_API_BASE_URL', 'http://localhost:11434/v1')
        clean_env.setenv('EMBEDDING_API_MODEL', 'nomic-embed-text')
        clean_env.setenv('EMBEDDING_API_PROVIDER', 'ollama')
        clean_env.setenv('EMBEDDING_DIMENSION', '768')
        
        # Load configuration
        config = OpenAIConfig.from_env()
        
        # Verify chat API configuration
        assert config.chat_api.api_key == 'sk-chat-key'
        assert config.chat_api.base_url == 'https://api.openai.com/v1'
        assert config.chat_api.model == 'gpt-4'
        assert config.chat_api.provider == ProviderType.OPENAI
        
        # Verify embedding API configuration
        assert config.embedding_api.api_key == 'sk-embedding-key'
        assert config.embedding_api.base_url == 'http://localhost:11434/v1'
        assert config.embedding_api.model == 'nomic-embed-text'
        assert config.embedding_api.provider == ProviderType.OLLAMA
        assert config.embedding_api.dimension == 768
    
    def test_embedding_config_fallback_to_chat(self, clean_env, mock_load_dotenv):
        """Test fallback behavior when embedding config is not set."""
        # Set only chat configuration
        clean_env.setenv('CHAT_API_KEY', 'sk-chat-key')
        clean_env.setenv('CHAT_API_BASE_URL', 'https://api.deepseek.com/v1')
        clean_env.setenv('CHAT_API_MODEL', 'deepseek-chat')
        
        # Load configuration with fallback
        config = OpenAIConfig.from_env_with_fallback()
        
        # Chat API should be configured
        assert config.chat_api.api_key == 'sk-chat-key'
        assert config.chat_api.base_url == 'https://api.deepseek.com/v1'
        assert config.chat_api.model == 'deepseek-chat'
        
        # Embedding API should fall back to chat API settings
        assert config.embedding_api.api_key == 'sk-chat-key'
        assert config.embedding_api.base_url == 'https://api.deepseek.com/v1'
        assert config.embedding_api.provider == ProviderType.OPENAI  # Default provider
    
    def test_legacy_compatibility(self, clean_env, mock_load_dotenv):
        """Test backward compatibility with legacy environment variables."""
        # Set legacy variables
        clean_env.setenv('OPENAI_API_KEY', 'sk-legacy-key')
        clean_env.setenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
        clean_env.setenv('OPENAI_MODEL', 'deepseek-chat')
        clean_env.setenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        clean_env.setenv('EMBEDDING_DIMENSION', '3072')
        
        # Load configuration with fallback
        config = OpenAIConfig.from_env_with_fallback()
        
        # Verify legacy variables are used
        assert config.chat_api.api_key == 'sk-legacy-key'
        assert config.chat_api.base_url == 'https://api.deepseek.com/v1'
        assert config.chat_api.model == 'deepseek-chat'
        assert config.embedding_api.model == 'text-embedding-3-large'
        assert config.embedding_api.dimension == 3072
        
        # Verify legacy properties work
        assert config.api_key == 'sk-legacy-key'
        assert config.base_url == 'https://api.deepseek.com/v1'
        assert config.default_model == 'deepseek-chat'
        assert config.embedding_model == 'text-embedding-3-large'
        assert config.embedding_dimension == 3072

    def test_missing_api_key_error(self, clean_env, mock_load_dotenv):
        """Test configuration loading with missing API key."""
        # Don't set any environment variables
        
        with pytest.raises(ValueError, match="CHAT_API_KEY or OPENAI_API_KEY environment variable is required"):
            ChatAPIConfig.from_env()


class TestConfigManager:
    """Test cases for configuration manager."""
    
    def test_get_global_config(self, clean_env, mock_load_dotenv):
        """Test getting global configuration."""
        clean_env.setenv('OPENAI_API_KEY', 'sk-test-key')
        
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        config = config_manager.get_global_config()
        
        assert config.chat_api.api_key == 'sk-test-key'
        assert config.embedding_api.api_key == 'sk-test-key'
    
    def test_get_agent_config_no_override(self, clean_env, mock_load_dotenv, tmp_path):
        """Test getting agent config without overrides."""
        clean_env.setenv('OPENAI_API_KEY', 'sk-test-key')
        
        # Create a temporary config file
        config_content = """
api_config:
  agent_overrides:
    some_other_agent:
      chat_model: "gpt-4"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        from utils.config_manager import ConfigManager
        config_manager = ConfigManager(str(config_file))
        
        # Test agent without override
        config = config_manager.get_agent_config("coordination")
        assert config.chat_api.model == "gpt-3.5-turbo"  # Default
    
    def test_get_agent_config_with_override(self, clean_env, mock_load_dotenv, tmp_path):
        """Test getting agent config with overrides."""
        clean_env.setenv('OPENAI_API_KEY', 'sk-test-key')
        
        # Create a temporary config file with overrides
        config_content = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        from utils.config_manager import ConfigManager
        config_manager = ConfigManager(str(config_file))
        
        # Test agent with override
        config = config_manager.get_agent_config("coordination")
        assert config.chat_api.model == "gpt-4"
        assert config.embedding_api.model == "text-embedding-3-large"
        assert config.embedding_api.dimension == 3072


class TestChatMessage:
    """Test cases for ChatMessage model."""
    
    def test_chat_message_creation(self):
        """Test ChatMessage creation."""
        message = ChatMessage(role="user", content="Hello, world!")
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.name is None
    
    def test_chat_message_with_name(self):
        """Test ChatMessage creation with name."""
        message = ChatMessage(
            role="user",
            content="Hello, world!",
            name="test_user"
        )
        assert message.name == "test_user"


class TestOpenAIClientWrapper:
    """OpenAI client wrapper tests."""
    
    def test_initialization(self, clean_env, mock_load_dotenv):
        """Test client wrapper initialization."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key-123')
        
        config = OpenAIConfig.from_env()
        
        with patch('utils.openai_client.openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            
            client = OpenAIClientWrapper(config)
            
            assert client.config == config
            assert client._chat_client is None  # Should be lazy loaded
            assert client._embedding_client is None  # Should be lazy loaded
            mock_openai.assert_not_called()  # Should not create client yet
    
    def test_get_chat_completion_basic(self, clean_env, mock_load_dotenv):
        """Test basic chat completion."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key-123')
        
        config = OpenAIConfig.from_env()
        
        with patch('utils.openai_client.openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            
            client = OpenAIClientWrapper(config)
            client._chat_client = mock_openai.return_value
            
            # Mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = 'Test response'
            mock_response.model = "gpt-3.5-turbo"
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"prompt_tokens": 10, "completion_tokens": 5}
            
            client.chat_client.chat.completions.create.return_value = mock_response
            
            messages = [{"role": "user", "content": "Hello"}]
            response = client.get_chat_completion(messages)
            
            assert response == mock_response
            client.chat_client.chat.completions.create.assert_called_once_with(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
    
    def test_get_embedding_single_text(self, clean_env, mock_load_dotenv):
        """Test embedding generation with single text."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key-123')
        
        config = OpenAIConfig.from_env()
        
        with patch('utils.openai_client.openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            
            client = OpenAIClientWrapper(config)
            client._embedding_client = mock_openai.return_value
            
            # Mock response
            mock_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
            mock_response = MagicMock()
            mock_response.data = [MagicMock()]
            mock_response.data[0].embedding = mock_embedding
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"prompt_tokens": 5}
            
            client.embedding_client.embeddings.create.return_value = mock_response
            
            text = "Test text"
            result = client.get_embedding(text)
            
            assert len(result) == 1
            assert result[0].embedding == mock_embedding
            client.embedding_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input=["Test text"]
            )
    
    def test_get_embedding_vector(self, clean_env, mock_load_dotenv):
        """Test getting raw embedding vectors."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key-123')
        
        config = OpenAIConfig.from_env()
        
        with patch('utils.openai_client.openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            
            client = OpenAIClientWrapper(config)
            client._embedding_client = mock_openai.return_value
            
            # Mock response
            mock_vector = [0.1, 0.2, 0.3] * 512
            mock_response = MagicMock()
            mock_response.data = [MagicMock()]
            mock_response.data[0].embedding = mock_vector
            
            client.embedding_client.embeddings.create.return_value = mock_response
            
            text = "Test"
            vector = client.get_embedding_vector(text)
            
            assert len(vector) == 1
            assert vector[0] == mock_vector
            assert isinstance(vector, list)
            assert isinstance(vector[0], list)


class TestGlobalClient:
    """Global client tests."""
    
    def test_get_openai_client_singleton(self, clean_env, mock_load_dotenv):
        """Test that get_openai_client returns the same instance."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key')
        
        with patch('utils.openai_client.openai.OpenAI'):
            reset_openai_client()
            
            client1 = get_openai_client()
            client2 = get_openai_client()
            
            assert client1 is client2
    
    def test_reset_openai_client(self, clean_env, mock_load_dotenv):
        """Test reset_openai_client function."""
        clean_env.setenv('OPENAI_API_KEY', 'key1')
        
        with patch('utils.openai_client.openai.OpenAI'):
            reset_openai_client()
            client1 = get_openai_client()
            
            reset_openai_client()
            client2 = get_openai_client()
            
            # Reset should create different instances
            assert client1 is not client2


if __name__ == "__main__":
    pytest.main([__file__])