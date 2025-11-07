"""Test suite for OpenAI client wrapper using pytest monkeypatch.

This module provides focused tests for the core issue that was failing.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from utils.openai_client import (
    OpenAIConfig,
    OpenAIClientWrapper,
    ChatMessage,
    OpenAIError,
    get_openai_client,
    reset_openai_client,
)


# ==================== FIXTURES ====================

@pytest.fixture
def clean_env(monkeypatch):
    """Provide a clean environment variable environment."""
    keys_to_clean = [
        'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_MODEL',
        'EMBEDDING_MODEL', 'EMBEDDING_DIMENSION', 'OPENAI_TIMEOUT',
        'OPENAI_MAX_RETRIES', 'OPENAI_RETRY_DELAY', 'OPENAI_MAX_RETRY_DELAY',
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
        
        This is the fixed version of the failing test.
        """
        # Set only the required API key
        clean_env.setenv('OPENAI_API_KEY', 'sk-test-key')
        
        # Load configuration
        config = OpenAIConfig.from_env()
        
        # Verify defaults
        assert config.api_key == 'sk-test-key'
        assert config.base_url is None  # ✅ Fixed: Now correctly None
        assert config.default_model == 'gpt-3.5-turbo'
        assert config.embedding_model == 'text-embedding-3-small'
        assert config.embedding_dimension == 1536
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.max_retry_delay == 60.0
    
    def test_from_env_custom_base_url(self, clean_env, mock_load_dotenv):
        """Test custom base_url configuration."""
        clean_env.setenv('OPENAI_API_KEY', 'key')
        clean_env.setenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1')
        clean_env.setenv('OPENAI_MODEL', 'deepseek-chat')
        
        config = OpenAIConfig.from_env()
        
        assert config.api_key == 'key'
        assert config.base_url == 'https://api.deepseek.com/v1'
        assert config.default_model == 'deepseek-chat'
    
    def test_from_env_missing_api_key(self, clean_env, mock_load_dotenv):
        """Test configuration loading with missing API key."""
        # Don't set any environment variables
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
            OpenAIConfig.from_env()


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
            assert client._client is None  # Should be lazy loaded
            mock_openai.assert_not_called()  # Should not create client yet
    
    def test_get_chat_completion_basic(self, clean_env, mock_load_dotenv):
        """Test basic chat completion."""
        clean_env.setenv('OPENAI_API_KEY', 'test-key-123')
        
        config = OpenAIConfig.from_env()
        
        with patch('utils.openai_client.openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock()
            
            client = OpenAIClientWrapper(config)
            client._client = mock_openai.return_value
            
            # Mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = 'Test response'
            mock_response.model = "gpt-3.5-turbo"
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"prompt_tokens": 10, "completion_tokens": 5}
            
            client.client.chat.completions.create.return_value = mock_response
            
            messages = [{"role": "user", "content": "Hello"}]
            response = client.get_chat_completion(messages)
            
            assert response == mock_response
            client.client.chat.completions.create.assert_called_once_with(
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
            client._client = mock_openai.return_value
            
            # Mock response
            mock_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
            mock_response = MagicMock()
            mock_response.data = [MagicMock()]
            mock_response.data[0].embedding = mock_embedding
            mock_response.usage = MagicMock()
            mock_response.usage.model_dump.return_value = {"prompt_tokens": 5}
            
            client.client.embeddings.create.return_value = mock_response
            
            text = "Test text"
            result = client.get_embedding(text)
            
            assert len(result) == 1
            assert result[0].embedding == mock_embedding
            client.client.embeddings.create.assert_called_once_with(
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
            client._client = mock_openai.return_value
            
            # Mock response
            mock_vector = [0.1, 0.2, 0.3] * 512
            mock_response = MagicMock()
            mock_response.data = [MagicMock()]
            mock_response.data[0].embedding = mock_vector
            
            client.client.embeddings.create.return_value = mock_response
            
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