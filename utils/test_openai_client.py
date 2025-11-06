"""Test suite for OpenAI client wrapper.

This module provides comprehensive tests for the OpenAI client wrapper
implementation, including unit tests and integration tests.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import List

from utils.openai_client import (
    OpenAIConfig,
    OpenAIClientWrapper,
    ChatMessage,
    OpenAIError,
    get_openai_client,
    reset_openai_client,
)


class TestOpenAIConfig:
    """Test cases for OpenAIConfig."""
    
    def test_from_env_success(self):
        """Test successful configuration loading from environment."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://api.test.com",
            "OPENAI_MODEL": "gpt-4",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "EMBEDDING_DIMENSION": "3072",
        }):
            config = OpenAIConfig.from_env()
            
            assert config.api_key == "test-key"
            assert config.base_url == "https://api.test.com"
            assert config.default_model == "gpt-4"
            assert config.embedding_model == "text-embedding-3-large"
            assert config.embedding_dimension == 3072
    
    def test_from_env_missing_api_key(self):
        """Test configuration loading with missing API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                OpenAIConfig.from_env()
    
    def test_from_env_defaults(self):
        """Test configuration loading with default values."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
        }):
            config = OpenAIConfig.from_env()
            
            assert config.api_key == "test-key"
            assert config.base_url is None
            assert config.default_model == "gpt-3.5-turbo"
            assert config.embedding_model == "text-embedding-3-small"
            assert config.embedding_dimension == 1536


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
    """Test cases for OpenAIClientWrapper."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return OpenAIConfig(
            api_key="test-key",
            base_url="https://api.test.com",
            default_model="gpt-4",
            embedding_model="text-embedding-3-large",
            timeout=30,
            max_retries=2,
        )
    
    @pytest.fixture
    def client_wrapper(self, mock_config):
        """Create a client wrapper instance for testing."""
        return OpenAIClientWrapper(mock_config)
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = Mock()
        mock_client.chat = Mock()
        mock_client.chat.completions = Mock()
        mock_client.embeddings = Mock()
        return mock_client
    
    def test_init_with_config(self, mock_config):
        """Test initialization with provided config."""
        wrapper = OpenAIClientWrapper(mock_config)
        assert wrapper.config == mock_config
    
    def test_init_without_config(self):
        """Test initialization without config (loads from env)."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
        }):
            wrapper = OpenAIClientWrapper()
            assert wrapper.config.api_key == "test-key"
    
    def test_client_property(self, client_wrapper, mock_openai_client):
        """Test client property creates client lazily."""
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client = client_wrapper.client
            assert client == mock_openai_client
            # Should not create client twice
            client2 = client_wrapper.client
            assert client2 == client
    
    def test_retry_with_backoff_success(self, client_wrapper):
        """Test retry logic with successful first attempt."""
        mock_func = Mock(return_value="success")
        
        result = client_wrapper._retry_with_backoff(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_retry_with_backoff_with_retries(self, client_wrapper):
        """Test retry logic with initial failure then success."""
        mock_func = Mock(side_effect=[Exception("fail"), "success"])
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client_wrapper._retry_with_backoff(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_with_backoff_exhausted(self, client_wrapper):
        """Test retry logic with all attempts failing."""
        mock_func = Mock(side_effect=Exception("fail"))
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(OpenAIError, match="All retries exhausted"):
                client_wrapper._retry_with_backoff(mock_func)
        
        assert mock_func.call_count == client_wrapper.config.max_retries + 1
    
    def test_get_chat_completion_with_dicts(self, client_wrapper, mock_openai_client):
        """Test chat completion with dict messages."""
        mock_response = Mock()
        mock_response.model = "gpt-4"
        mock_response.usage = Mock()
        mock_response.usage.model_dump.return_value = {"prompt_tokens": 10, "completion_tokens": 5}
        
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            # Reset the client to force recreation
            client_wrapper._client = None
            result = client_wrapper.get_chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4",
                temperature=0.5
            )
        
        assert result == mock_response
        mock_openai_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.5
        )
    
    def test_get_chat_completion_with_chatmessage_objects(self, client_wrapper, mock_openai_client):
        """Test chat completion with ChatMessage objects."""
        mock_response = Mock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        messages = [ChatMessage(role="user", content="Hello")]
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            # Reset() client to force recreation
            client_wrapper._client = None
            result = client_wrapper.get_chat_completion(messages)
        
        assert result == mock_response
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args[1]
        # ChatMessage.model_dump() includes name=None field, so we expect that
        assert call_args["messages"] == [{"role": "user", "content": "Hello", "name": None}]
    
    def test_get_chat_completion_empty_messages(self, client_wrapper):
        """Test chat completion with empty messages list."""
        with pytest.raises(OpenAIError, match="Messages list cannot be empty"):
            client_wrapper.get_chat_completion([])
    
    def test_get_chat_completion_invalid_message_format(self, client_wrapper):
        """Test chat completion with invalid message format."""
        with pytest.raises(OpenAIError, match="Invalid message format"):
            client_wrapper.get_chat_completion([{"invalid": "message"}])
    
    def test_get_embedding_single_text(self, client_wrapper, mock_openai_client):
        """Test embedding generation with single text."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_response.usage = Mock()
        mock_response.usage.model_dump.return_value = {"prompt_tokens": 5}
        
        mock_openai_client.embeddings.create.return_value = mock_response
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            result = client_wrapper.get_embedding("Hello world")
        
        assert result == mock_response.data
        mock_openai_client.embeddings.create.assert_called_once_with(
            model=client_wrapper.config.embedding_model,
            input=["Hello world"]
        )
    
    def test_get_embedding_multiple_texts(self, client_wrapper, mock_openai_client):
        """Test embedding generation with multiple texts."""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        texts = ["Hello", "World"]
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            result = client_wrapper.get_embedding(texts)
        
        assert result == mock_response.data
        mock_openai_client.embeddings.create.assert_called_once_with(
            model=client_wrapper.config.embedding_model,
            input=texts
        )
    
    def test_get_embedding_empty_texts(self, client_wrapper):
        """Test embedding generation with empty texts list."""
        with pytest.raises(OpenAIError, match="Texts list cannot be empty"):
            client_wrapper.get_embedding([])
    
    def test_get_embedding_invalid_text(self, client_wrapper):
        """Test embedding generation with invalid text."""
        with pytest.raises(OpenAIError, match="Invalid text at index 0"):
            client_wrapper.get_embedding([""])
    
    def test_get_embedding_vector(self, client_wrapper, mock_openai_client):
        """Test getting raw embedding vectors."""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            result = client_wrapper.get_embedding_vector(["Hello", "World"])
        
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    
    def test_get_embedding_vector_single_text(self, client_wrapper, mock_openai_client):
        """Test getting raw embedding vector for single text."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            result = client_wrapper.get_embedding_vector("Hello")
        
        assert result == [[0.1, 0.2, 0.3]]
    
    def test_validate_config_success(self, client_wrapper, mock_openai_client):
        """Test successful configuration validation."""
        mock_response = Mock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            result = client_wrapper.validate_config()
        
        assert result is True
    
    def test_validate_config_failure(self, client_wrapper, mock_openai_client):
        """Test configuration validation failure."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API error")
        
        with patch('utils.openai_client.OpenAI', return_value=mock_openai_client):
            client_wrapper._client = None
            with pytest.raises(OpenAIError, match="Configuration validation failed"):
                client_wrapper.validate_config()


class TestGlobalClient:
    """Test cases for global client functions."""
    
    def test_get_openai_client_singleton(self):
        """Test that get_openai_client returns the same instance."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client1 = get_openai_client()
            client2 = get_openai_client()
            assert client1 is client2
    
    def test_reset_openai_client(self):
        """Test reset_openai_client function."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            client1 = get_openai_client()
            reset_openai_client()
            client2 = get_openai_client()
            assert client1 is not client2


# Integration tests (these would require actual API keys in CI/CD)
class TestIntegration:
    """Integration tests for OpenAI client wrapper."""
    
    @pytest.mark.integration
    def test_real_chat_completion(self):
        """Test real chat completion with OpenAI API."""
        # This test would require real API keys and should only run in specific environments
        pass
    
    @pytest.mark.integration
    def test_real_embedding(self):
        """Test real embedding generation with OpenAI API."""
        # This test would require real API keys and should only run in specific environments
        pass


if __name__ == "__main__":
    pytest.main([__file__])