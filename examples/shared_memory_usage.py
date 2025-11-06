"""Example usage of the Milvus shared memory system.

This file demonstrates how to use the shared memory system for storing
and retrieving knowledge across multiple agents in a multi-agent system.
"""

import asyncio
import time
from typing import Dict, List

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.shared_memory import AsyncSharedMemory, SharedMemory


def basic_usage_example():
    """Demonstrate basic usage of the shared memory system."""
    print("=== Basic Usage Example ===")
    
    # Initialize shared memory
    memory = SharedMemory()
    
    # Store expert knowledge
    expert_content = {
        "expert_domain": "python",
        "content": "Python's async/await syntax makes asynchronous programming easier to read and maintain. Use asyncio for concurrent operations.",
        "metadata": {
            "source": "python_expert",
            "category": "async_programming",
            "difficulty": "intermediate"
        }
    }
    
    record_id = memory.store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        content=expert_content
    )
    
    print(f"Stored expert knowledge with ID: {record_id}")
    
    # Search for knowledge
    results = memory.search_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        query="asynchronous programming in Python",
        top_k=3,
        threshold=0.3
    )
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Similarity: {result['similarity_score']:.3f}")
        print(f"     Content: {result['content'][:100]}...")
        print(f"     Expert Domain: {result['expert_domain']}")
        print()


def collaboration_history_example():
    """Demonstrate storing and retrieving collaboration history."""
    print("=== Collaboration History Example ===")
    
    memory = SharedMemory()
    
    # Store collaboration history
    collaboration_content = {
        "interaction_id": "collab_2024_001",
        "initiator_agent": "general",
        "participating_agents": "python_expert,milvus_expert",
        "task_description": "Implement vector similarity search for Python code recommendations",
        "metadata": {
            "outcome": "success",
            "tokens_used": 1250,
            "duration_minutes": 45,
            "user_satisfaction": 4.5
        }
    }
    
    record_id = memory.store_knowledge(
        collection=SharedMemory.COLLECTION_COLLABORATION_HISTORY,
        tenant_id="company_a",
        content=collaboration_content
    )
    
    print(f"Stored collaboration history with ID: {record_id}")
    
    # Search similar collaborations
    results = memory.search_knowledge(
        collection=SharedMemory.COLLECTION_COLLABORATION_HISTORY,
        tenant_id="company_a",
        query="vector search implementation with multiple experts",
        top_k=5
    )
    
    print(f"Found {len(results)} similar collaborations:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Task: {result['task_description']}")
        print(f"     Participants: {result['participating_agents']}")
        print(f"     Outcome: {result['metadata'].get('outcome', 'N/A')}")
        print()


def problem_solutions_example():
    """Demonstrate storing and retrieving problem solutions."""
    print("=== Problem Solutions Example ===")
    
    memory = SharedMemory()
    
    # Store problem solution
    problem_content = {
        "problem": "How to efficiently handle large-scale vector similarity search in production?",
        "solution": "Use Milvus with proper indexing (HNSW for high recall, IVF_FLAT for speed), implement batch processing, and consider GPU acceleration for high-throughput scenarios.",
        "metadata": {
            "difficulty": "advanced",
            "success_rate": 0.92,
            "expert_domains": "milvus,devops",
            "implementation_time": "2 weeks",
            "performance_improvement": "15x faster"
        }
    }
    
    record_id = memory.store_knowledge(
        collection=SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
        tenant_id="company_a",
        content=problem_content
    )
    
    print(f"Stored problem solution with ID: {record_id}")
    
    # Search for similar problems
    results = memory.search_knowledge(
        collection=SharedMemory.COLLECTION_PROBLEM_SOLUTIONS,
        tenant_id="company_a",
        query="production vector database performance optimization",
        top_k=3
    )
    
    print(f"Found {len(results)} similar problems:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Problem: {result['problem']}")
        print(f"     Solution: {result['solution'][:150]}...")
        print(f"     Success Rate: {result['metadata'].get('success_rate', 'N/A')}")
        print()


def batch_operations_example():
    """Demonstrate batch operations for improved performance."""
    print("=== Batch Operations Example ===")
    
    memory = SharedMemory()
    
    # Prepare batch of expert knowledge
    batch_contents = [
        {
            "expert_domain": "python",
            "content": "List comprehensions provide a concise way to create lists based on existing lists.",
            "metadata": {"category": "python_basics"}
        },
        {
            "expert_domain": "python",
            "content": "Decorators allow you to modify or extend the behavior of functions without permanently modifying them.",
            "metadata": {"category": "python_advanced"}
        },
        {
            "expert_domain": "python",
            "content": "Context managers (with statements) ensure proper resource management and cleanup.",
            "metadata": {"category": "python_best_practices"}
        }
    ]
    
    # Batch store
    start_time = time.time()
    record_ids = memory.batch_store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        contents=batch_contents
    )
    batch_store_time = time.time() - start_time
    
    print(f"Batch stored {len(record_ids)} items in {batch_store_time:.3f}s")
    
    # Batch search
    queries = [
        "list creation in Python",
        "function modification techniques",
        "resource management in Python"
    ]
    
    start_time = time.time()
    batch_results = memory.batch_search_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        queries=queries,
        top_k=2
    )
    batch_search_time = time.time() - start_time
    
    print(f"Batch searched {len(queries)} queries in {batch_search_time:.3f}s")
    
    for i, (query, results) in enumerate(zip(queries, batch_results), 1):
        print(f"  Query {i}: '{query}' - Found {len(results)} results")
        for j, result in enumerate(results, 1):
            print(f"    {j}. Similarity: {result['similarity_score']:.3f}")
    print()


def multi_tenant_example():
    """Demonstrate multi-tenant isolation."""
    print("=== Multi-Tenant Isolation Example ===")
    
    memory = SharedMemory()
    
    # Store data for different tenants
    tenant1_content = {
        "expert_domain": "python",
        "content": "Company A's internal Python coding standards and best practices.",
        "metadata": {"company": "Company A", "internal": True}
    }
    
    tenant2_content = {
        "expert_domain": "python",
        "content": "Company B's Python development workflow and deployment strategies.",
        "metadata": {"company": "Company B", "internal": True}
    }
    
    # Store for both tenants
    memory.store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        content=tenant1_content
    )
    
    memory.store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_b",
        content=tenant2_content
    )
    
    # Search for each tenant
    tenant1_results = memory.search_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        query="Python coding standards"
    )
    
    tenant2_results = memory.search_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_b",
        query="Python development workflow"
    )
    
    print(f"Company A found {len(tenant1_results)} results")
    for result in tenant1_results:
        print(f"  - Content: {result['content'][:50]}...")
        print(f"    Tenant: {result['tenant_id']}")
    
    print(f"Company B found {len(tenant2_results)} results")
    for result in tenant2_results:
        print(f"  - Content: {result['content'][:50]}...")
        print(f"    Tenant: {result['tenant_id']}")
    print()


def performance_monitoring_example():
    """Demonstrate performance monitoring and metrics."""
    print("=== Performance Monitoring Example ===")
    
    memory = SharedMemory()
    
    # Perform some operations to generate metrics
    for i in range(5):
        content = {
            "expert_domain": "python",
            "content": f"Python tip number {i+1}: Always use meaningful variable names.",
            "metadata": {"tip_number": i+1}
        }
        
        memory.store_knowledge(
            collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            tenant_id="company_a",
            content=content
        )
    
    # Perform searches
    for i in range(3):
        memory.search_knowledge(
            collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
            tenant_id="company_a",
            query=f"Python programming tip {i+1}",
            top_k=2
        )
    
    # Display metrics
    metrics = memory.metrics
    print(f"Storage Operations: {metrics.storage_operations}")
    print(f"Embedding API Calls: {metrics.embedding_calls}")
    print(f"Cache Hit Ratio: {metrics.cache_hit_ratio:.2%}")
    print(f"Average Search Latency: {metrics.get_average_latency():.3f}s")
    print(f"Error Count: {metrics.errors_count}")
    
    # Display cache stats
    cache_stats = memory.health_check()["cache_stats"]
    print(f"Cache Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print()


async def async_usage_example():
    """Demonstrate asynchronous usage."""
    print("=== Async Usage Example ===")
    
    memory = AsyncSharedMemory()
    
    # Async store
    content = {
        "expert_domain": "python",
        "content": "Async/await in Python allows for non-blocking I/O operations.",
        "metadata": {"category": "async_programming"}
    }
    
    record_id = await memory.astore_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        content=content
    )
    
    print(f"Async stored knowledge with ID: {record_id}")
    
    # Async search
    results = await memory.asearch_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        query="non-blocking operations",
        top_k=3
    )
    
    print(f"Async search found {len(results)} results")
    
    # Async batch operations
    batch_contents = [
        {
            "expert_domain": "python",
            "content": "Use asyncio.gather() to run multiple coroutines concurrently.",
        },
        {
            "expert_domain": "python",
            "content": "Async context managers (async with) handle async resource cleanup.",
        }
    ]
    
    batch_ids = await memory.abatch_store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="company_a",
        contents=batch_contents
    )
    
    print(f"Async batch stored {len(batch_ids)} items")
    
    # Async health check
    health = await memory.ahealth_check()
    print(f"System health: {'OK' if health['milvus_connected'] else 'ERROR'}")
    print()


def health_check_example():
    """Demonstrate health check and system monitoring."""
    print("=== Health Check Example ===")
    
    memory = SharedMemory()
    
    # Perform health check
    health = memory.health_check()
    
    print("System Health Status:")
    print(f"  Milvus Connected: {health['milvus_connected']}")
    print(f"  Collections Status:")
    
    for collection, status in health["collections"].items():
        print(f"    {collection}:")
        print(f"      Status: {status['status']}")
        if 'record_count' in status:
            print(f"      Records: {status['record_count']}")
        if 'index_status' in status:
            print(f"      Index: {status['index_status']}")
    
    print(f"  Cache Statistics:")
    cache_stats = health["cache_stats"]
    print(f"    Size: {cache_stats['size']}/{cache_stats['max_size']}")
    print(f"    Hit Ratio: {cache_stats['hit_ratio']:.2%}")
    
    print(f"  Performance Metrics:")
    metrics = health["metrics"]
    print(f"    Avg Search Latency: {metrics['avg_search_latency']:.3f}s")
    print(f"    Embedding Calls: {metrics['embedding_calls']}")
    print(f"    Storage Operations: {metrics['storage_operations']}")
    print(f"    Error Count: {metrics['errors_count']}")
    print()


def tenant_management_example():
    """Demonstrate tenant management operations."""
    print("=== Tenant Management Example ===")
    
    memory = SharedMemory()
    
    # Store data for a tenant
    contents = [
        {
            "expert_domain": "python",
            "content": "Tenant-specific Python knowledge 1",
        },
        {
            "expert_domain": "python",
            "content": "Tenant-specific Python knowledge 2",
        }
    ]
    
    memory.batch_store_knowledge(
        collection=SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        tenant_id="temp_tenant",
        contents=contents
    )
    
    # Get tenant statistics
    stats = memory.get_collection_stats(
        SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        "temp_tenant"
    )
    
    print(f"Tenant stats before deletion:")
    print(f"  Total records: {stats['total_records']}")
    print(f"  Tenant records: {stats['tenant_records']}")
    
    # Delete tenant data (GDPR compliance)
    deleted_count = memory.delete_by_tenant(
        SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        "temp_tenant"
    )
    
    print(f"Deleted {deleted_count} records for tenant 'temp_tenant'")
    
    # Check stats after deletion
    stats_after = memory.get_collection_stats(
        SharedMemory.COLLECTION_EXPERT_KNOWLEDGE,
        "temp_tenant"
    )
    
    print(f"Tenant stats after deletion:")
    print(f"  Tenant records: {stats_after['tenant_records']}")
    print()


def main():
    """Run all examples."""
    print("Milvus Shared Memory System - Usage Examples")
    print("=" * 50)
    print()
    
    try:
        # Synchronous examples
        basic_usage_example()
        collaboration_history_example()
        problem_solutions_example()
        batch_operations_example()
        multi_tenant_example()
        performance_monitoring_example()
        health_check_example()
        tenant_management_example()
        
        # Asynchronous example
        print("Running async example...")
        asyncio.run(async_usage_example())
        
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()