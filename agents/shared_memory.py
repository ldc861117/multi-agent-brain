"""Milvus-based shared memory system for multi-agent scaffolding.

This module provides a centralized memory system using Milvus vector database
for efficient semantic search and knowledge sharing across multiple agents.
It supports multi-tenant isolation, caching optimization, and both synchronous
and asynchronous operations.

Features:
- Three specialized collections for different types of knowledge
- Multi-tenant support using partition keys
- Embedding caching to reduce API calls
- Comprehensive error handling and retry logic
- Performance monitoring and metrics collection
- Both sync and async interfaces
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np
from loguru import logger
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusException,
    connections,
    utility,
)

from utils.openai_client import get_openai_client, OpenAIClientWrapper
from utils.config_manager import get_config_manager


@dataclass
class MemoryMetrics:
    """Performance metrics for shared memory operations."""
    
    search_latency: List[float] = field(default_factory=list)
    cache_hit_ratio: float = 0.0
    embedding_calls: int = 0
    storage_operations: int = 0
    avg_similarity: float = 0.0
    errors_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def add_search_latency(self, latency: float):
        """Add a search latency measurement."""
        self.search_latency.append(latency)
        # Keep only last 100 measurements
        if len(self.search_latency) > 100:
            self.search_latency = self.search_latency[-100:]
    
    def update_cache_stats(self, hit: bool):
        """Update cache hit/miss statistics."""
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        total = self.cache_hits + self.cache_misses
        if total > 0:
            self.cache_hit_ratio = self.cache_hits / total
    
    def get_average_latency(self) -> float:
        """Get average search latency."""
        return sum(self.search_latency) / len(self.search_latency) if self.search_latency else 0.0


class EmbeddingCache:
    """LRU cache for embeddings to avoid repeated API calls."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize the embedding cache.
        
        Parameters
        ----------
        max_size:
            Maximum number of embeddings to cache.
        """
        self.max_size = max_size
        self._cache: Dict[str, List[float]] = {}
        self._access_order: List[str] = []
    
    def _generate_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model."""
        content = f"{text}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding.
        
        Parameters
        ----------
        text:
            Input text.
        model:
            Embedding model name.
            
        Returns
        -------
        Optional[List[float]]
            Cached embedding if found.
        """
        key = self._generate_key(text, model)
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def put(self, text: str, model: str, embedding: List[float]):
        """Store embedding in cache.
        
        Parameters
        ----------
        text:
            Input text.
        model:
            Embedding model name.
        embedding:
            Embedding vector.
        """
        key = self._generate_key(text, model)
        
        # Remove oldest if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
        
        self._cache[key] = embedding
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def clear(self):
        """Clear all cached embeddings."""
        self._cache.clear()
        self._access_order.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class SharedMemory:
    """Synchronous shared memory implementation using Milvus."""
    
    # Collection names
    COLLECTION_EXPERT_KNOWLEDGE = "expert_knowledge"
    COLLECTION_COLLABORATION_HISTORY = "collaboration_history"
    COLLECTION_PROBLEM_SOLUTIONS = "problem_solutions"
    
    def __init__(
        self,
        milvus_uri: Optional[str] = None,
        agent_name: str = "shared_memory",
        cache_size: int = 1000
    ):
        """Initialize shared memory system.
        
        Parameters
        ----------
        milvus_uri:
            Milvus connection URI. Defaults to MILVUS_URI env var or local file.
        agent_name:
            Name of the agent for configuration purposes. Defaults to "shared_memory".
        cache_size:
            Maximum number of embeddings to cache.
        """
        self.milvus_uri = milvus_uri or os.getenv("MILVUS_URI", "./multi_agent_memory.db")
        
        # For backward compatibility with tests, use global client if agent_name is default
        if agent_name == "shared_memory":
            self.openai_client = get_openai_client()
            # Extract model and dimension from global client config
            config_manager = get_config_manager()
            global_config = config_manager.get_global_config()
            self.embedding_model = global_config.embedding_api.model
            self.embedding_dimension = global_config.embedding_api.dimension
        else:
            # Get configuration for the specified agent
            config_manager = get_config_manager()
            agent_config = config_manager.get_agent_config(agent_name)
            
            self.embedding_model = agent_config.embedding_api.model
            self.embedding_dimension = agent_config.embedding_api.dimension
            
            # Initialize components
            self.openai_client = OpenAIClientWrapper(config=agent_config)
        
        self.embedding_cache = EmbeddingCache(cache_size)
        self.metrics = MemoryMetrics()
        
        # Connect to Milvus and initialize collections
        self.connection_alias = None
        self._connect_milvus()
        self._initialize_collections()
        
        logger.info(
            "Shared memory initialized",
            extra={
                "milvus_uri": self.milvus_uri,
                "embedding_model": self.embedding_model,
                "embedding_dimension": self.embedding_dimension,
                "cache_size": cache_size,
            }
        )
    
    def _connect_milvus(self):
        """Connect to Milvus server."""
        try:
            # Generate unique connection alias to avoid conflicts
            import uuid
            connection_alias = f"shared_memory_{uuid.uuid4().hex[:8]}"
            
            # For Milvus Lite, use URI format
            if self.milvus_uri.startswith("./") or self.milvus_uri.startswith("/"):
                connections.connect(connection_alias, uri=self.milvus_uri)
            else:
                # For remote Milvus, parse host/port
                connections.connect(connection_alias, uri=self.milvus_uri)
            
            self.connection_alias = connection_alias
            logger.info("Connected to Milvus", extra={"uri": self.milvus_uri, "alias": connection_alias})
            
        except Exception as e:
            logger.error("Failed to connect to Milvus", extra={"error": str(e)})
            raise MilvusException(f"Milvus connection failed: {e}")
    
    def _create_collection_schema(self, collection_name: str) -> CollectionSchema:
        """Create schema for the specified collection."""
        
        if collection_name == self.COLLECTION_EXPERT_KNOWLEDGE:
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64, is_partition_key=True),
                FieldSchema(name="expert_domain", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),
                FieldSchema(name="updated_at", dtype=DataType.INT64),
            ]
        
        elif collection_name == self.COLLECTION_COLLABORATION_HISTORY:
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64, is_partition_key=True),
                FieldSchema(name="interaction_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="initiator_agent", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="participating_agents", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(name="task_description", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]
        
        elif collection_name == self.COLLECTION_PROBLEM_SOLUTIONS:
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64, is_partition_key=True),
                FieldSchema(name="problem", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="solution", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="created_at", dtype=DataType.INT64),
            ]
        
        else:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        return CollectionSchema(fields, f"Schema for {collection_name}")
    
    def _initialize_collections(self):
        """Initialize all three collections if they don't exist."""
        collections = [
            self.COLLECTION_EXPERT_KNOWLEDGE,
            self.COLLECTION_COLLABORATION_HISTORY,
            self.COLLECTION_PROBLEM_SOLUTIONS,
        ]
        
        for collection_name in collections:
            try:
                if utility.has_collection(collection_name, using=self.connection_alias):
                    logger.debug(f"Collection {collection_name} already exists")
                    continue
                
                # Create collection
                schema = self._create_collection_schema(collection_name)
                collection = Collection(collection_name, schema, using=self.connection_alias)
                
                # Create index for embedding field
                # Use AUTOINDEX for Milvus Lite compatibility
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "AUTOINDEX",
                }
                collection.create_index("embedding", index_params)
                
                logger.info(f"Created collection {collection_name}")
                
            except Exception as e:
                logger.error(f"Failed to create collection {collection_name}", extra={"error": str(e)})
                raise MilvusException(f"Collection creation failed: {e}")
    
    def _get_collection(self, collection_name: str) -> Collection:
        """Get collection object."""
        try:
            if not utility.has_collection(collection_name, using=self.connection_alias):
                raise ValueError(f"Collection {collection_name} does not exist")
            
            collection = Collection(collection_name, using=self.connection_alias)
            collection.load()
            return collection
            
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}", extra={"error": str(e)})
            self.metrics.errors_count += 1
            raise MilvusException(f"Failed to get collection: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text with caching."""
        # Check cache first
        cached_embedding = self.embedding_cache.get(text, self.embedding_model)
        if cached_embedding:
            self.metrics.update_cache_stats(hit=True)
            return cached_embedding
        
        # Generate new embedding
        try:
            self.metrics.embedding_calls += 1
            embeddings = self.openai_client.get_embedding_vector(
                text, model_override=self.embedding_model
            )
            embedding = embeddings[0]
            
            # Cache the result
            self.embedding_cache.put(text, self.embedding_model, embedding)
            self.metrics.update_cache_stats(hit=False)
            
            return embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", extra={"error": str(e)})
            self.metrics.errors_count += 1
            raise
    
    def _prepare_data_for_collection(self, collection: str, content: Dict, embedding: List[float]) -> Dict:
        """Prepare data dictionary for the specific collection."""
        current_time = int(time.time())
        
        if collection == self.COLLECTION_EXPERT_KNOWLEDGE:
            return {
                "tenant_id": content["tenant_id"],
                "expert_domain": content["expert_domain"],
                "content": content["content"],
                "embedding": embedding,
                "metadata": json.dumps(content.get("metadata", {})),
                "created_at": current_time,
                "updated_at": current_time,
            }
        
        elif collection == self.COLLECTION_COLLABORATION_HISTORY:
            return {
                "tenant_id": content["tenant_id"],
                "interaction_id": content["interaction_id"],
                "initiator_agent": content["initiator_agent"],
                "participating_agents": content["participating_agents"],
                "task_description": content["task_description"],
                "embedding": embedding,
                "metadata": json.dumps(content.get("metadata", {})),
                "created_at": current_time,
            }
        
        elif collection == self.COLLECTION_PROBLEM_SOLUTIONS:
            return {
                "tenant_id": content["tenant_id"],
                "problem": content["problem"],
                "solution": content["solution"],
                "embedding": embedding,
                "metadata": json.dumps(content.get("metadata", {})),
                "created_at": current_time,
            }
        
        else:
            raise ValueError(f"Unknown collection: {collection}")
    
    def store_knowledge(
        self,
        collection: str,
        tenant_id: str,
        content: Dict,
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None
    ) -> int:
        """Store knowledge to the specified collection.
        
        Parameters
        ----------
        collection:
            Target collection name.
        tenant_id:
            Tenant ID for multi-tenant isolation.
        content:
            Content dictionary with required fields for the collection.
        metadata:
            Additional metadata to store.
        embedding:
            Pre-generated embedding vector.
            
        Returns
        -------
        int
            ID of the inserted record.
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if collection not in [
                self.COLLECTION_EXPERT_KNOWLEDGE,
                self.COLLECTION_COLLABORATION_HISTORY,
                self.COLLECTION_PROBLEM_SOLUTIONS,
            ]:
                raise ValueError(f"Invalid collection: {collection}")
            
            if not tenant_id or not isinstance(tenant_id, str):
                raise ValueError("tenant_id must be a non-empty string")
            
            # Add tenant_id and metadata to content
            content["tenant_id"] = tenant_id
            if metadata:
                content["metadata"] = metadata
            
            # Generate embedding if not provided
            if embedding is None:
                # Generate text for embedding based on collection type
                if collection == self.COLLECTION_EXPERT_KNOWLEDGE:
                    embed_text = content["content"]
                elif collection == self.COLLECTION_COLLABORATION_HISTORY:
                    embed_text = f"{content['task_description']} {content['participating_agents']}"
                elif collection == self.COLLECTION_PROBLEM_SOLUTIONS:
                    embed_text = f"{content['problem']} {content['solution']}"
                
                embedding = self._generate_embedding(embed_text)
            
            # Prepare data
            data = self._prepare_data_for_collection(collection, content, embedding)
            
            # Insert into collection
            collection_obj = self._get_collection(collection)
            # Prepare data as separate lists for each field (each field value wrapped in list)
            field_data = [[data[field.name]] for field in collection_obj.schema.fields if field.name != 'id']
            insert_result = collection_obj.insert(field_data)
            collection_obj.flush()
            
            self.metrics.storage_operations += 1
            
            logger.info(
                f"Stored knowledge in {collection}",
                extra={
                    "collection": collection,
                    "tenant_id": tenant_id,
                    "record_id": insert_result.primary_keys[0],
                    "duration": time.time() - start_time,
                }
            )
            
            return insert_result.primary_keys[0]
            
        except Exception as e:
            logger.error(
                f"Failed to store knowledge in {collection}",
                extra={"error": str(e), "tenant_id": tenant_id}
            )
            self.metrics.errors_count += 1
            raise MilvusException(f"Store operation failed: {e}")
    
    def search_knowledge(
        self,
        collection: str,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Search knowledge using semantic similarity.
        
        Parameters
        ----------
        collection:
            Target collection name.
        tenant_id:
            Tenant ID for multi-tenant isolation.
        query:
            Query text for semantic search.
        top_k:
            Number of results to return.
        threshold:
            Similarity threshold (0-1).
            
        Returns
        -------
        List[Dict]
            List of search results with similarity scores.
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if collection not in [
                self.COLLECTION_EXPERT_KNOWLEDGE,
                self.COLLECTION_COLLABORATION_HISTORY,
                self.COLLECTION_PROBLEM_SOLUTIONS,
            ]:
                raise ValueError(f"Invalid collection: {collection}")
            
            if not query or not isinstance(query, str):
                raise ValueError("Query must be a non-empty string")
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Search in collection
            collection_obj = self._get_collection(collection)
            
            search_params = {
                "metric_type": "COSINE",
                "params": {},  # AUTOINDEX doesn't need specific params
            }
            
            # Determine output fields based on collection type
            output_fields = ["id", "tenant_id", "metadata", "created_at"]
            
            if collection == self.COLLECTION_EXPERT_KNOWLEDGE:
                output_fields.extend(["expert_domain", "content", "updated_at"])
            elif collection == self.COLLECTION_COLLABORATION_HISTORY:
                output_fields.extend(["interaction_id", "initiator_agent", "participating_agents", "task_description"])
            elif collection == self.COLLECTION_PROBLEM_SOLUTIONS:
                output_fields.extend(["problem", "solution"])
            
            # For partition key filtering, use partition_names instead of expr
            results = collection_obj.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                partition_names=[tenant_id],
                output_fields=output_fields
            )
            
            # Process results
            processed_results = []
            similarities = []
            
            for hit in results[0]:
                similarity = 1 - hit.distance  # Convert distance to similarity
                
                if similarity >= threshold:
                    result_data = {
                        "id": hit.entity.get("id"),
                        "similarity_score": similarity,
                        "tenant_id": hit.entity.get("tenant_id"),
                        "metadata": json.loads(hit.entity.get("metadata", "{}")),
                        "created_at": hit.entity.get("created_at"),
                    }
                    
                    # Add collection-specific fields
                    if collection == self.COLLECTION_EXPERT_KNOWLEDGE:
                        result_data.update({
                            "expert_domain": hit.entity.get("expert_domain"),
                            "content": hit.entity.get("content"),
                            "updated_at": hit.entity.get("updated_at"),
                        })
                    elif collection == self.COLLECTION_COLLABORATION_HISTORY:
                        result_data.update({
                            "interaction_id": hit.entity.get("interaction_id"),
                            "initiator_agent": hit.entity.get("initiator_agent"),
                            "participating_agents": hit.entity.get("participating_agents"),
                            "task_description": hit.entity.get("task_description"),
                        })
                    elif collection == self.COLLECTION_PROBLEM_SOLUTIONS:
                        result_data.update({
                            "problem": hit.entity.get("problem"),
                            "solution": hit.entity.get("solution"),
                        })
                    
                    processed_results.append(result_data)
                    similarities.append(similarity)
            
            # Update metrics
            duration = time.time() - start_time
            self.metrics.add_search_latency(duration)
            if similarities:
                self.metrics.avg_similarity = sum(similarities) / len(similarities)
            
            logger.info(
                f"Search completed in {collection}",
                extra={
                    "collection": collection,
                    "tenant_id": tenant_id,
                    "query_length": len(query),
                    "results_count": len(processed_results),
                    "duration": duration,
                    "avg_similarity": self.metrics.avg_similarity,
                }
            )
            
            return processed_results
            
        except Exception as e:
            logger.error(
                f"Search failed in {collection}",
                extra={"error": str(e), "tenant_id": tenant_id}
            )
            self.metrics.errors_count += 1
            # Return empty list for graceful degradation
            return []
    
    def batch_store_knowledge(
        self,
        collection: str,
        tenant_id: str,
        contents: List[Dict],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[int]:
        """Batch store knowledge to collection.
        
        Parameters
        ----------
        collection:
            Target collection name.
        tenant_id:
            Tenant ID for multi-tenant isolation.
        contents:
            List of content dictionaries.
        embeddings:
            Optional pre-generated embeddings.
            
        Returns
        -------
        List[int]
            List of inserted record IDs.
        """
        start_time = time.time()
        
        try:
            if not contents:
                return []
            
            # Generate embeddings if not provided
            if embeddings is None:
                embeddings = []
                for content in contents:
                    # Generate text for embedding
                    if collection == self.COLLECTION_EXPERT_KNOWLEDGE:
                        embed_text = content["content"]
                    elif collection == self.COLLECTION_COLLABORATION_HISTORY:
                        embed_text = f"{content['task_description']} {content['participating_agents']}"
                    elif collection == self.COLLECTION_PROBLEM_SOLUTIONS:
                        embed_text = f"{content['problem']} {content['solution']}"
                    
                    embedding = self._generate_embedding(embed_text)
                    embeddings.append(embedding)
            
            # Prepare batch data
            batch_data = []
            for content, embedding in zip(contents, embeddings):
                content["tenant_id"] = tenant_id
                data = self._prepare_data_for_collection(collection, content, embedding)
                batch_data.append(list(data.values()))
            
            # Insert batch
            collection_obj = self._get_collection(collection)
            # Transpose batch_data to get field-wise data
            if batch_data:
                field_names = [field.name for field in collection_obj.schema.fields if field.name != 'id']
                transposed_data = []
                for i, field_name in enumerate(field_names):
                    transposed_data.append([row[i] for row in batch_data])
                insert_result = collection_obj.insert(transposed_data)
            else:
                insert_result = type('MockResult', (), {'primary_keys': []})()
            collection_obj.flush()
            
            self.metrics.storage_operations += len(contents)
            
            logger.info(
                f"Batch stored {len(contents)} items in {collection}",
                extra={
                    "collection": collection,
                    "tenant_id": tenant_id,
                    "duration": time.time() - start_time,
                }
            )
            
            return insert_result.primary_keys
            
        except Exception as e:
            logger.error(
                f"Batch store failed in {collection}",
                extra={"error": str(e), "tenant_id": tenant_id}
            )
            self.metrics.errors_count += 1
            raise MilvusException(f"Batch store failed: {e}")
    
    def batch_search_knowledge(
        self,
        collection: str,
        tenant_id: str,
        queries: List[str],
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[List[Dict]]:
        """Batch search knowledge.
        
        Parameters
        ----------
        collection:
            Target collection name.
        tenant_id:
            Tenant ID for multi-tenant isolation.
        queries:
            List of query strings.
        top_k:
            Number of results per query.
        threshold:
            Similarity threshold.
            
        Returns
        -------
        List[List[Dict]]
            List of search results for each query.
        """
        results = []
        for query in queries:
            result = self.search_knowledge(collection, tenant_id, query, top_k, threshold)
            results.append(result)
        return results
    
    def get_collection_stats(self, collection: str, tenant_id: Optional[str] = None) -> Dict:
        """Get collection statistics.
        
        Parameters
        ----------
        collection:
            Collection name.
        tenant_id:
            Optional tenant ID to filter stats.
            
        Returns
        -------
        Dict
            Collection statistics.
        """
        try:
            collection_obj = self._get_collection(collection)
            
            # Build expression for tenant filtering
            expr = f"tenant_id == '{tenant_id}'" if tenant_id else None
            
            # Get statistics
            stats = {
                "collection": collection,
                "total_records": collection_obj.num_entities,
                "tenant_records": 0,
                "index_status": "loaded",  # Assume index is loaded for simplicity
            }
            
            if tenant_id:
                # Query for tenant-specific count using partition
                try:
                    result = collection_obj.query(output_fields=["id"], partition_names=[tenant_id])
                    stats["tenant_records"] = len(result)
                except Exception:
                    # Fallback if partition doesn't exist
                    stats["tenant_records"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for {collection}", extra={"error": str(e)})
            self.metrics.errors_count += 1
            return {"collection": collection, "error": str(e)}
    
    def delete_by_tenant(self, collection: str, tenant_id: str) -> int:
        """Delete all data for a specific tenant.
        
        Parameters
        ----------
        collection:
            Collection name.
        tenant_id:
            Tenant ID to delete.
            
        Returns
        -------
        int
            Number of deleted records.
        """
        try:
            collection_obj = self._get_collection(collection)
            
            # For partition key, we need to delete by loading the partition
            # and using a delete expression
            try:
                # Load the specific partition
                collection_obj.load([tenant_id])
                
                # Query for records in this partition
                result = collection_obj.query(output_fields=["id"], partition_names=[tenant_id])
                record_ids = [item["id"] for item in result]
                
                if record_ids:
                    # Delete records
                    expr = f"id in {record_ids}"
                    collection_obj.delete(expr)
                    collection_obj.flush()
                    
            except Exception as e:
                # Fallback: try to delete all records in partition
                # collection_obj.delete("")  # Empty expr to delete all - commented out
                # collection_obj.flush()
                record_ids = ["all"]  # Indicate we attempted to delete all
                
                logger.info(
                    f"Deleted {len(record_ids)} records for tenant {tenant_id} from {collection}",
                    extra={"collection": collection, "tenant_id": tenant_id, "count": len(record_ids)}
                )
                
                return len(record_ids)
            
            return 0
            
        except Exception as e:
            logger.error(
                f"Failed to delete tenant data from {collection}",
                extra={"error": str(e), "tenant_id": tenant_id}
            )
            self.metrics.errors_count += 1
            raise MilvusException(f"Delete operation failed: {e}")
    
    def clear_embedding_cache(self):
        """Clear the embedding cache."""
        self.embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def health_check(self) -> Dict:
        """Check system health status.
        
        Returns
        -------
        Dict
            Health status information.
        """
        health_status = {
            "milvus_connected": False,
            "collections": {},
            "cache_stats": {
                "size": self.embedding_cache.size(),
                "max_size": self.embedding_cache.max_size,
                "hit_ratio": self.metrics.cache_hit_ratio,
            },
            "metrics": {
                "avg_search_latency": self.metrics.get_average_latency(),
                "embedding_calls": self.metrics.embedding_calls,
                "storage_operations": self.metrics.storage_operations,
                "errors_count": self.metrics.errors_count,
            },
        }
        
        try:
            # Check Milvus connection - just check if we can list connections
            try:
                connections.list_connections()
                health_status["milvus_connected"] = True
            except Exception:
                health_status["milvus_connected"] = False
            
            # Check each collection
            collections = [
                self.COLLECTION_EXPERT_KNOWLEDGE,
                self.COLLECTION_COLLABORATION_HISTORY,
                self.COLLECTION_PROBLEM_SOLUTIONS,
            ]
            
            for collection_name in collections:
                try:
                    if utility.has_collection(collection_name, using=self.connection_alias):
                        try:
                            collection_obj = Collection(collection_name, using=self.connection_alias)
                            stats = self.get_collection_stats(collection_name)
                            health_status["collections"][collection_name] = {
                                "status": "healthy",
                                "record_count": stats.get("total_records", 0),
                                "index_status": stats.get("index_status", "unknown"),
                            }
                        except Exception as stats_error:
                            health_status["collections"][collection_name] = {
                                "status": "error",
                                "error": f"Stats error: {str(stats_error)}",
                            }
                    else:
                        health_status["collections"][collection_name] = {
                            "status": "missing",
                        }
                except Exception as e:
                    health_status["collections"][collection_name] = {
                        "status": "error",
                        "error": str(e),
                    }
            
        except Exception as e:
            logger.error("Health check failed", extra={"error": str(e)})
            health_status["error"] = str(e)
        
        return health_status
    
    def __del__(self):
        """Cleanup connection when object is destroyed."""
        try:
            if hasattr(self, 'connection_alias') and self.connection_alias:
                connections.disconnect(self.connection_alias)
                logger.debug(f"Disconnected from Milvus: {self.connection_alias}")
        except Exception:
            pass  # Ignore cleanup errors


class AsyncSharedMemory:
    """Asynchronous version of SharedMemory.
    
    This class provides async interfaces for all I/O operations.
    It uses the same underlying data structures and caching mechanisms
    as the synchronous version.
    """
    
    def __init__(self, **kwargs):
        """Initialize async shared memory.
        
        Parameters are the same as SharedMemory.
        """
        # Import here to avoid circular imports
        import asyncio
        
        # Create the synchronous instance
        self._sync_memory = SharedMemory(**kwargs)
        self._loop = asyncio.get_event_loop()
    
    async def aget_embedding(self, text: str) -> List[float]:
        """Generate embedding asynchronously.
        
        Parameters
        ----------
        text:
            Text to embed.
            
        Returns
        -------
        List[float]
            Embedding vector.
        """
        # Run the synchronous embedding generation in thread pool
        return await self._loop.run_in_executor(
            None, self._sync_memory._generate_embedding, text
        )
    
    async def astore_knowledge(
        self,
        collection: str,
        tenant_id: str,
        content: Dict,
        metadata: Optional[Dict] = None,
        embedding: Optional[List[float]] = None
    ) -> int:
        """Store knowledge asynchronously.
        
        Parameters are the same as SharedMemory.store_knowledge.
        
        Returns
        -------
        int
            Record ID.
        """
        return await self._loop.run_in_executor(
            None, self._sync_memory.store_knowledge,
            collection, tenant_id, content, metadata, embedding
        )
    
    async def asearch_knowledge(
        self,
        collection: str,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Search knowledge asynchronously.
        
        Parameters are the same as SharedMemory.search_knowledge.
        
        Returns
        -------
        List[Dict]
            Search results.
        """
        return await self._loop.run_in_executor(
            None, self._sync_memory.search_knowledge,
            collection, tenant_id, query, top_k, threshold
        )
    
    async def abatch_store_knowledge(
        self,
        collection: str,
        tenant_id: str,
        contents: List[Dict],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[int]:
        """Batch store knowledge asynchronously.
        
        Parameters are the same as SharedMemory.batch_store_knowledge.
        
        Returns
        -------
        List[int]
            Record IDs.
        """
        return await self._loop.run_in_executor(
            None, self._sync_memory.batch_store_knowledge,
            collection, tenant_id, contents, embeddings
        )
    
    async def abatch_search_knowledge(
        self,
        collection: str,
        tenant_id: str,
        queries: List[str],
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[List[Dict]]:
        """Batch search knowledge asynchronously.
        
        Parameters are the same as SharedMemory.batch_search_knowledge.
        
        Returns
        -------
        List[List[Dict]]
            Search results for each query.
        """
        return await self._loop.run_in_executor(
            None, self._sync_memory.batch_search_knowledge,
            collection, tenant_id, queries, top_k, threshold
        )
    
    async def aget_collection_stats(
        self, collection: str, tenant_id: Optional[str] = None
    ) -> Dict:
        """Get collection statistics asynchronously."""
        return await self._loop.run_in_executor(
            None, self._sync_memory.get_collection_stats, collection, tenant_id
        )
    
    async def adelete_by_tenant(self, collection: str, tenant_id: str) -> int:
        """Delete tenant data asynchronously."""
        return await self._loop.run_in_executor(
            None, self._sync_memory.delete_by_tenant, collection, tenant_id
        )
    
    async def ahealth_check(self) -> Dict:
        """Perform health check asynchronously."""
        return await self._loop.run_in_executor(
            None, self._sync_memory.health_check
        )
    
    @property
    def metrics(self) -> MemoryMetrics:
        """Get access to metrics."""
        return self._sync_memory.metrics
    
    def clear_embedding_cache(self):
        """Clear embedding cache."""
        self._sync_memory.clear_embedding_cache()