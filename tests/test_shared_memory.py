#!/usr/bin/env python3
"""Basic tests for SharedMemory functionality."""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Mock the dependencies that might not be available
class MockMilvusException(Exception):
    pass

# Set up mocks before importing
mock_pymilvus = Mock()
mock_pymilvus.connections = Mock()
mock_pymilvus.Collection = Mock
mock_pymilvus.CollectionSchema = Mock
mock_pymilvus.DataType = Mock()
mock_pymilvus.DataType.INT64 = 'INT64'
mock_pymilvus.DataType.VARCHAR = 'VARCHAR'
mock_pymilvus.DataType.FLOAT_VECTOR = 'FLOAT_VECTOR'
mock_pymilvus.FieldSchema = Mock
mock_pymilvus.MilvusException = MockMilvusException
mock_pymilvus.utility = Mock()

sys.modules['pymilvus'] = mock_pymilvus

# Mock numpy
class MockNumpy:
    def array(self, data):
        return data
    def __getattr__(self, name):
        return Mock()

sys.modules['numpy'] = MockNumpy()

# Now import the module
from agents.shared_memory import SharedMemory, MemoryMetrics


class TestSharedMemory:
    """Test cases for SharedMemory class."""
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_shared_memory_init(self, mock_init, mock_has_collection, mock_connect):
        """Test SharedMemory initialization."""
        mock_has_collection.return_value = False
        
        with patch('agents.shared_memory.get_openai_client') as mock_client:
            memory = SharedMemory()
            
            assert memory is not None
            assert isinstance(memory.metrics, MemoryMetrics)
            assert hasattr(memory, 'milvus_uri')
            mock_init.assert_called_once()
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_shared_memory_init_with_agent_name(self, mock_init, mock_has_collection, mock_connect):
        """Test SharedMemory initialization with agent name."""
        mock_has_collection.return_value = False
        
        with patch('agents.shared_memory.get_openai_client') as mock_client:
            memory = SharedMemory(agent_name="coordination")
            
            assert memory is not None
            assert hasattr(memory, 'milvus_uri')
            mock_init.assert_called_once()
    
    def test_memory_metrics_initialization(self):
        """Test MemoryMetrics initialization."""
        metrics = MemoryMetrics()
        
        assert metrics.search_latency == []
        assert metrics.cache_hit_ratio == 0.0
        assert metrics.embedding_calls == 0
        assert metrics.storage_operations == 0
        assert metrics.avg_similarity == 0.0
    
    def test_memory_metrics_with_values(self):
        """Test MemoryMetrics with initial values."""
        metrics = MemoryMetrics(
            search_latency=[0.1, 0.2, 0.3],
            cache_hit_ratio=0.75,
            embedding_calls=10,
            storage_operations=5,
            avg_similarity=0.85
        )
        
        assert metrics.search_latency == [0.1, 0.2, 0.3]
        assert metrics.cache_hit_ratio == 0.75
        assert metrics.embedding_calls == 10
        assert metrics.storage_operations == 5
        assert metrics.avg_similarity == 0.85


class TestSharedMemoryConfig:
    """Test SharedMemory configuration loading."""
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_shared_memory_uses_agent_config(self, mock_init, mock_has_collection, mock_connect):
        """Test that SharedMemory can use agent-specific configuration."""
        mock_has_collection.return_value = False
        
        with patch('agents.shared_memory.get_openai_client') as mock_client:
            # Test with agent name
            memory = SharedMemory(agent_name="coordination")
            assert memory is not None
            
            # Test without agent name
            memory_default = SharedMemory()
            assert memory_default is not None
    
    @patch('agents.shared_memory.get_config_manager')
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_config_manager_integration(self, mock_init, mock_has_collection, mock_connect, mock_get_config):
        """Test ConfigManager integration."""
        mock_config = Mock()
        mock_config._load_yaml_config.return_value = {
            'api_config': {'agent_overrides': {}}
        }
        mock_get_config.return_value = mock_config
        mock_has_collection.return_value = False
        
        memory = SharedMemory()
        assert memory is not None


class TestSharedMemoryErrorHandling:
    """Test SharedMemory error handling."""
    
    @patch('agents.shared_memory.connections.connect')
    def test_connection_error_handling(self, mock_connect):
        """Test handling of connection errors."""
        mock_connect.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            SharedMemory()
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    def test_collection_error_handling(self, mock_has_collection, mock_connect):
        """Test handling of collection errors."""
        mock_has_collection.side_effect = MockMilvusException("Collection error")
        
        with pytest.raises(MockMilvusException):
            SharedMemory()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])