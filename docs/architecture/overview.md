# Architecture Overview

> High-level map of the multi-agent-brain system, highlighting major services, coordination flow, and shared infrastructure.

## 1. System Snapshot

```text
┌─────────────────────────────────────────────────────────────┐
│                OpenAgents Network (HTTP + gRPC)             │
│  ┌─────────────┬──────────────┬──────────────┬────────────┐ │
│  │ Coordination│ Python Expert│ Milvus Expert│ DevOps     │ │
│  │   Agent     │    Agent     │    Agent     │  Expert    │ │
│  └─────────────┴──────────────┴──────────────┴────────────┘ │
│             ▲                         ▲                     │
│             │ agent responses         │ shared utilities     │
└─────────────┴─────────────────────────┴─────────────────────┘
              │                         │
              │                         └─────────────┐
              ▼                                       ▼
┌─────────────────────────────────────┐  ┌──────────────────────┐
│ SharedMemory (Milvus + Cache)       │  │ BrowserTool          │
│ • expert_knowledge                  │  │ • Search (Tavily,    │
│ • collaboration_history             │  │   DuckDuckGo, etc)   │
│ • web_snapshots                     │  │ • Navigation         │
│ • Embedding cache & metrics         │  │   (Playwright)       │
└─────────────────────────────────────┘  │ • Content extraction │
              │                          └──────────────────────┘
              ▼                                       
┌─────────────────────────────────────────────────────────────┐
│ OpenAIClientWrapper (provider-agnostic)                     │
│ • Chat & embedding endpoints                                │
│ • Exponential backoff / retry budgeting                     │
│ • ProviderType: openai, ollama, custom                      │
└─────────────────────────────────────────────────────────────┘
```

## 2. Agents & Responsibilities

| Agent | Role | Highlights |
|-------|------|------------|
| `CoordinationAgent` | Orchestrates conversations, routes to specialists, performs synthesis, and persists collaboration traces. | Async dispatch via `asyncio.gather`, configurable expert routing, knowledge retrieval via SharedMemory. |
| `GeneralAgent` | Public entry point for lightweight queries or delegation to the coordinator. | Provides minimal responses and redirection hints. |
| `PythonExpertAgent` | Placeholder for Python-specific tasks. | Shares configuration and memory helpers; ready for execution tooling. |
| `MilvusExpertAgent` | Vector database specialist scaffold. | Offers structured answers about collection management and embeddings. |
| `DevOpsExpertAgent` | DevOps & infrastructure scaffold. | Future home for CI/CD procedures. |

Agents inherit from `BaseAgent` and return `AgentResponse` objects that include content plus metadata. All share the same utilities exported from `utils/__init__.py` (notably `get_openai_client`, `OpenAIClientWrapper`, and `SharedMemory`).

## 3. Configuration Data Flow

```text
config.yaml (api_config + agent_overrides)
        │           ▲
        ▼           │
ConfigManager ←─────┘
  │  get_global_config()   # applies .env overrides & legacy fallbacks
  │  get_agent_config(name)
  └─ get_agent_answer_verbose(name)
        │
        ▼
OpenAIClientWrapper(config)
        │
        ▼
Agents & SharedMemory
```

See the [Configuration Guide](../configuration/guide.md) for precedence rules and provider examples.

## 4. Knowledge & Memory Layer

- **Milvus** provides persistent semantic search through collections such as `expert_knowledge`, `collaboration_history`, and `web_snapshots`.
- **EmbeddingCache** deduplicates embedding calls and tracks metrics.
- **SharedMemory** exposes `store_knowledge`, `search_knowledge`, and health checks. Deeper internals are documented in [Shared Memory Deep Dive](shared-memory.md).

## 5. Tool Integration Layer

- **BrowserTool** enables agents to search the web and navigate pages:
  - Multiple search providers (Tavily, DuckDuckGo, Bing, Google, SearXNG)
  - Browser automation via Playwright for full page navigation
  - Content extraction using BeautifulSoup
  - Explicit opt-in for memory persistence
- Agents access tools through `BaseAgent.tools()` and `_get_browser_tool()`
- Tool configuration follows the same override patterns as LLM APIs
- See [Browser Tool Guide](../tools/browser_tool.md) for usage details

## 6. Testing & Observability Hooks

- Unit suites validate configuration loading, OpenAI client behaviour, shared memory storage, browser tool integration, and coverage utilities. Refer to the [Testing Reference](../testing/README.md).
- Logging leverages `loguru` with defaults defined in `config.yaml`'s `logging` section. Browser tool operations include structured logging with correlation IDs.
- Metrics from `SharedMemory.metrics` expose cache hit ratios and embedding call counts. Browser tool usage is tracked via the observability system when `ENABLE_METRICS=true`.

## 7. Further Reading

- [Code Map](codemap.md) – Directory-level breakdown and runtime pathways.
- [Agent Interaction Patterns](../guides/interaction.md) – How messages move between agents.
- [Troubleshooting](../guides/troubleshooting.md) – Common operational issues and mitigations.
