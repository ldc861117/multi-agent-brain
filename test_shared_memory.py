"""Tests for the shared memory system.

This module provides comprehensive tests for the Milvus-based shared memory
implementation, including unit tests, integration tests, and performance tests.
"""

import asyncio
import json
import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from pymilvus import utility

from agents.shared_memory import AsyncSharedMemory, EmbeddingCache, MemoryMetrics, SharedMemory


class TestEmbeddingCache(unittest.TestCase):
    """Test the embedding cache functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = EmbeddingCache(max_size=3)
    
    def test_cache_basic_operations(self):
        """Test basic cache put/get operations."""
        text = "test text"
        model = "text-embedding-3-large"
        embedding = [0.1, 0.2, 0.3]
        
        # Test miss
        result = self.cache.get(text, model)
        self.assertIsNone(result)
        
        # Test put and hit
        self.cache.put(text, model, embedding)
        result = self.cache.get(text, model)
        self.assertEqual(result, embedding)
        
        # Test size
        self.assertEqual(self.cache.size(), 1)
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        embeddings = [
            ([0.1, 0.2], "text1"),
            ([0.3, 0.4], "text2"),
            ([0.5, 0.6], "text3"),
            ([0.7, 0.8], "text4"),
        ]
        
        # Fill cache to capacity
        for embedding, text in embeddings[:3]:
            self.cache.put(text, "model", embedding)
        
        self.assertEqual(self.cache.size(), 3)
        
        # Access first item to make it most recently used
        self.cache.get("text1", "model")
        
        # Add new item, should evict text2 (least recently used)
        self.cache.put("text4", "model", embeddings[3][0])
        
        # text2 should be evicted, text1 should still be cached
        self.assertIsNone(self.cache.get("text2", "model"))
        self.assertEqual(self.cache.get("text1", "model"), embeddings[0][0])
        self.assertEqual(self.cache.get("text4", "model"), embeddings[3][0])
        
        self.assertEqual(self.cache.size(), 3)
    
    def test_cache_clear(self):
        """Test cache clearing."""
        self.cache.put("text1", "model", [0.1, 0.2])
        self.cache.put("text2", "model", [0.3, 0.4])
        
        self.assertEqual(self.cache.size(), 2)
        
        self.cache.clear()
        
        self.assertEqual(self.cache.size(), 0)
        self.assertIsNone(self.cache.get("text1", "model"))
        self.assertIsNone(self.cache.get("text2", "model"))


class TestMemoryMetrics(unittest.TestCase):
    """Test the memory metrics functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = MemoryMetrics()
    
    def test_search_latency_tracking(self):
        """Test search latency tracking."""
        latencies = [0.1, 0.2, 0.3]
        
        for latency in latencies:
            self.metrics.add_search_latency(latency)
        
        self.assertEqual(len(self.metrics.search_latency), 3)
        self.assertAlmostEqual(self.metrics.get_average_latency(), 0.2, places=2)
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        # Test hits
        self.metrics.update_cache_stats(hit=True)
        self.metrics.update_cache_stats(hit=True)
        
        # Test miss
        self.metrics.update_cache_stats(hit=False)
        
        self.assertEqual(self.metrics.cache_hits, 2)
        self.assertEqual(self.metrics.cache_misses, 1)
        self.assertAlmostEqual(self.metrics.cache_hit_ratio, 2/3, places=2)
    
    def test_latency_limit(self):
        """Test that latency list is limited to 100 entries."""
        for i in range(150):
            self.metrics.add_search_latency(0.1)
        
        self.assertEqual(len(self.metrics.search_latency), 100)


class TestSharedMemory(unittest.TestCase):
    """Test the shared memory functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        
        # Mock OpenAI client
        self.mock_openai_client = Mock()
        self.mock_openai_client.get_embedding_vector.return_value = [[0.1, 0.2, 0.3, 0.4]]
        
        # Environment variables for testing
        os.environ["MILVUS_URI"] = self.temp_db.name
        os.environ["EMBEDDING_MODEL"] = "text-embedding-3-large"
        os.environ["EMBEDDING_DIMENSION"] = "4"
        os.environ["OPENAI_API_KEY"] = "test-key"
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_initialization(self, mock_get_client):
        """Test shared memory initialization."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        self.assertEqual(memory.embedding_dimension, 4)
        self.assertEqual(memory.embedding_model, "text-embedding-3-large")
        self.assertIsNotNone(memory.embedding_cache)
        self.assertIsNotNone(memory.metrics)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_store_expert_knowledge(self, mock_get_client):
        """Test storing expert knowledge."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        content = {
            "expert_domain": "python",
            "content": "Python is a programming language",
            "metadata": {"source": "test", "category": "basics"},
        }
        
        record_id = memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        self.assertIsInstance(record_id, int)
        self.assertEqual(memory.metrics.storage_operations, 1)
        self.assertEqual(memory.metrics.embedding_calls, 1)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_search_expert_knowledge(self, mock_get_client):
        """Test searching expert knowledge."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        # First store some knowledge
        content = {
            "expert_domain": "python",
            "content": "Python is a programming language",
        }
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        # Then search for it
        results = memory.search_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            "programming language",
            top_k=5,
            threshold=0.1
        )
        
        self.assertIsInstance(results, list)
        # May not find results due to mock embedding limitations
        # but should not raise an exception
    
    @patch('agents.shared_memory.get_openai_client')
    def test_batch_store_knowledge(self, mock_get_client):
        """Test batch storing knowledge."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        contents = [
            {
                "expert_domain": "python",
                "content": "Python is great",
            },
            {
                "expert_domain": "python",
                "content": "Python has many libraries",
            },
        ]
        
        record_ids = memory.batch_store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            contents
        )
        
        self.assertEqual(len(record_ids), 2)
        self.assertEqual(memory.metrics.storage_operations, 2)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_collaboration_history_storage(self, mock_get_client):
        """Test storing collaboration history."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        content = {
            "interaction_id": "interaction_123",
            "initiator_agent": "python_expert",
            "participating_agents": "python_expert,milvus_expert",
            "task_description": "Implement vector search",
            "metadata": {"outcome": "success", "tokens_used": 150},
        }
        
        record_id = memory.store_knowledge(
            SharedMemory.COLLECTION_COLLABORATION_HISTORY,
            "tenant1",
            content
        )
        
        self.assertIsInstance(record_id, int)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_problem_solutions_storage(self, mock_get_client):
        """Test storing problem solutions."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        content = {
            "problem": "How to handle large datasets efficiently?",
            "solution": "Use chunking and streaming approaches",
            "metadata": {"difficulty": "medium", "success_rate": 0.85},
        }
        
        record_id = memory.store_knowledge(
            SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
            "tenant1",
            content
        )
        
        self.assertIsInstance(record_id, int)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_problem_solutions_cold_start_search_is_resilient(self, mock_get_client):
        """Ensure problem_solutions search bootstraps missing collections."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        if utility.has_collection(SharedMemory.COLLECTION_PROBLEM_SOLUTIONS, using=memory.connection_alias):
            utility.drop_collection(SharedMemory.COLLECTION_PROBLEM_SOLUTIONS, using=memory.connection_alias)

            start = time.time()
            while utility.has_collection(SharedMemory.COLLECTION_PROBLEM_SOLUTIONS, using=memory.connection_alias):
                if time.time() - start > 5:
                    break
                time.sleep(0.1)
        
        self.assertFalse(
            utility.has_collection(SharedMemory.COLLECTION_PROBLEM_SOLUTIONS, using=memory.connection_alias)
        )
        
        results = memory.search_knowledge(
            SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
            "tenant1",
            "cold start bootstrap test",
            top_k=3,
            threshold=0.1,
        )
        
        self.assertEqual(results, [])
        self.assertTrue(
            utility.has_collection(SharedMemory.COLLECTION_PROBLEM_SOLUTIONS, using=memory.connection_alias)
        )
    
    @patch('agents.shared_memory.get_openai_client')
    def test_get_collection_stats(self, mock_get_client):
        """Test getting collection statistics."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        # Store some data first
        content = {"expert_domain": "python", "content": "test content"}
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        stats = memory.get_collection_stats(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1"
        )
        
        self.assertIn("collection", stats)
        self.assertIn("total_records", stats)
        self.assertIn("tenant_records", stats)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_delete_by_tenant(self, mock_get_client):
        """Test deleting tenant data."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        # Store some data first
        content = {"expert_domain": "python", "content": "test content"}
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        # Delete tenant data
        deleted_count = memory.delete_by_tenant(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1"
        )
        
        self.assertGreaterEqual(deleted_count, 0)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_health_check(self, mock_get_client):
        """Test health check functionality."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        health = memory.health_check()
        
        self.assertIn("milvus_connected", health)
        self.assertIn("collections", health)
        self.assertIn("cache_stats", health)
        self.assertIn("metrics", health)
        
        # Check all collections are present
        for collection_name in [
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            SharedMemory.COLLECTION_COLLABORATION_HISTORY,
            SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
        ]:
            self.assertIn(collection_name, health["collections"])
    
    @patch('agents.shared_memory.get_openai_client')
    def test_embedding_cache_functionality(self, mock_get_client):
        """Test that embedding cache works correctly."""
        mock_get_client.return_value = self.mock_openai_client
        
        memory = SharedMemory()
        
        # Store knowledge twice with same content
        content = {"expert_domain": "python", "content": "test content"}
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        # Second call should use cache
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content
        )
        
        # Should only have called embedding API once due to caching
        self.assertEqual(memory.metrics.embedding_calls, 1)
        self.assertGreater(memory.metrics.cache_hits, 0)


class TestAsyncSharedMemory(unittest.TestCase):
    """Test the async shared memory functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        
        # Mock OpenAI client
        self.mock_openai_client = Mock()
        self.mock_openai_client.get_embedding_vector.return_value = [[0.1, 0.2, 0.3, 0.4]]
        
        # Environment variables for testing
        os.environ["MILVUS_URI"] = self.temp_db.name
        os.environ["EMBEDDING_MODEL"] = "text-embedding-3-large"
        os.environ["EMBEDDING_DIMENSION"] = "4"
        os.environ["OPENAI_API_KEY"] = "test-key"
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_async_store_and_search(self, mock_get_client):
        """Test async store and search operations."""
        mock_get_client.return_value = self.mock_openai_client
        
        async def run_test():
            memory = AsyncSharedMemory()
            
            # Store knowledge
            content = {
                "expert_domain": "python",
                "content": "Python is a programming language",
            }
            
            record_id = await memory.astore_knowledge(
                SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
                "tenant1",
                content
            )
            
            self.assertIsInstance(record_id, int)
            
            # Search knowledge
            results = await memory.asearch_knowledge(
                SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
                "tenant1",
                "programming language",
                top_k=5,
                threshold=0.1
            )
            
            self.assertIsInstance(results, list)
        
        # Run the async test
        asyncio.run(run_test())
    
    @patch('agents.shared_memory.get_openai_client')
    def test_async_batch_operations(self, mock_get_client):
        """Test async batch operations."""
        mock_get_client.return_value = self.mock_openai_client
        
        async def run_test():
            memory = AsyncSharedMemory()
            
            # Batch store
            contents = [
                {
                    "expert_domain": "python",
                    "content": "Python is great",
                },
                {
                    "expert_domain": "python",
                    "content": "Python has many libraries",
                },
            ]
            
            record_ids = await memory.abatch_store_knowledge(
                SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
                "tenant1",
                contents
            )
            
            self.assertEqual(len(record_ids), 2)
            
            # Batch search
            queries = ["Python", "libraries"]
            results = await memory.abatch_search_knowledge(
                SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
                "tenant1",
                queries,
                top_k=5
            )
            
            self.assertEqual(len(results), 2)
        
        # Run the async test
        asyncio.run(run_test())
    
    @patch('agents.shared_memory.get_openai_client')
    def test_async_health_check(self, mock_get_client):
        """Test async health check."""
        mock_get_client.return_value = self.mock_openai_client
        
        async def run_test():
            memory = AsyncSharedMemory()
            
            health = await memory.ahealth_check()
            
            self.assertIn("milvus_connected", health)
            self.assertIn("collections", health)
            self.assertIn("cache_stats", health)
        
        # Run the async test
        asyncio.run(run_test())


class TestIntegration(unittest.TestCase):
    """Integration tests for the shared memory system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        
        # Environment variables for testing
        os.environ["MILVUS_URI"] = self.temp_db.name
        os.environ["EMBEDDING_MODEL"] = "text-embedding-3-large"
        os.environ["EMBEDDING_DIMENSION"] = "4"
        os.environ["OPENAI_API_KEY"] = "test-key"
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @patch('agents.shared_memory.get_openai_client')
    def test_multi_tenant_isolation(self, mock_get_client):
        """Test multi-tenant data isolation."""
        mock_client = Mock()
        mock_client.get_embedding_vector.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_get_client.return_value = mock_client
        
        memory = SharedMemory()
        
        # Store data for different tenants
        content1 = {"expert_domain": "python", "content": "Tenant 1 data"}
        content2 = {"expert_domain": "python", "content": "Tenant 2 data"}
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            content1
        )
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant2",
            content2
        )
        
        # Search for tenant 1 should only return tenant 1 data
        results1 = memory.search_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            "data",
            top_k=10
        )
        
        # All results should belong to tenant1
        for result in results1:
            self.assertEqual(result["tenant_id"], "tenant1")
    
    @patch('agents.shared_memory.get_openai_client')
    def test_cross_collection_search(self, mock_get_client):
        """Test searching across different collection types."""
        mock_client = Mock()
        mock_client.get_embedding_vector.return_value = [[0.1, 0.2, 0.3, 0.4]]
        mock_get_client.return_value = mock_client
        
        memory = SharedMemory()
        
        # Store in different collections
        expert_content = {
            "expert_domain": "python",
            "content": "Python error handling best practices",
        }
        
        problem_content = {
            "problem": "How to handle exceptions in Python?",
            "solution": "Use try-except blocks and specific exception types",
        }
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            expert_content
        )
        
        memory.store_knowledge(
            SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
            "tenant1",
            problem_content
        )
        
        # Search in both collections
        expert_results = memory.search_knowledge(
            SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            "tenant1",
            "Python error handling"
        )
        
        solution_results = memory.search_knowledge(
            SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
            "tenant1",
            "Python error handling"
        )
        
        self.assertIsInstance(expert_results, list)
        self.assertIsInstance(solution_results, list)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)