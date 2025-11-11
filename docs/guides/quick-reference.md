# Quick Reference

> Fast lookup for common commands, Python snippets, and configuration helpers used across the multi-agent-brain repository.

## 1. Command Cheatsheet

| Task | Command | Notes |
|------|---------|-------|
| Install dependencies | `make install` | Creates `.venv`, upgrades `pip`, installs `requirements.txt`. |
| Launch OpenAgents network | `make run-network` | Starts HTTP and gRPC transports defined in `config.yaml`. |
| Start Studio UI | `make studio` | Opens the web UI on port 8050 for monitoring. |
| Bring up Milvus Lite | `make milvus-lite` | Spins up a local Milvus container (Docker required). |
| Run full test suite | `make test` | Delegates to `scripts/run_tests.sh` (quiet mode by default). |
| Run unit tests only | `make test-fast` | Excludes `slow` and `integration` markers. |
| Generate coverage | `make cov` | Produces `coverage.xml` and `htmlcov/`. |
| Lint / Format | `make lint` / `make format` | Wraps `scripts/lint.sh` and `scripts/format.sh`. |
| Quick smoke check | `make quick-verify` | Runs `scripts/quick_verify.py --run` for targeted suites. |

## 2. Configuration Helpers

```python
from utils import get_openai_client, get_agent_config, get_agent_answer_verbose

# Global client inferred from configuration precedence
client = get_openai_client()

# Agent-specific configuration
coord_config = get_agent_config("coordination")
verbose = get_agent_answer_verbose("coordination")
print(coord_config.chat.model, coord_config.embedding.model, verbose)
```

Update `.env` to override runtime settings. Reference values:

```ini
CHAT_API_KEY=sk-xxx
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_MODEL=gpt-4o-mini
CHAT_API_PROVIDER=openai

EMBEDDING_API_KEY=sk-emb
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_MODEL=text-embedding-3-large
EMBEDDING_API_PROVIDER=openai
EMBEDDING_DIMENSION=3072

MILVUS_URI=http://localhost:19530
```

See the [Configuration Guide](../configuration/guide.md) for precedence, provider cheat sheets, and troubleshooting.

## 3. OpenAI Client Usage

```python
from utils import OpenAIClientWrapper
from utils import get_agent_config

coord_client = OpenAIClientWrapper(config=get_agent_config("coordination"))

completion = coord_client.get_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful coordinator."},
        {"role": "user", "content": "Summarise the shared memory module."},
    ],
    temperature=0.2,
    max_tokens=300,
)
print(completion.choices[0].message.content)

embeddings = coord_client.get_embeddings_batch([
    "Milvus collection schema",
    "DevOps deployment checklist",
])
print(len(embeddings), len(embeddings[0]))
```

## 4. SharedMemory Snippets

```python
from agents.shared_memory import SharedMemory

memory = SharedMemory(agent_name="coordination")

memory.store_knowledge(
    collection="expert_knowledge",
    tenant_id="project-a",
    content={
        "expert_domain": "milvus",
        "summary": "How to bootstrap Milvus Lite",
    },
    metadata={"source_agent": "coordination"},
)

results = memory.search_knowledge(
    collection="expert_knowledge",
    tenant_id="project-a",
    query="Milvus Lite quickstart",
    top_k=3,
    threshold=0.72,
)
print(results)
```

## 5. Agent Orchestration Patterns

```python
from agents.coordination.agent import CoordinationAgent
from agents.base import AgentMessage

agent = CoordinationAgent()
message = AgentMessage(
    content="Outline the configuration precedence for chat and embedding APIs.",
    tenant_id="project-a",
)

response = agent.handle_message(message)
print(response.content)
```

> The coordination agent handles expert dispatch and shared memory lookups automatically. Provide a `tenant_id` to maintain isolation.

## 6. Useful Links

- [Quickstart](../getting-started/quickstart.md)
- [Configuration Guide](../configuration/guide.md)
- [Testing Reference](../testing/README.md)
- [Architecture Overview](../architecture/overview.md)
- [Troubleshooting](troubleshooting.md)
- [ADR Log](../adr/README.md)

Consult the [Documentation Hub](../README.md) when you need a broader tour of the available guides.
