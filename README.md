# multi-agent-brain

[![CI · Python & Docs](https://img.shields.io/github/actions/workflow/status/ldc861117/multi-agent-brain/python-ci.yml?branch=main&label=CI%20%C2%B7%20Python%20%26%20Docs&logo=github)](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml)

> OpenAgents-powered multi-agent network with Milvus-backed shared memory and provider-agnostic LLM access.

## Highlights

- 🤝 **Coordinated experts** – `CoordinationAgent` routes work to Python, Milvus, and DevOps specialists.
- 🧠 **Persistent memory** – Milvus collections plus an embedding cache capture knowledge and collaboration history.
- 🔌 **Configurable providers** – Split `CHAT_API_*` and `EMBEDDING_API_*` settings with per-agent overrides in `config.yaml`.
- 🧩 **Extensible scaffolding** – Implement any new agent by inheriting `BaseAgent` and wiring it into `channels`.

## Quickstart

1. Clone the repository and enter the directory.
2. Create a virtual environment and install dependencies:
   ```bash
   make install
   ```
3. Copy the environment template and fill in keys (OpenAI, Milvus, etc.):
   ```bash
   cp .env.example .env
   ```
4. Start Milvus Lite (optional) and launch the agent network:
   ```bash
   make milvus-lite  # docker required
   make run-network
   ```
5. Verify health and run the fast test suite:
   ```bash
   curl http://localhost:8700/health
   make test-fast
   ```

Detailed setup instructions live in [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md).

## Documentation

All project documentation has moved under `docs/`.

- [Documentation Hub](docs/README.md) – table of contents for every guide.
- [Configuration Guide](docs/configuration/guide.md) – precedence, overrides, provider notes.
- [Testing Reference](docs/testing/README.md) – pytest layout, Makefile helpers, coverage workflow.
- [Architecture Overview](docs/architecture/overview.md) – system diagram and component responsibilities.
- [Quick Reference](docs/guides/quick-reference.md) – command and API cheat sheet.
- [Troubleshooting](docs/guides/troubleshooting.md) – common failure scenarios and fixes.
- [ADR Log](docs/adr/README.md) – accepted decisions; archives capture legacy reports.

## Everyday Commands

| Command | Description |
|---------|-------------|
| `make install` | Bootstrap `.venv` and install dependencies. |
| `make run-network` | Launch HTTP and gRPC transports using `config.yaml`. |
| `make studio` | Open the OpenAgents Studio UI on port 8050. |
| `make test` / `make test-fast` | Run full or unit-only pytest suites. |
| `make cov` | Execute pytest with coverage reporting. |
| `make quick-verify` | Lightweight smoke validation of critical tests. |

Find more snippets in the [Quick Reference](docs/guides/quick-reference.md).

## Architecture at a Glance

```text
User → CoordinationAgent → Specialist Agents (Python, Milvus, DevOps)
           │                     │
           ▼                     ▼
      SharedMemory ───→ OpenAIClientWrapper (chat + embedding)
```

Shared state persists in Milvus collections (`expert_knowledge`, `collaboration_history`, etc.), while the provider layer is configurable per agent via `ConfigManager`.

## Additional Resources

- [AGENTS manual](AGENTS.md) – machine-readable onboarding for every agent.
- [config.yaml](config.yaml) – default transport, provider, and override settings.
- [Makefile](Makefile) – source of all developer command shortcuts.

## Contributing

1. Fork or branch and follow the quickstart steps above.
2. Update or add documentation under `docs/` rather than scattering Markdown in the root.
3. Run `make test-fast` (or `make test`) before opening a PR.
4. Record significant architectural changes as ADRs and link them from relevant guides.

Your feedback and contributions keep the multi-agent-brain evolving—thank you!
