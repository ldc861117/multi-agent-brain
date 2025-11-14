# Project Codemap · multi-agent-brain

> Snapshot of the current architecture, runtime layers, and operational checklists for the multi-agent-brain repository.

---

## Overview

multi-agent-brain packages an OpenAgents network that coordinates multiple specialist agents, persists shared knowledge in Milvus, and exposes provider-agnostic LLM access. This codemap stays close to the code and configuration surface to help contributors and AI coding agents identify the relevant entry points quickly.

## Current Status

- **Coordination pipeline** is production-ready: [CoordinationAgent](agents/coordination/agent.py) analyses prompts, retrieves shared memory, dispatches experts, and records collaboration traces.
- **Specialist agents** (`python_expert`, `milvus_expert`, `devops_expert`) currently return scaffolded responses until runtime tooling is attached.
- **Shared memory** defaults to Milvus but falls back to an in-process store when `TEST_DISABLE_MILVUS=1`, ensuring tests and offline runs do not require an external vector DB.
- **LLM connectivity** is provider-agnostic via `CHAT_API_*` / `EMBEDDING_API_*` environment variables with per-agent overrides.

## Layered Architecture

```text
Transport layer (OpenAgents network defined in config.yaml)
    │
    ├─ Entry channels (agents/general, agents/coordination)
    │
    ├─ Coordination layer (CoordinationAgent orchestrates experts)
    │
    ├─ Specialist agents (python_expert, milvus_expert, devops_expert)
    │
    ├─ Knowledge layer (agents/shared_memory.SharedMemory ↔ Milvus or in-memory fallback)
    │
    └─ Provider layer (utils.openai_client.OpenAIClientWrapper + ConfigManager)
```

Supporting utilities such as `utils/observability.py` supply telemetry, and `tools/operator` offers a read-only dashboard for local introspection.

## Key Modules/Files

| Path | Purpose |
| --- | --- |
| `agents/base.py` | Declares `BaseAgent` and `AgentResponse`, the interface every agent implements. |
| `agents/coordination/agent.py` | Core orchestration logic: analysis, retrieval, expert dispatch, synthesis, and persistence. |
| `agents/shared_memory.py` | Shared memory client with embedding cache, metrics, and Milvus/in-memory adapters. |
| `utils/config_manager.py` | Loads `config.yaml`, merges environment overrides, and exposes per-agent configuration helpers. |
| `utils/openai_client.py` | Wraps chat and embedding providers with retry/backoff, batching, and configurable models. |
| `docs/README.md` | Documentation hub pointing to architecture, configuration, and troubleshooting guides. |
| `tests/unit/test_env_config.py` | Verifies configuration precedence and per-agent overrides. |
| `scripts/run_tests.sh` | Canonical entry point for running pytest across unit, integration, and slow suites. |

## Configuration & Environment

- Declare provider credentials in `.env` using the `CHAT_API_*` and `EMBEDDING_API_*` keys shown in [.env.example](.env.example). Legacy `OPENAI_*` variables act as a fallback.
- Global defaults live in [config.yaml](config.yaml); agent-specific overrides (model, embedding model, verbosity, embedding dimension) sit in `api_config.agent_overrides`.
- `utils.get_agent_config(name)` and `utils.get_agent_answer_verbose(name)` resolve the merged configuration for the requested agent.
- When Milvus connectivity is unavailable, set `TEST_DISABLE_MILVUS=1` to activate the in-memory SharedMemory backend during tests and local development.

## Testing & CI

- Run the full suite with `make test`; use `make test-fast` for a unit-only pass and `make quick-verify` for scripted sanity checks.
- Static analysis goes through `scripts/lint.sh`, which prefers `ruff` and `flake8` when installed.
- CI is orchestrated by [python-ci.yml](.github/workflows/python-ci.yml), running lint, unit tests, and coverage reporting on pushes and pull requests.
- Tests stub LLM and Milvus dependencies via `pytest.MonkeyPatch` fixtures inside [tests/conftest.py](tests/conftest.py), preventing accidental live calls.

## Recent Changes

- SharedMemory gained an in-memory fallback for environments that export `TEST_DISABLE_MILVUS=1`, improving local reliability.
- Documentation was consolidated around [docs/README.md](docs/README.md) and [AGENTS.md](AGENTS.md) to streamline onboarding for new agents.
- Observability baseline established structured logging and an optional `/metrics` endpoint (see [utils/observability.py](utils/observability.py)).

## Runbook

1. **Bootstrap environment**
   ```bash
   make install
   cp .env.example .env  # populate CHAT_API_* and optional EMBEDDING_API_*
   ```
2. **Launch the network**
   ```bash
   make run-network
   curl http://localhost:8700/health
   ```
3. **Activate Milvus (optional)**
   ```bash
   make milvus-lite
   export MILVUS_URI=http://localhost:19530
   ```
4. **Run tests / lint**
   ```bash
   make test-fast
   make lint
   ```
5. **Operator dashboard** (optional)
   ```bash
   make operator
   ```

## Roadmap

Strategic milestones are tracked in [docs/ROADMAP.md](docs/ROADMAP.md). Roadmap sections cover foundational hardening, UI/UX enablement, and productization, with success metrics and dependency call-outs for each horizon.

## Conventions

- Prefer asynchronous patterns already established in `CoordinationAgent` and reuse `OpenAIClientWrapper` rather than importing SDKs directly.
- Routing and escalation rules belong in `config.yaml`; avoid hardcoding dispatch logic in agents.
- Logging should use the project-wide logger (see `utils/observability.py`) with correlation IDs propagated through responses.
- Format code with `ruff format` (or `black`) and ensure lint via `ruff check` / `flake8` before submitting changes.
- Tests should avoid external dependencies by leveraging the fixtures in `tests/conftest.py` and the `TEST_DISABLE_MILVUS` guard for shared memory.
