"""OpenAI client wrapper for multi-agent scaffolding.

This module provides a centralized OpenAI client with support for custom endpoints,
error handling, retry logic, and environment-based configuration. It's designed to
be used across all agents and shared memory components in the multi-agent system.

Features:
- Compatible with OpenAI, DeepSeek, Moonshot, and other OpenAI-compatible providers
- Automatic retry with exponential backoff
- Comprehensive error handling and logging
- Environment-based configuration with dotenv support
- Type-safe interfaces using Pydantic models
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import openai
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.embedding import Embedding
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported provider types for APIs."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class ChatAPIConfig:
    """Configuration for chat completion API."""
    
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    provider: ProviderType = ProviderType.OPENAI
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    
    @classmethod
    def from_env(cls) -> ChatAPIConfig:
        """Load chat API configuration from environment variables."""
        load_dotenv()
        
        api_key = os.getenv("CHAT_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("CHAT_API_KEY or OPENAI_API_KEY environment variable is required")
        
        base_url = os.getenv("CHAT_API_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        model = os.getenv("CHAT_API_MODEL") or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        provider_str = os.getenv("CHAT_API_PROVIDER", "openai")
        
        try:
            provider = ProviderType(provider_str)
        except ValueError:
            logger.warning(f"Unknown provider '{provider_str}', defaulting to 'openai'")
            provider = ProviderType.OPENAI
        
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider=provider,
            timeout=int(os.getenv("CHAT_API_TIMEOUT", "30")),
            max_retries=int(os.getenv("CHAT_API_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("CHAT_API_RETRY_DELAY", "1.0")),
            max_retry_delay=float(os.getenv("CHAT_API_MAX_RETRY_DELAY", "60.0")),
        )


@dataclass
class EmbeddingAPIConfig:
    """Configuration for embedding API."""
    
    api_key: Optional[str] = None  # Optional for local providers like Ollama
    base_url: Optional[str] = None
    model: str = "text-embedding-3-small"
    provider: ProviderType = ProviderType.OPENAI
    dimension: int = 1536
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    
    @classmethod
    def from_env(cls) -> EmbeddingAPIConfig:
        """Load embedding API configuration from environment variables."""
        load_dotenv()
        
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("EMBEDDING_API_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        model = os.getenv("EMBEDDING_API_MODEL") or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        provider_str = os.getenv("EMBEDDING_API_PROVIDER", "openai")
        
        try:
            provider = ProviderType(provider_str)
        except ValueError:
            logger.warning(f"Unknown provider '{provider_str}', defaulting to 'openai'")
            provider = ProviderType.OPENAI
        
        # Set default dimensions based on model
        dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
        if dimension == 1536 and model.endswith("-large"):
            dimension = 3072
        elif dimension == 3072 and model.endswith("-small"):
            dimension = 1536
        
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider=provider,
            dimension=dimension,
            timeout=int(os.getenv("EMBEDDING_API_TIMEOUT", "30")),
            max_retries=int(os.getenv("EMBEDDING_API_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("EMBEDDING_API_RETRY_DELAY", "1.0")),
            max_retry_delay=float(os.getenv("EMBEDDING_API_MAX_RETRY_DELAY", "60.0")),
        )


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI client wrapper with separate chat and embedding APIs."""
    
    chat_api: ChatAPIConfig = field(default_factory=ChatAPIConfig.from_env)
    embedding_api: EmbeddingAPIConfig = field(default_factory=EmbeddingAPIConfig.from_env)
    
    @classmethod
    def from_env(cls) -> OpenAIConfig:
        """Load configuration from environment variables."""
        return cls(
            chat_api=ChatAPIConfig.from_env(),
            embedding_api=EmbeddingAPIConfig.from_env(),
        )
    
    @classmethod
    def from_env_with_fallback(cls) -> OpenAIConfig:
        """Load configuration with fallback for embedding API to chat API."""
        chat_config = ChatAPIConfig.from_env()
        
        # Try to load embedding config
        try:
            embedding_config = EmbeddingAPIConfig.from_env()
            # If embedding API key is None but chat API key exists, fallback
            if embedding_config.api_key is None and chat_config.api_key:
                logger.info("Embedding API key not set, falling back to chat API key")
                embedding_config.api_key = chat_config.api_key
            # If embedding base URL is None but chat base URL exists, fallback
            if embedding_config.base_url is None and chat_config.base_url:
                logger.info("Embedding API base URL not set, falling back to chat API base URL")
                embedding_config.base_url = chat_config.base_url
        except Exception as e:
            logger.warning(f"Failed to load embedding API config, falling back to chat API: {e}")
            # Fallback to chat API settings
            embedding_config = EmbeddingAPIConfig(
                api_key=chat_config.api_key,
                base_url=chat_config.base_url,
                provider=chat_config.provider,
                timeout=chat_config.timeout,
                max_retries=chat_config.max_retries,
                retry_delay=chat_config.retry_delay,
                max_retry_delay=chat_config.max_retry_delay,
            )
        
        return cls(
            chat_api=chat_config,
            embedding_api=embedding_config,
        )
    
    # Legacy properties for backward compatibility
    @property
    def api_key(self) -> str:
        return self.chat_api.api_key
    
    @property
    def base_url(self) -> Optional[str]:
        return self.chat_api.base_url
    
    @property
    def default_model(self) -> str:
        return self.chat_api.model
    
    @property
    def embedding_model(self) -> str:
        return self.embedding_api.model
    
    @property
    def embedding_dimension(self) -> int:
        return self.embedding_api.dimension


class ChatMessage(BaseModel):
    """Chat message model for type safety."""
    
    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")
    name: Optional[str] = Field(None, description="Optional message name")


class OpenAIError(Exception):
    """Custom exception for OpenAI client errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class OpenAIClientWrapper:
    """Centralized OpenAI client wrapper with error handling and retry logic."""
    
    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize the OpenAI client wrapper.
        
        Parameters
        ----------
        config:
            Optional configuration. If not provided, loads from environment with fallback.
        """
        self.config = config or OpenAIConfig.from_env_with_fallback()
        self._chat_client: Optional[OpenAI] = None
        self._embedding_client: Optional[OpenAI] = None
        
        logger.info(
            "OpenAI client wrapper initialized",
            extra={
                "chat_base_url": self.config.chat_api.base_url or "default",
                "chat_model": self.config.chat_api.model,
                "embedding_base_url": self.config.embedding_api.base_url or "default",
                "embedding_model": self.config.embedding_api.model,
                "embedding_provider": self.config.embedding_api.provider.value,
            }
        )
    
    @property
    def chat_client(self) -> OpenAI:
        """Get or create the chat API client instance."""
        if self._chat_client is None:
            client_kwargs = {
                "api_key": self.config.chat_api.api_key,
                "timeout": self.config.chat_api.timeout,
                "max_retries": 0,  # We handle retries ourselves
            }
            
            if self.config.chat_api.base_url:
                client_kwargs["base_url"] = self.config.chat_api.base_url
            
            self._chat_client = OpenAI(**client_kwargs)
            logger.debug("Chat API client created")
        
        return self._chat_client
    
    @property
    def embedding_client(self) -> OpenAI:
        """Get or create the embedding API client instance."""
        if self._embedding_client is None:
            client_kwargs = {
                "api_key": self.config.embedding_api.api_key or "dummy-key-for-local",
                "timeout": self.config.embedding_api.timeout,
                "max_retries": 0,  # We handle retries ourselves
            }
            
            if self.config.embedding_api.base_url:
                client_kwargs["base_url"] = self.config.embedding_api.base_url
            
            self._embedding_client = OpenAI(**client_kwargs)
            logger.debug("Embedding API client created")
        
        return self._embedding_client
    
    @property
    def client(self) -> OpenAI:
        """Legacy property for backward compatibility. Returns chat client."""
        return self.chat_client
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic.
        
        Parameters
        ----------
        func:
            Function to execute
        *args, **kwargs:
            Arguments to pass to the function
            
        Returns
        -------
        Any
            Function result
            
        Raises
        ------
        OpenAIError
            If all retries are exhausted
        """
        # Determine which config to use for retry settings based on the function
        config = self.config.chat_api
        if hasattr(func, '__self__') and func.__self__ == self._embedding_client:
            config = self.config.embedding_api
        
        last_error = None
        
        for attempt in range(config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                # Don't retry on certain error types
                if isinstance(e, openai.AuthenticationError):
                    logger.error("Authentication error, not retrying", extra={"error": str(e)})
                    raise OpenAIError(f"Authentication failed: {e}", e)
                elif isinstance(e, openai.NotFoundError):
                    logger.error("Resource not found, not retrying", extra={"error": str(e)})
                    raise OpenAIError(f"Resource not found: {e}", e)
                
                if attempt < config.max_retries:
                    delay = min(
                        config.retry_delay * (2 ** attempt),
                        config.max_retry_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": config.max_retries + 1,
                            "error": str(e),
                            "retry_delay": delay,
                        }
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All retries exhausted",
                        extra={
                            "attempts": attempt + 1,
                            "final_error": str(e),
                        }
                    )
        
        raise OpenAIError(f"All retries exhausted: {last_error}", last_error)
    
    def get_chat_completion(
        self,
        messages: Union[List[Dict[str, str]], List[ChatMessage]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletion:
        """Get chat completion from OpenAI.
        
        Parameters
        ----------
        messages:
            List of chat messages. Can be dict or ChatMessage objects.
        model:
            Model to use. If not provided, uses config.default_model.
        temperature:
            Sampling temperature (0.0 to 2.0).
        max_tokens:
            Maximum tokens to generate.
        **kwargs:
            Additional parameters to pass to the OpenAI API.
            
        Returns
        -------
        ChatCompletion
            OpenAI chat completion response.
            
        Raises
        ------
        OpenAIError
            If the API call fails.
        """
        # Convert messages to the expected format
        if messages and isinstance(messages[0], ChatMessage):
            messages = [msg.model_dump() for msg in messages]
        
        # Validate messages
        if not messages:
            raise OpenAIError("Messages list cannot be empty")
        
        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise OpenAIError(f"Invalid message format: {msg}")
        
        # Prepare request parameters
        request_params = {
            "model": model or self.config.chat_api.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens is not None:
            request_params["max_tokens"] = max_tokens
        
        # Add any additional kwargs
        request_params.update(kwargs)
        
        logger.info(
            "Requesting chat completion",
            extra={
                "model": request_params["model"],
                "message_count": len(messages),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        
        try:
            result = self._retry_with_backoff(
                self.chat_client.chat.completions.create,
                **request_params
            )
            
            logger.info(
                "Chat completion successful",
                extra={
                    "model": result.model,
                    "usage": result.usage.model_dump() if result.usage else None,
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Chat completion failed",
                extra={
                    "model": request_params["model"],
                    "error": str(e),
                }
            )
            raise OpenAIError(f"Chat completion failed: {e}", e)
    
    def get_embedding(
        self,
        texts: Union[str, List[str]],
        model_override: Optional[str] = None,
        **kwargs
    ) -> List[Embedding]:
        """Get embeddings from OpenAI.
        
        Parameters
        ----------
        texts:
            Text or list of texts to embed.
        model_override:
            Override the default embedding model.
        **kwargs:
            Additional parameters to pass to the OpenAI API.
            
        Returns
        -------
        List[Embedding]
            List of embedding objects.
            
        Raises
        ------
        OpenAIError
            If the API call fails.
        """
        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]
        
        if not texts:
            raise OpenAIError("Texts list cannot be empty")
        
        # Validate texts
        for i, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise OpenAIError(f"Invalid text at index {i}: {text}")
        
        model = model_override or self.config.embedding_api.model
        
        logger.info(
            "Requesting embeddings",
            extra={
                "model": model,
                "text_count": len(texts),
                "total_chars": sum(len(text) for text in texts),
            }
        )
        
        try:
            result = self._retry_with_backoff(
                self.embedding_client.embeddings.create,
                model=model,
                input=texts,
                **kwargs
            )
            
            logger.info(
                "Embeddings successful",
                extra={
                    "model": model,
                    "usage": result.usage.model_dump() if result.usage else None,
                    "embedding_count": len(result.data),
                }
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Embeddings failed",
                extra={
                    "model": model,
                    "error": str(e),
                }
            )
            raise OpenAIError(f"Embeddings failed: {e}", e)
    
    def get_embedding_vector(
        self,
        texts: Union[str, List[str]],
        model_override: Optional[str] = None,
        **kwargs
    ) -> List[List[float]]:
        """Get embedding vectors as raw lists.
        
        This is a convenience method that extracts just the embedding vectors
        from the full Embedding objects.
        
        Parameters
        ----------
        texts:
            Text or list of texts to embed.
        model_override:
            Override the default embedding model.
        **kwargs:
            Additional parameters to pass to the OpenAI API.
            
        Returns
        -------
        List[List[float]]
            List of embedding vectors.
        """
        embeddings = self.get_embedding(texts, model_override, **kwargs)
        return [emb.embedding for emb in embeddings]
    
    def validate_config(self) -> bool:
        """Validate the current configuration.
        
        Returns
        -------
        bool
            True if configuration is valid.
            
        Raises
        ------
        OpenAIError
            If configuration is invalid.
        """
        try:
            # Test basic connectivity with a minimal request
            self.get_chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            # Test embedding connectivity (if different endpoint)
            if (self.config.embedding_api.base_url and 
                self.config.embedding_api.base_url != self.config.chat_api.base_url):
                self.get_embedding_vector("test")
            
            return True
        except Exception as e:
            raise OpenAIError(f"Configuration validation failed: {e}", e)
    
    def get_embeddings_batch(self, texts: List[str], **kwargs) -> List[Embedding]:
        """Batch embeddings with optimized processing.
        
        This method handles batching for large lists of texts to optimize API calls.
        
        Parameters
        ----------
        texts:
            List of texts to embed.
        **kwargs:
            Additional parameters to pass to the embedding API.
            
        Returns
        -------
        List[Embedding]
            List of embedding objects.
        """
        if not texts:
            return []
        
        # Process in batches to avoid hitting API limits
        batch_size = 100  # Adjust based on provider limits
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.get_embedding(batch, **kwargs)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings


# Global instance for easy access
_global_client: Optional[OpenAIClientWrapper] = None


def get_openai_client() -> OpenAIClientWrapper:
    """Get the global OpenAI client instance.
    
    Returns
    -------
    OpenAIClientWrapper
        Global client instance.
    """
    global _global_client
    if _global_client is None:
        _global_client = OpenAIClientWrapper()
    return _global_client


def reset_openai_client():
    """Reset the global OpenAI client instance.
    
    This is useful for testing or when configuration changes.
    """
    global _global_client
    _global_client = None