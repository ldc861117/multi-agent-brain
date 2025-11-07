# Configuration Structure Migration Guide

## Overview

The multi-agent-brain project has been updated to support separate chat and embedding API endpoints with provider flexibility. This document explains the new configuration structure and how to migrate existing configurations.

## Key Changes

### 1. Separate API Configuration

The system now supports separate configuration for chat completions and embeddings:

- **Chat API**: Used for LLM chat completions (GPT, Claude, etc.)
- **Embedding API**: Used for text embeddings (vector generation)

### 2. Provider Flexibility

Support for multiple providers:
- `openai`: OpenAI and OpenAI-compatible APIs
- `ollama`: Local Ollama instances
- `custom`: Other custom endpoints

### 3. Per-Agent Model Overrides

Agents can override global defaults via `config.yaml`:
```yaml
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
```

## New Environment Variables

### Chat API Configuration
- `CHAT_API_KEY`: API key for chat completions
- `CHAT_API_BASE_URL`: Base URL for chat API
- `CHAT_API_MODEL`: Default chat model
- `CHAT_API_PROVIDER`: Provider type (openai, ollama, custom)
- `CHAT_API_TIMEOUT`: Request timeout
- `CHAT_API_MAX_RETRIES`: Maximum retry attempts
- `CHAT_API_RETRY_DELAY`: Initial retry delay
- `CHAT_API_MAX_RETRY_DELAY`: Maximum retry delay

### Embedding API Configuration
- `EMBEDDING_API_KEY`: API key for embeddings (optional for local providers)
- `EMBEDDING_API_BASE_URL`: Base URL for embedding API
- `EMBEDDING_API_MODEL`: Default embedding model
- `EMBEDDING_API_PROVIDER`: Provider type (openai, ollama, custom)
- `EMBEDDING_DIMENSION`: Embedding vector dimension
- `EMBEDDING_API_TIMEOUT`: Request timeout
- `EMBEDDING_API_MAX_RETRIES`: Maximum retry attempts
- `EMBEDDING_API_RETRY_DELAY`: Initial retry delay
- `EMBEDDING_API_MAX_RETRY_DELAY`: Maximum retry delay

## Backward Compatibility

### Legacy Environment Variables (Still Supported)
- `OPENAI_API_KEY` → Falls back to `CHAT_API_KEY`
- `OPENAI_BASE_URL` → Falls back to both `CHAT_API_BASE_URL` and `EMBEDDING_API_BASE_URL`
- `OPENAI_MODEL` → Falls back to `CHAT_API_MODEL`
- `EMBEDDING_MODEL` → Falls back to `EMBEDDING_API_MODEL`
- `EMBEDDING_DIMENSION` → Falls back to `EMBEDDING_DIMENSION`

### Fallback Behavior
1. If new variables are set, they take precedence
2. If new variables are not set, system falls back to legacy variables
3. If embedding API is not configured, it falls back to chat API settings

## Configuration Examples

### Example 1: DeepSeek for Chat, OpenAI for Embeddings

```bash
# .env file
CHAT_API_KEY=sk-deepseek-key
CHAT_API_BASE_URL=https://api.deepseek.com/v1
CHAT_API_MODEL=deepseek-chat
CHAT_API_PROVIDER=custom

EMBEDDING_API_KEY=sk-openai-key
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_MODEL=text-embedding-3-small
EMBEDDING_API_PROVIDER=openai
EMBEDDING_DIMENSION=1536
```

### Example 2: Local Ollama for Both

```bash
# .env file
CHAT_API_KEY=ollama
CHAT_API_BASE_URL=http://localhost:11434/v1
CHAT_API_MODEL=qwen2:7b
CHAT_API_PROVIDER=ollama

EMBEDDING_API_KEY=ollama
EMBEDDING_API_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_MODEL=nomic-embed-text
EMBEDDING_API_PROVIDER=ollama
EMBEDDING_DIMENSION=768
```

### Example 3: Mixed Configuration with Agent Overrides

```yaml
# config.yaml
api_config:
  chat_api:
    provider: "openai"
    model: "gpt-3.5-turbo"
  
  embedding_api:
    provider: "openai"
    model: "text-embedding-3-small"
    dimension: 1536
  
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
    python_expert:
      chat_model: "gpt-4"
```

## Code Changes

### Agent Initialization

Agents now use the new configuration system:

```python
from utils import get_agent_config, OpenAIClientWrapper

class MyAgent(BaseAgent):
    def __init__(self):
        # Get agent-specific configuration
        agent_config = get_agent_config(self.name)
        self.client = OpenAIClientWrapper(config=agent_config)
        
        # SharedMemory with agent-specific config
        self.memory = SharedMemory(agent_name=self.name)
```

### Configuration Access

```python
from utils import get_config_manager

config_manager = get_config_manager()

# Get global configuration
global_config = config_manager.get_global_config()

# Get agent-specific configuration
agent_config = config_manager.get_agent_config("coordination")

# Get specific settings
chat_model = config_manager.get_agent_chat_model("coordination")
embedding_model = config_manager.get_agent_embedding_model("coordination")
embedding_dim = config_manager.get_agent_embedding_dimension("coordination")
```

## Migration Steps

### For Existing Users

1. **No immediate action required** - existing configurations continue to work
2. **Optional migration** - update to new variable names for better clarity
3. **Consider agent overrides** - for specialized use cases

### For New Deployments

1. Use new variable names (`CHAT_API_*`, `EMBEDDING_API_*`)
2. Configure per-agent overrides in `config.yaml` if needed
3. Test with your specific provider combinations

## Testing

### Configuration Validation

```python
from utils import get_agent_config

# Test configuration loading
try:
    config = get_agent_config("coordination")
    print(f"Chat model: {config.chat_api.model}")
    print(f"Embedding model: {config.embedding_api.model}")
    print(f"Embedding dimension: {config.embedding_api.dimension}")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Provider Testing

```python
from utils import OpenAIClientWrapper, get_agent_config

# Test chat API
config = get_agent_config("coordination")
client = OpenAIClientWrapper(config=config)

try:
    response = client.get_chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10
    )
    print("Chat API working")
except Exception as e:
    print(f"Chat API error: {e}")

try:
    embedding = client.get_embedding_vector("Hello world")
    print(f"Embedding API working (dimension: {len(embedding)})")
except Exception as e:
    print(f"Embedding API error: {e}")
```

## Troubleshooting

### Common Issues

1. **Missing API Key**: Ensure `CHAT_API_KEY` or `OPENAI_API_KEY` is set
2. **Wrong Dimension**: Match `EMBEDDING_DIMENSION` to your embedding model
3. **Provider Mismatch**: Ensure `*_API_PROVIDER` matches your endpoint
4. **Network Issues**: Check `*_API_BASE_URL` accessibility

### Debug Logging

Enable debug logging to see configuration loading:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from utils import get_agent_config
config = get_agent_config("coordination")
```

### Fallback Behavior

If embedding API is not working, the system will:
1. Log a warning about fallback
2. Use chat API settings for embeddings
3. Continue operation with reduced functionality

## Future Enhancements

- Support for additional providers (Cohere, Anthropic, etc.)
- Dynamic configuration reloading
- Configuration validation and health checks
- Performance metrics per provider
- Automatic provider failover