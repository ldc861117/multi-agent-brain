#!/usr/bin/env python3
"""Minimal smoke tests for SharedMemory to boost coverage.

These tests focus on code paths not covered by existing integration tests,
using mocked Milvus connections to avoid external dependencies.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Mock external dependencies before importing
class MockMilvusException(Exception):
    pass

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

class MockNumpy:
    def array(self, data):
        return data
    def __getattr__(self, name):
        return Mock()
sys.modules['numpy'] = MockNumpy()

from agents.shared_memory import SharedMemory, MemoryMetrics, EmbeddingCache


@pytest.mark.smoke
class TestMemoryMetrics:
    """Test MemoryMetrics class functionality."""
    
    def test_metrics_initialization(self):
        """Test metrics object initializes correctly."""
        metrics = MemoryMetrics()
        assert metrics.cache_hit_ratio == 0.0
        assert metrics.embedding_calls == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
    
    def test_add_search_latency(self):
        """Test adding search latency measurements."""
        metrics = MemoryMetrics()
        metrics.add_search_latency(0.5)
        metrics.add_search_latency(0.7)
        
        assert len(metrics.search_latency) == 2
        assert 0.5 in metrics.search_latency
        assert 0.7 in metrics.search_latency
    
    def test_search_latency_limit(self):
        """Test search latency list is limited to 100 items."""
        metrics = MemoryMetrics()
        
        # Add 150 measurements
        for i in range(150):
            metrics.add_search_latency(float(i))
        
        # Should only keep last 100
        assert len(metrics.search_latency) == 100
        assert metrics.search_latency[0] == 50.0  # First of last 100
        assert metrics.search_latency[-1] == 149.0  # Last added
    
    def test_update_cache_stats_hit(self):
        """Test cache hit statistics update."""
        metrics = MemoryMetrics()
        metrics.update_cache_stats(hit=True)
        
        assert metrics.cache_hits == 1
        assert metrics.cache_misses == 0
        assert metrics.cache_hit_ratio == 1.0
    
    def test_update_cache_stats_miss(self):
        """Test cache miss statistics update."""
        metrics = MemoryMetrics()
        metrics.update_cache_stats(hit=False)
        
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 1
        assert metrics.cache_hit_ratio == 0.0
    
    def test_cache_hit_ratio_calculation(self):
        """Test cache hit ratio is calculated correctly."""
        metrics = MemoryMetrics()
        
        # 3 hits, 1 miss = 75% hit ratio
        metrics.update_cache_stats(hit=True)
        metrics.update_cache_stats(hit=True)
        metrics.update_cache_stats(hit=True)
        metrics.update_cache_stats(hit=False)
        
        assert metrics.cache_hits == 3
        assert metrics.cache_misses == 1
        assert metrics.cache_hit_ratio == 0.75
    
    def test_get_average_latency_empty(self):
        """Test average latency with no measurements."""
        metrics = MemoryMetrics()
        assert metrics.get_average_latency() == 0.0
    
    def test_get_average_latency(self):
        """Test average latency calculation."""
        metrics = MemoryMetrics()
        metrics.add_search_latency(0.5)
        metrics.add_search_latency(1.0)
        metrics.add_search_latency(1.5)
        
        avg = metrics.get_average_latency()
        assert avg == 1.0  # (0.5 + 1.0 + 1.5) / 3


@pytest.mark.smoke
class TestEmbeddingCache:
    """Test EmbeddingCache class functionality."""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct size."""
        cache = EmbeddingCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_cache_key_generation(self):
        """Test cache key is generated consistently."""
        cache = EmbeddingCache()
        key1 = cache._generate_key("test text", "model-1")
        key2 = cache._generate_key("test text", "model-1")
        key3 = cache._generate_key("test text", "model-2")
        
        # Same text and model should produce same key
        assert key1 == key2
        # Different model should produce different key
        assert key1 != key3
    
    def test_cache_get_miss(self):
        """Test cache get returns None on miss."""
        cache = EmbeddingCache()
        result = cache.get("test text", "model-1")
        assert result is None
    
    def test_cache_put_and_get(self):
        """Test cache put and get operations."""
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]
        
        cache.put("test text", "model-1", embedding)
        result = cache.get("test text", "model-1")
        
        assert result == embedding
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = EmbeddingCache(max_size=2)
        
        # Add 3 items to cache with max_size=2
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        cache.put("text3", "model", [0.3])  # Should evict text1
        
        # text1 should be evicted
        assert cache.get("text1", "model") is None
        # text2 and text3 should still be there
        assert cache.get("text2", "model") == [0.2]
        assert cache.get("text3", "model") == [0.3]
    
    def test_cache_access_order_update(self):
        """Test accessing an item updates LRU order."""
        cache = EmbeddingCache(max_size=2)
        
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        
        # Access text1 to make it recently used
        cache.get("text1", "model")
        
        # Add text3, should evict text2 (least recently used)
        cache.put("text3", "model", [0.3])
        
        assert cache.get("text1", "model") == [0.1]
        assert cache.get("text2", "model") is None
        assert cache.get("text3", "model") == [0.3]
    
    def test_cache_clear(self):
        """Test cache clear operation."""
        cache = EmbeddingCache()
        cache.put("text1", "model", [0.1])
        cache.put("text2", "model", [0.2])
        
        assert cache.size() == 2
        
        cache.clear()
        
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
        assert cache.size() == 0
        assert cache.get("text1", "model") is None
    
    def test_cache_size_method(self):
        """Test cache size method."""
        cache = EmbeddingCache()
        assert cache.size() == 0
        
        cache.put("text1", "model", [0.1])
        assert cache.size() == 1
        
        cache.put("text2", "model", [0.2])
        assert cache.size() == 2


@pytest.mark.smoke
class TestSharedMemoryBasics:
    """Test basic SharedMemory functionality without external services."""
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    @patch('agents.shared_memory.get_openai_client')
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'sk-test-fake-key-12345',
        'CHAT_API_KEY': 'sk-test-fake-key-12345',
    }, clear=False)
    def test_shared_memory_init(self, mock_client, mock_init, mock_has_coll, mock_connect):
        """Test SharedMemory initializes with correct defaults."""
        mock_has_coll.return_value = True
        mock_client_instance = Mock()
        mock_client_instance.config = Mock()
        mock_client_instance.config.embedding_api = Mock()
        mock_client_instance.config.embedding_api.model = 'text-embedding-3-small'
        mock_client_instance.config.embedding_api.dimension = 1536
        mock_client.return_value = mock_client_instance
        
        memory = SharedMemory(agent_name="shared_memory")
        
        assert memory.embedding_model is not None
        assert memory.embedding_dimension > 0
        assert isinstance(memory.metrics, MemoryMetrics)
        assert isinstance(memory.embedding_cache, EmbeddingCache)
        assert memory.embedding_cache.max_size == 1000
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    @patch('agents.shared_memory.get_openai_client')
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'sk-test-fake-key-12345',
        'CHAT_API_KEY': 'sk-test-fake-key-12345',
    }, clear=False)
    def test_shared_memory_custom_cache_size(self, mock_client, mock_init, mock_has_coll, mock_connect):
        """Test SharedMemory with custom cache size."""
        mock_has_coll.return_value = True
        mock_client_instance = Mock()
        mock_client_instance.config = Mock()
        mock_client_instance.config.embedding_api = Mock()
        mock_client_instance.config.embedding_api.model = 'text-embedding-3-small'
        mock_client_instance.config.embedding_api.dimension = 1536
        mock_client.return_value = mock_client_instance
        
        memory = SharedMemory(
            agent_name="shared_memory",
            cache_size=500
        )
        
        assert memory.embedding_cache.max_size == 500
        assert isinstance(memory.metrics, MemoryMetrics)
    
    @patch('agents.shared_memory.connections.connect')
    @patch('agents.shared_memory.utility.has_collection')
    @patch('agents.shared_memory.SharedMemory._initialize_collections')
    @patch('agents.shared_memory.get_openai_client')
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'sk-test-fake-key-12345',
        'CHAT_API_KEY': 'sk-test-fake-key-12345',
    }, clear=False)
    def test_cache_stats_tracking(self, mock_client, mock_init, mock_has_coll, mock_connect):
        """Test metrics tracking works correctly."""
        mock_has_coll.return_value = True
        mock_client_instance = Mock()
        mock_client_instance.config = Mock()
        mock_client_instance.config.embedding_api = Mock()
        mock_client_instance.config.embedding_api.model = 'text-embedding-3-small'
        mock_client_instance.config.embedding_api.dimension = 1536
        mock_client.return_value = mock_client_instance
        
        memory = SharedMemory(agent_name="shared_memory")
        
        # Initial state
        assert memory.metrics.cache_hits == 0
        assert memory.metrics.cache_misses == 0
        
        # Simulate cache stats updates
        memory.metrics.update_cache_stats(hit=True)
        memory.metrics.update_cache_stats(hit=False)
        
        assert memory.metrics.cache_hits == 1
        assert memory.metrics.cache_misses == 1
        assert memory.metrics.cache_hit_ratio == 0.5
