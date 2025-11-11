# Troubleshooting Guide

> Resolve common configuration, provider, and infrastructure issues encountered while running multi-agent-brain.

## Quick Reference Table

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `Milvus connection refused` | Milvus container or remote service not running; URI incorrect. | Start Milvus with `make milvus-lite` or point `MILVUS_URI` to a reachable endpoint (e.g. `http://localhost:19530`). |
| `embedding dimension mismatch (expected X, got Y)` | Embedding model changed without updating configuration. | Align `embedding_dimension` in `.env` or `api_config.agent_overrides` to match the model spec. |
| `OpenAIError: Rate limit` | Provider throttling active connection. | Rotate API keys, increase `CHAT_API_MAX_RETRIES`/`CHAT_API_MAX_RETRY_DELAY`, or temporarily switch providers. |
| `agent_overrides` ignored | Environment variables override YAML settings. | Remove overlapping `CHAT_API_*` or `EMBEDDING_API_*` entries, call `from utils import reload_config; reload_config()`, and restart long-lived services. |
| `Studio` cannot connect | Network transports are down or ports occupied. | Verify `make run-network` is active and ports 8700/8050 are free. |
| Pytest environments leaking keys | `.env` loaded during tests or `patch.dict` used. | Follow the patterns in `tests/conftest.py` and rely on `pytest.MonkeyPatch` fixtures. |

## Diagnostic Tips

1. **Check health endpoints** – `curl http://localhost:8700/health` confirms the HTTP transport and Milvus connectivity.
2. **Inspect logs** – `loguru` outputs to stdout by default; adjust `config.yaml` if you need JSON or file logging.
3. **Validate configuration** – Run `python -m utils.config_validator --path config.yaml` for quick sanity checks.
4. **Regenerate embeddings** – Clear cache entries or adjust prompts if embedding payloads change unexpectedly.
5. **Confirm overrides** – Print `get_agent_config(<name>)` in a Python shell to ensure agent-specific settings apply.

## When to Escalate

- Persistent provider errors after retries → consider switching to a fallback provider or reducing concurrency.
- Milvus schema changes → update embedding dimensions and collection names in both configuration and code (the archive contains historical context).
- New agents or transports → document the approach in the [Architecture Decision Records](../adr/README.md) to keep the team aligned.

For historical investigations or previous post-mortems, consult the [archive index](../archive/README.md).
