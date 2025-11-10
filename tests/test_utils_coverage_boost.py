#!/usr/bin/env python3
"""Additional utils coverage tests to boost overall coverage.

These tests target simple code paths in utils modules that aren't
covered by existing integration tests.
"""

import pytest
from unittest.mock import patch, Mock


@pytest.mark.smoke
class TestProviderType:
    """Test ProviderType enum thoroughly."""
    
    def test_provider_type_values(self):
        """Test all provider type enum values."""
        from utils.openai_client import ProviderType
        
        assert ProviderType.OPENAI.value == 'openai'
        assert ProviderType.OLLAMA.value == 'ollama'
        assert ProviderType.CUSTOM.value == 'custom'
    
    def test_provider_type_string_representation(self):
        """Test provider type string representations."""
        from utils.openai_client import ProviderType
        
        assert str(ProviderType.OPENAI.value) == 'openai'
        assert str(ProviderType.OLLAMA.value) == 'ollama'
        assert str(ProviderType.CUSTOM.value) == 'custom'
    
    def test_provider_type_comparison(self):
        """Test provider type can be compared."""
        from utils.openai_client import ProviderType
        
        provider1 = ProviderType.OPENAI
        provider2 = ProviderType.OPENAI
        provider3 = ProviderType.OLLAMA
        
        assert provider1 == provider2
        assert provider1 != provider3


@pytest.mark.smoke
class TestChatAPIConfig:
    """Test ChatAPIConfig dataclass."""
    
    @patch.dict('os.environ', {
        'CHAT_API_KEY': 'test-key-123',
        'CHAT_API_BASE_URL': 'https://api.example.com/v1',
        'CHAT_API_PROVIDER': 'openai',
    }, clear=True)
    @patch('utils.openai_client.load_dotenv')
    def test_chat_api_config_from_env_basic(self, mock_load_dotenv):
        """Test ChatAPIConfig can load from environment."""
        from utils.openai_client import ChatAPIConfig
        
        config = ChatAPIConfig.from_env(load_env=False)
        
        assert config.api_key == 'test-key-123'
        assert config.base_url == 'https://api.example.com/v1'
    
    def test_chat_api_config_initialization(self):
        """Test ChatAPIConfig can be initialized directly."""
        from utils.openai_client import ChatAPIConfig, ProviderType
        
        config = ChatAPIConfig(
            api_key='test-key',
            base_url='https://api.example.com',
            model='gpt-4',
            provider=ProviderType.OPENAI
        )
        
        assert config.api_key == 'test-key'
        assert config.base_url == 'https://api.example.com'
        assert config.model == 'gpt-4'
        assert config.provider == ProviderType.OPENAI
        assert config.timeout == 30  # default
        assert config.max_retries == 3  # default


@pytest.mark.smoke
class TestEmbeddingAPIConfig:
    """Test EmbeddingAPIConfig dataclass."""
    
    def test_embedding_api_config_initialization(self):
        """Test EmbeddingAPIConfig can be initialized directly."""
        from utils.openai_client import EmbeddingAPIConfig, ProviderType
        
        config = EmbeddingAPIConfig(
            api_key='test-key',
            base_url='https://api.example.com',
            model='text-embedding-3-small',
            provider=ProviderType.OPENAI,
            dimension=1536
        )
        
        assert config.api_key == 'test-key'
        assert config.base_url == 'https://api.example.com'
        assert config.model == 'text-embedding-3-small'
        assert config.provider == ProviderType.OPENAI
        assert config.dimension == 1536
        assert config.timeout == 30  # default
    
    @patch.dict('os.environ', {
        'EMBEDDING_API_KEY': 'embed-key-123',
        'EMBEDDING_API_MODEL': 'text-embedding-ada-002',
        'EMBEDDING_API_PROVIDER': 'openai',
    }, clear=True)
    @patch('utils.openai_client.load_dotenv')
    def test_embedding_api_config_from_env_basic(self, mock_load_dotenv):
        """Test EmbeddingAPIConfig can load from environment."""
        from utils.openai_client import EmbeddingAPIConfig
        
        config = EmbeddingAPIConfig.from_env(load_env=False)
        
        assert config.api_key == 'embed-key-123'
        assert config.model == 'text-embedding-ada-002'


@pytest.mark.smoke
class TestOpenAIConfig:
    """Test OpenAIConfig composite class."""
    
    def test_openai_config_initialization(self):
        """Test OpenAIConfig can be initialized with chat and embedding configs."""
        from utils.openai_client import OpenAIConfig, ChatAPIConfig, EmbeddingAPIConfig, ProviderType
        
        chat_config = ChatAPIConfig(
            api_key='chat-key',
            model='gpt-4',
            provider=ProviderType.OPENAI
        )
        
        embedding_config = EmbeddingAPIConfig(
            api_key='embed-key',
            model='text-embedding-3-small',
            provider=ProviderType.OPENAI
        )
        
        config = OpenAIConfig(
            chat_api=chat_config,
            embedding_api=embedding_config
        )
        
        assert config.chat_api == chat_config
        assert config.embedding_api == embedding_config
    
    def test_openai_config_legacy_properties(self):
        """Test OpenAIConfig provides legacy property access."""
        from utils.openai_client import OpenAIConfig, ChatAPIConfig, EmbeddingAPIConfig, ProviderType
        
        chat_config = ChatAPIConfig(
            api_key='chat-key',
            base_url='https://api.openai.com/v1',
            model='gpt-4',
            provider=ProviderType.OPENAI
        )
        
        embedding_config = EmbeddingAPIConfig(
            api_key='embed-key',
            model='text-embedding-3-small',
            provider=ProviderType.OPENAI,
            dimension=1536
        )
        
        config = OpenAIConfig(
            chat_api=chat_config,
            embedding_api=embedding_config
        )
        
        # Test legacy properties
        assert config.api_key == 'chat-key'
        assert config.base_url == 'https://api.openai.com/v1'
        assert config.default_model == 'gpt-4'
        assert config.embedding_model == 'text-embedding-3-small'
        assert config.embedding_dimension == 1536


@pytest.mark.smoke
class TestConfigValidationError:
    """Test ConfigValidationError exception."""
    
    def test_config_validation_error_can_be_raised(self):
        """Test ConfigValidationError can be raised and caught."""
        from utils.config_validator import ConfigValidationError
        
        with pytest.raises(ConfigValidationError) as exc_info:
            raise ConfigValidationError("Test error message")
        
        assert "Test error message" in str(exc_info.value)
    
    def test_config_validation_error_is_exception(self):
        """Test ConfigValidationError is an Exception subclass."""
        from utils.config_validator import ConfigValidationError
        
        assert issubclass(ConfigValidationError, Exception)


@pytest.mark.smoke  
class TestOpenAIError:
    """Test OpenAIError exception."""
    
    def test_openai_error_can_be_raised(self):
        """Test OpenAIError can be raised and caught."""
        from utils.openai_client import OpenAIError
        
        with pytest.raises(OpenAIError) as exc_info:
            raise OpenAIError("Test OpenAI error")
        
        assert "Test OpenAI error" in str(exc_info.value)
    
    def test_openai_error_is_exception(self):
        """Test OpenAIError is an Exception subclass."""
        from utils.openai_client import OpenAIError
        
        assert issubclass(OpenAIError, Exception)


@pytest.mark.smoke
class TestChatMessage:
    """Test ChatMessage TypedDict."""
    
    def test_chat_message_structure(self):
        """Test ChatMessage can be created with correct structure."""
        from utils.openai_client import ChatMessage
        
        # ChatMessage is a TypedDict, so we just create a dict
        message: ChatMessage = {
            "role": "user",
            "content": "Hello, world!"
        }
        
        assert message["role"] == "user"
        assert message["content"] == "Hello, world!"
    
    def test_chat_message_system_role(self):
        """Test ChatMessage with system role."""
        from utils.openai_client import ChatMessage
        
        message: ChatMessage = {
            "role": "system",
            "content": "You are a helpful assistant."
        }
        
        assert message["role"] == "system"
        assert message["content"] == "You are a helpful assistant."


@pytest.mark.smoke
class TestAgentResponse:
    """Additional tests for AgentResponse."""
    
    def test_agent_response_with_metadata(self):
        """Test AgentResponse with complex metadata."""
        from agents.base import AgentResponse
        
        metadata = {
            "sources": ["doc1", "doc2"],
            "confidence": 0.95,
            "processing_time": 1.23
        }
        
        response = AgentResponse(
            content="Test response",
            metadata=metadata
        )
        
        assert response.content == "Test response"
        assert response.metadata["sources"] == ["doc1", "doc2"]
        assert response.metadata["confidence"] == 0.95
        assert response.metadata["processing_time"] == 1.23
    
    def test_agent_response_equality(self):
        """Test AgentResponse equality comparison."""
        from agents.base import AgentResponse
        
        resp1 = AgentResponse(content="test", metadata={"key": "value"})
        resp2 = AgentResponse(content="test", metadata={"key": "value"})
        resp3 = AgentResponse(content="different", metadata={"key": "value"})
        
        assert resp1 == resp2
        assert resp1 != resp3
