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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import openai
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.embedding import Embedding
from pydantic import BaseModel, Field


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI client wrapper."""
    
    api_key: str
    base_url: Optional[str] = None
    default_model: str = "gpt-3.5-turbo"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    
    @classmethod
    def from_env(cls) -> OpenAIConfig:
        """Load configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            default_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("OPENAI_RETRY_DELAY", "1.0")),
            max_retry_delay=float(os.getenv("OPENAI_MAX_RETRY_DELAY", "60.0")),
        )


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
            Optional configuration. If not provided, loads from environment.
        """
        self.config = config or OpenAIConfig.from_env()
        self._client: Optional[OpenAI] = None
        
        logger.info(
            "OpenAI client wrapper initialized",
            extra={
                "base_url": self.config.base_url or "default",
                "default_model": self.config.default_model,
                "embedding_model": self.config.embedding_model,
            }
        )
    
    @property
    def client(self) -> OpenAI:
        """Get or create the OpenAI client instance."""
        if self._client is None:
            client_kwargs = {
                "api_key": self.config.api_key,
                "timeout": self.config.timeout,
                "max_retries": 0,  # We handle retries ourselves
            }
            
            if self.config.base_url:
                client_kwargs["base_url"] = self.config.base_url
            
            self._client = OpenAI(**client_kwargs)
            logger.debug("OpenAI client created")
        
        return self._client
    
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
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
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
                
                if attempt < self.config.max_retries:
                    delay = min(
                        self.config.retry_delay * (2 ** attempt),
                        self.config.max_retry_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries + 1,
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
            "model": model or self.config.default_model,
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
                self.client.chat.completions.create,
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
        
        model = model_override or self.config.embedding_model
        
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
                self.client.embeddings.create,
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
            return True
        except Exception as e:
            raise OpenAIError(f"Configuration validation failed: {e}", e)


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