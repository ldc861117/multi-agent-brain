#!/usr/bin/env python3
"""Smoke tests for agent imports and basic structure validation.

These tests ensure all agent modules can be imported without external
dependencies and that key symbols/classes are properly exposed.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock


@pytest.fixture(autouse=True)
def mock_external_deps():
    """Mock external dependencies before imports to avoid network/service calls."""
    # Mock pymilvus
    mock_pymilvus = MagicMock()
    mock_pymilvus.connections = Mock()
    mock_pymilvus.Collection = Mock
    mock_pymilvus.CollectionSchema = Mock
    mock_pymilvus.DataType = Mock()
    mock_pymilvus.DataType.INT64 = 'INT64'
    mock_pymilvus.DataType.VARCHAR = 'VARCHAR'
    mock_pymilvus.DataType.FLOAT_VECTOR = 'FLOAT_VECTOR'
    mock_pymilvus.FieldSchema = Mock
    mock_pymilvus.MilvusException = type('MilvusException', (Exception,), {})
    mock_pymilvus.utility = Mock()
    sys.modules['pymilvus'] = mock_pymilvus
    
    # Mock numpy
    mock_numpy = MagicMock()
    mock_numpy.array = lambda x: x
    sys.modules['numpy'] = mock_numpy
    
    yield
    
    # Cleanup not necessary as tests run in same process


@pytest.mark.smoke
class TestAgentImports:
    """Test that all agent modules can be imported."""
    
    def test_base_agent_imports(self):
        """Test base agent protocol imports."""
        from agents.base import BaseAgent, AgentResponse
        assert BaseAgent is not None
        assert AgentResponse is not None
        assert hasattr(BaseAgent, 'handle_message')
        assert hasattr(BaseAgent, 'name')
        assert hasattr(BaseAgent, 'description')
    
    def test_agent_response_structure(self):
        """Test AgentResponse dataclass."""
        from agents.base import AgentResponse
        response = AgentResponse(content="test", metadata={"key": "value"})
        assert response.content == "test"
        assert response.metadata == {"key": "value"}
        
        # Test default metadata
        response2 = AgentResponse(content="test2")
        assert response2.metadata == {}
    
    def test_general_agent_imports(self):
        """Test general agent can be imported."""
        from agents.general import GeneralAgent
        assert GeneralAgent is not None
        assert hasattr(GeneralAgent, 'handle_message')
    
    def test_coordination_agent_imports(self):
        """Test coordination agent can be imported."""
        from agents.coordination import CoordinationAgent
        assert CoordinationAgent is not None
        assert hasattr(CoordinationAgent, 'handle_message')
    
    def test_python_expert_imports(self):
        """Test python expert agent can be imported."""
        from agents.python_expert import PythonExpertAgent
        assert PythonExpertAgent is not None
        assert hasattr(PythonExpertAgent, 'handle_message')
    
    def test_milvus_expert_imports(self):
        """Test milvus expert agent can be imported."""
        from agents.milvus_expert import MilvusExpertAgent
        assert MilvusExpertAgent is not None
        assert hasattr(MilvusExpertAgent, 'handle_message')
    
    def test_devops_expert_imports(self):
        """Test devops expert agent can be imported."""
        from agents.devops_expert import DevOpsExpertAgent
        assert DevOpsExpertAgent is not None
        assert hasattr(DevOpsExpertAgent, 'handle_message')


@pytest.mark.smoke
class TestSharedMemoryImports:
    """Test shared memory module imports."""
    
    def test_shared_memory_imports(self):
        """Test SharedMemory class can be imported."""
        from agents.shared_memory import SharedMemory, MemoryMetrics
        assert SharedMemory is not None
        assert MemoryMetrics is not None
    
    def test_memory_metrics_structure(self):
        """Test MemoryMetrics dataclass structure."""
        from agents.shared_memory import MemoryMetrics
        metrics = MemoryMetrics()
        
        # Check key attributes exist
        assert hasattr(metrics, 'cache_hits')
        assert hasattr(metrics, 'cache_misses')
        assert hasattr(metrics, 'embedding_calls')
        assert hasattr(metrics, 'cache_hit_ratio')
        
        # Verify initial values
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.embedding_calls == 0
        assert metrics.cache_hit_ratio == 0.0


@pytest.mark.smoke
class TestUtilsImports:
    """Test utils module imports."""
    
    def test_openai_client_imports(self):
        """Test OpenAI client utilities can be imported."""
        from utils.openai_client import (
            OpenAIClientWrapper,
            ChatAPIConfig,
            EmbeddingAPIConfig,
            OpenAIConfig,
            ProviderType,
        )
        assert OpenAIClientWrapper is not None
        assert ChatAPIConfig is not None
        assert EmbeddingAPIConfig is not None
        assert OpenAIConfig is not None
        assert ProviderType is not None
    
    def test_config_manager_imports(self):
        """Test config manager can be imported."""
        from utils.config_manager import ConfigManager
        assert ConfigManager is not None
        assert hasattr(ConfigManager, 'get_global_config')
        assert hasattr(ConfigManager, 'get_agent_config')
    
    def test_config_validator_imports(self):
        """Test config validator can be imported."""
        from utils.config_validator import ConfigValidator
        assert ConfigValidator is not None
    
    def test_provider_type_enum(self):
        """Test ProviderType enum has expected values."""
        from utils.openai_client import ProviderType
        assert ProviderType.OPENAI.value == 'openai'
        assert ProviderType.OLLAMA.value == 'ollama'
        assert ProviderType.CUSTOM.value == 'custom'
