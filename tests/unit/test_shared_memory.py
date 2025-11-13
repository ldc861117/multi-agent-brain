#!/usr/bin/env python3
"""Basic tests for SharedMemory functionality."""

import pytest
import sys
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

os.environ.setdefault("TEST_DISABLE_MILVUS", "1")

# Now import the module
from agents.shared_memory import SharedMemory, MemoryMetrics


class TestSharedMemory:
    """Test cases for SharedMemory class."""
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_shared_memory_init(self, mock_init, mock_connect):
        """SharedMemory falls back to in-memory backend when Milvus is disabled."""
        with patch('agents.shared_memory.get_openai_client') as mock_client, patch.dict(
            os.environ,
            {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "1"},
            clear=False,
        ):
            memory = SharedMemory()

        assert memory is not None
        assert memory._milvus_disabled is True
        assert memory._in_memory_store is not None
        assert isinstance(memory.metrics, MemoryMetrics)
        assert hasattr(memory, 'milvus_uri')
        mock_connect.assert_not_called()
        mock_init.assert_not_called()
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    def test_shared_memory_init_with_agent_name(self, mock_init, mock_connect):
        """Agent-specific initialization should also use the in-memory backend."""
        with patch('agents.shared_memory.get_openai_client') as mock_client, patch.dict(
            os.environ,
            {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "1"},
            clear=False,
        ):
            memory = SharedMemory(agent_name="coordination")

        assert memory is not None
        assert memory._milvus_disabled is True
        assert memory._in_memory_store is not None
        assert hasattr(memory, 'milvus_uri')
        mock_connect.assert_not_called()
        mock_init.assert_not_called()

    def test_in_memory_store_and_search(self):
        """store_knowledge and search_knowledge operate with the in-memory backend."""
        with patch('agents.shared_memory.get_openai_client') as mock_client, patch.dict(
            os.environ,
            {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "1"},
            clear=False,
        ):
            memory = SharedMemory()

        record_id = memory.store_knowledge(
            memory.COLLECTION_PROBLEM_SOLUTIONS,
            tenant_id="tenant-42",
            content={
                "problem": "Milvus setup guidance",
                "solution": "Enable the TEST_DISABLE_MILVUS flag for tests.",
            },
        )

        assert record_id > 0
        assert memory.metrics.storage_operations == 1

        results = memory.search_knowledge(
            memory.COLLECTION_PROBLEM_SOLUTIONS,
            tenant_id="tenant-42",
            query="Milvus",
            top_k=3,
            threshold=0.3,
        )

        assert results
        assert results[0]["problem"] == "Milvus setup guidance"
        assert results[0]["solution"].startswith("Enable the TEST_DISABLE_MILVUS")

        stats_before = memory.get_collection_stats(memory.COLLECTION_PROBLEM_SOLUTIONS)
        assert stats_before["total_records"] == 1
        assert stats_before["tenant_records"] == 1

        health_before = memory.health_check()
        assert health_before.get("mode") == "in_memory"
        assert health_before["collections"][memory.COLLECTION_PROBLEM_SOLUTIONS]["record_count"] == 1

        deleted = memory.delete_by_tenant(memory.COLLECTION_PROBLEM_SOLUTIONS, "tenant-42")
        assert deleted == 1

        stats_after = memory.get_collection_stats(memory.COLLECTION_PROBLEM_SOLUTIONS)
        assert stats_after["total_records"] == 0
        assert stats_after["tenant_records"] == 0

        results_after_delete = memory.search_knowledge(
            memory.COLLECTION_PROBLEM_SOLUTIONS,
            tenant_id="tenant-42",
            query="Milvus",
            top_k=3,
            threshold=0.3,
        )
        assert results_after_delete == []

        health_after = memory.health_check()
        assert health_after.get("mode") == "in_memory"
        assert health_after["collections"][memory.COLLECTION_PROBLEM_SOLUTIONS]["record_count"] == 0
    
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
    
    @patch('agents.shared_memory.get_config_manager')
    @patch('agents.shared_memory.get_openai_client')
    def test_shared_memory_uses_agent_config(self, mock_get_openai_client, mock_get_config_manager):
        """Configuration manager values populate embedding metadata for each mode."""
        manager = Mock()
        manager.get_global_config.return_value = SimpleNamespace(
            embedding_api=SimpleNamespace(model='global-model', dimension=128)
        )
        manager.get_agent_config.return_value = SimpleNamespace(
            embedding_api=SimpleNamespace(model='agent-model', dimension=256)
        )
        mock_get_config_manager.return_value = manager
        mock_get_openai_client.return_value = Mock()

        with patch('agents.shared_memory.OpenAIClientWrapper') as mock_wrapper, patch.dict(
            os.environ,
            {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "1"},
            clear=False,
        ):
            mock_wrapper.return_value = Mock()
            memory_agent = SharedMemory(agent_name="coordination")
            memory_default = SharedMemory()

        manager.get_agent_config.assert_called_with("coordination")
        manager.get_global_config.assert_called()
        assert memory_agent.embedding_model == "agent-model"
        assert memory_agent.embedding_dimension == 256
        assert memory_default.embedding_model == "global-model"
        assert memory_default.embedding_dimension == 128
    
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    @patch('agents.shared_memory.utility.has_collection', return_value=True)
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.get_config_manager')
    @patch('agents.shared_memory.get_openai_client')
    def test_config_manager_integration(
        self,
        mock_get_openai_client,
        mock_get_config_manager,
        mock_connect,
        mock_has_collection,
        mock_init,
    ):
        """When Milvus is enabled, connections and initialization are invoked."""
        manager = Mock()
        manager.get_global_config.return_value = SimpleNamespace(
            embedding_api=SimpleNamespace(model='global-milvus', dimension=384)
        )
        manager.get_agent_config.return_value = SimpleNamespace(
            embedding_api=SimpleNamespace(model='agent-milvus', dimension=256)
        )
        mock_get_config_manager.return_value = manager
        mock_get_openai_client.return_value = Mock()

        with patch('agents.shared_memory.OpenAIClientWrapper') as mock_wrapper, patch.dict(
            os.environ,
            {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "0"},
            clear=False,
        ):
            mock_wrapper.return_value = Mock()
            memory = SharedMemory()

        mock_connect.assert_called_once()
        mock_init.assert_called_once()
        assert memory is not None
        assert memory._milvus_disabled is False
        assert manager.get_global_config.called


class TestSharedMemoryErrorHandling:
    """Test SharedMemory error handling."""
    
    @patch('agents.shared_memory.get_openai_client')
    @patch('agents.shared_memory.connections.connect')
    def test_connection_error_handling(self, mock_connect, mock_get_openai_client):
        """Test handling of connection errors."""
        mock_connect.side_effect = Exception("Connection failed")
        
        with patch.dict(os.environ, {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "0"}, clear=False):
            with pytest.raises(Exception):
                SharedMemory()
    
    @patch('agents.shared_memory.get_openai_client')
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    def test_collection_error_handling(self, mock_has_collection, mock_connect, mock_get_openai_client):
        """Test handling of collection errors."""
        mock_has_collection.side_effect = MockMilvusException("Collection error")
        
        with patch.dict(os.environ, {"CHAT_API_KEY": "test-key", "TEST_DISABLE_MILVUS": "0"}, clear=False):
            with pytest.raises(MockMilvusException):
                SharedMemory()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])