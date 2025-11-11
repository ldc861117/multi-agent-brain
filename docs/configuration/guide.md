# Configuration Guide

> Reference for environment variables, YAML defaults, and agent-specific overrides that control the multi-agent-brain runtime.

## 1. Configuration Layers & Precedence

Configuration merges values from multiple sources. When the same field appears in more than one place, the highest priority wins.

| Priority (high → low) | Source | What it covers |
|-----------------------|--------|----------------|
| 1 | `config.yaml` → `api_config` and `agent_overrides` | Default providers, models, embedding dimensions, verbosity flags. |
| 2 | `.env` / system environment (`CHAT_API_*`, `EMBEDDING_API_*`, `MILVUS_*`) | Runtime overrides for keys, base URLs, models, timeouts, and vector DB endpoints. |
| 3 | Legacy variables (`OPENAI_*`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`) | Backward-compatible values recognised by `OpenAIConfig.from_env_with_fallback()`. |

> Tip: Remove conflicting environment variables when you want YAML overrides to apply. Call `from utils import reload_config; reload_config()` after editing configuration during a long-running session.

## 2. Essential Environment Variables

```ini
# Chat API
CHAT_API_KEY=sk-xxx
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_MODEL=gpt-4o-mini
CHAT_API_PROVIDER=openai
CHAT_API_TIMEOUT=60

# Embedding API (falls back to chat API when omitted)
EMBEDDING_API_KEY=sk-emb
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_MODEL=text-embedding-3-large
EMBEDDING_API_PROVIDER=openai
EMBEDDING_DIMENSION=3072

# Milvus
MILVUS_URI=http://localhost:19530
MILVUS_USERNAME=
MILVUS_PASSWORD=
```

Any `*_MAX_RETRIES`, `*_MAX_RETRY_DELAY`, or `*_REQUEST_TIMEOUT` setting listed in `.env.example` is also supported and feeds directly into the `OpenAIClientWrapper` retry policy.

## 3. Agent Overrides

Per-agent customisation lives under `api_config.agent_overrides` in `config.yaml`.

```yaml
api_config:
  chat_api:
    provider: "openai"
    model: "gpt-4o-mini"
  embedding_api:
    provider: "ollama"
    model: "qwen3-embedding:0.6b"
    dimension: 768
  agent_overrides:
    coordination:
      chat_model: "gpt-4o"
      embedding_model: "qwen3-embedding:0.6b"
      embedding_dimension: 768
      answer_verbose: false
    python_expert:
      chat_model: "gpt-4.1-mini"
      answer_verbose: true
```

Helpers:

```python
from utils import get_agent_config, get_agent_answer_verbose

coord_config = get_agent_config("coordination")
verbose = get_agent_answer_verbose("coordination")
```

## 4. Provider Cheat Sheet

| Provider | Chat Settings | Embedding Settings | Notes |
|----------|---------------|--------------------|-------|
| OpenAI | `CHAT_API_PROVIDER=openai`<br>`CHAT_API_BASE_URL=https://api.openai.com/v1` | Defaults to chat settings if embedding fields are omitted. | Requires API key for both chat and embedding. |
| DeepSeek / Moonshot / other OpenAI-compatible | `CHAT_API_PROVIDER=custom`<br>`CHAT_API_BASE_URL=<https endpoint>` | Same as chat or use dedicated model + base URL. | Set the model to provider-specific ID. |
| Ollama (local) | `CHAT_API_PROVIDER=ollama` (optional) | `EMBEDDING_API_PROVIDER=ollama`<br>`EMBEDDING_API_BASE_URL=http://localhost:11434/v1` | Embedding key can be a placeholder (e.g. `ollama`). Ensure the model exists locally. |
| Azure / compatibility layers | `CHAT_API_PROVIDER=custom`<br>`CHAT_API_BASE_URL=<azure endpoint>` | Provide deployment-specific names. | Supply headers via environment if needed. |

## 5. Validating Configuration

- **.env hygiene**: Use `python - <<'PY'` code snippets or the provided pytest fixtures as references for isolating environment variables.
- **Config validator**: `python -m utils.config_validator --path config.yaml` repairs drift compared to `config.default.yaml`.
- **Tests**: `pytest tests/unit/test_env_config.py -vv` exercises precedence, provider validation, and override behaviour. See the [Testing Reference](../testing/README.md) for running selective suites.

## 6. Troubleshooting

1. **Overrides ignored** – Remove overlapping `CHAT_API_*` or `EMBEDDING_API_*` variables, reload configuration, and confirm via logging.
2. **Embedding dimension mismatch** – Align `embedding_dimension` in overrides with the actual model specification.
3. **Provider timeouts** – Increase `CHAT_API_TIMEOUT` / `CHAT_API_MAX_RETRIES` or switch providers temporarily.
4. **Milvus authentication failures** – Supply credentials in `.env` or ensure the URI points to a non-secured local deployment.

For a deeper dive into historical decisions and exhaustive test coverage, consult the [archive index](../archive/README.md) or the ADR log.
