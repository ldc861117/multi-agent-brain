# multi-agent-brain

[![CI · Python & Docs](https://img.shields.io/github/actions/workflow/status/ldc861117/multi-agent-brain/python-ci.yml?branch=main&label=CI%20%C2%B7%20Python%20%26%20Docs&logo=github)](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml)

> OpenAgents-powered multi-agent network with Milvus-backed shared memory and provider-agnostic LLM access.

---

## Status at a Glance

- ✅ **Coordination pipeline implemented** — [CoordinationAgent](agents/coordination/agent.py) analyses incoming questions, retrieves Milvus-backed knowledge, dispatches experts, and persists collaboration traces. The flow is exercised end-to-end in [examples/coordination_agent_example.py](examples/coordination_agent_example.py) and the offline harness at [scripts/verify_multi_expert_dispatch.py](scripts/verify_multi_expert_dispatch.py).
- ✅ **Provider-agnostic configuration** — `ConfigManager` separates chat and embedding providers with per-agent overrides. Behaviour and precedence are covered by [utils/test_env_config.py](utils/test_env_config.py) and [tests/unit/test_openai_client.py](tests/unit/test_openai_client.py).
- ✅ **Shared memory with caching & metrics** — [SharedMemory](agents/shared_memory.py) integrates with Milvus, exposes an embedding cache, and tracks usage statistics. Coverage lives in [tests/unit/test_shared_memory.py](tests/unit/test_shared_memory.py) and [tests/unit/test_shared_memory_minimal.py](tests/unit/test_shared_memory_minimal.py).
- 📚 **Documentation-first workflow** — Comprehensive guides reside in [docs/README.md](docs/README.md), with agent specifics in [AGENTS.md](AGENTS.md) and testing practices in [docs/testing/README.md](docs/testing/README.md).

**Limitations**

- Specialist agents (`python_expert`, `milvus_expert`, `devops_expert`) currently return placeholder guidance until runtime tools are attached.
- Interactive runs require valid LLM credentials; unit tests stub network calls, but launching the network will target the configured providers.
- Persistent memory assumes an accessible Milvus endpoint. Without it, development falls back to local stubs and some features remain inert.

## Roadmap

The phased roadmap covering foundational hardening, UI/UX enablement, and productization lives in [docs/ROADMAP.md](docs/ROADMAP.md). Each horizon lists milestones with acceptance slices, dependencies, and success metrics to guide future tickets.

## Architecture Overview

The network is defined in [config.yaml](config.yaml) as an OpenAgents deployment exposing HTTP (8700) and gRPC (8600) transports. Messages enter through the public `general` channel, escalate to the `CoordinationAgent`, and fan out to domain specialists. Shared context is stored in Milvus via `SharedMemory`, while `OpenAIClientWrapper` mediates chat and embedding providers resolved by `ConfigManager`.

```text
User → general channel → CoordinationAgent
              │
              ├─ python_expert / milvus_expert / devops_expert
              │
              └─ SharedMemory ↔ Milvus (vectors via OpenAIClientWrapper)
                        │
                        └─ ConfigManager (chat / embedding defaults + overrides)
```

Deep dives and diagrams live in [docs/architecture/overview.md](docs/architecture/overview.md) and the [code map](docs/architecture/codemap.md).

## Agents Catalog

| Agent | Entrypoint | Responsibility | Configuration hooks |
| --- | --- | --- | --- |
| `general` | `agents.general:GeneralAgent` | Public entry point that greets users and forwards work to coordination. | `channels.general` in `config.yaml`<br>`routing.default_target` |
| `coordination` | `agents.coordination:CoordinationAgent` | Analyses prompts, retrieves shared knowledge, dispatches experts, and writes collaboration history. | `channels.coordination`<br>`routing.escalations.coordination`<br>`api_config.agent_overrides.coordination`<br>Env overrides such as `COORDINATION_AGENT_MODEL` |
| `python_expert` | `agents.python_expert:PythonExpertAgent` | Placeholder for Python debugging and future code execution support. | `channels.python_expert`<br>`api_config.agent_overrides.python_expert`<br>Env: `PYTHON_EXPERT_MODEL`, `PYTHON_EXPERT_EMBEDDING_MODEL` |
| `milvus_expert` | `agents.milvus_expert:MilvusExpertAgent` | Placeholder for Milvus sizing, schema, and tuning advice. | `channels.milvus_expert`<br>`api_config.agent_overrides.milvus_expert` |
| `devops_expert` | `agents.devops_expert:DevOpsExpertAgent` | Placeholder for CI/CD and infrastructure questions. | `channels.devops_expert`<br>`api_config.agent_overrides.devops_expert` |

All agents inherit from `BaseAgent` and use `AgentResponse`. See [AGENTS.md](AGENTS.md) for the machine-readable playbook, including escalation rules and onboarding checklists.

## Configuration Matrix

| Layer | Location | Keys / Commands | Notes |
| --- | --- | --- | --- |
| Chat API | `.env` (`CHAT_API_*`) | `CHAT_API_BASE_URL`, `CHAT_API_KEY`, `CHAT_API_PROVIDER`, `CHAT_API_MODEL`, `CHAT_API_TIMEOUT`, `CHAT_API_MAX_RETRIES`, … | Required for chat completions. Providers include `openai`, `ollama`, or `custom`. |
| Embedding API | `.env` (`EMBEDDING_API_*`) | `EMBEDDING_API_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_API_PROVIDER`, `EMBEDDING_API_MODEL`, `EMBEDDING_API_TIMEOUT`, … | Optional key for local providers; falls back to chat API settings when unset. |
| Legacy fallback | `.env` (`OPENAI_*`) | `OPENAI_API_KEY`, `OPENAI_API_BASE_URL` | Read only when the new `CHAT_API_*` / `EMBEDDING_API_*` variables are missing. |
| Per-agent env overrides | `.env` | `COORDINATION_AGENT_MODEL`, `PYTHON_EXPERT_EMBEDDING_MODEL`, etc. | Highest precedence for individual agents; override YAML defaults. |
| YAML defaults | [`config.yaml`](config.yaml) → `api_config.chat_api` / `embedding_api` | Provider, model, timeout, retry configuration, embedding dimensions. | Applies when no environment override is present. |
| Agent overrides (YAML) | `config.yaml → api_config.agent_overrides.<agent>` | `chat_model`, `embedding_model`, `embedding_dimension`, `answer_verbose`. | Used by `utils.get_agent_config("<agent>")` and `OpenAIClientWrapper`. |
| Network wiring | `config.yaml → channels`, `routing` | Channel entrypoints, visibility, escalation targets. | Controls which agents the coordination layer can dispatch to. |
| Validation tooling | CLI | `python -m utils.config_validator --path config.yaml --default config.default.yaml` | Validates and optionally repairs YAML against the template. |

Reference [.env.example](.env.example) for annotated samples and consult [docs/configuration/guide.md](docs/configuration/guide.md) for precedence details.

## Setup & Usage Modes

### Quickstart (minimal)

1. Install dependencies and bootstrap the virtual environment:
   ```bash
   make install
   ```
2. Copy the environment template and populate provider keys:
   ```bash
   cp .env.example .env
   # Set CHAT_API_* and (optionally) EMBEDDING_API_* values
   ```
3. Launch the OpenAgents network:
   ```bash
   make run-network
   ```
4. Smoke-test the deployment:
   ```bash
   curl http://localhost:8700/health
   make test-fast
   ```

Detailed steps live in [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md).

### Operator dashboard (CLI)

Launch the read-only operator dashboard to inspect agent status, recent task
runs, the resolved configuration snapshot, and a filtered log tail:

```bash
make operator
# or
python -m tools.operator --log-file openagents.log
```

Use `--filter-agent`, `--filter-run`, or `--filter-correlation` to narrow the log
pane, and adjust `--refresh` for slower or faster updates. Secrets such as API
keys are automatically redacted in the configuration view.

### Full local stack (Milvus)

1. Ensure Docker is available, then start Milvus Lite:
   ```bash
   make milvus-lite
   ```
2. Point the agents at the running instance (in `.env` or your shell):
   ```bash
   export MILVUS_URI=http://localhost:19530
   ```
3. Run `make run-network` (and optionally `make studio`) to bring up the transports and UI.
4. Monitor Milvus connectivity with `curl http://localhost:8700/health` or the `SharedMemory.health_check()` helper.

Alternative Milvus deployments (cloud or existing clusters) just require updating `MILVUS_URI` and credentials.

### Offline / CI mode

- Unit suites stub external providers via `pytest.MonkeyPatch`, so `make test-fast` runs without real API keys or Milvus.
- Use `make quick-verify` or `python scripts/verify_multi_expert_dispatch.py` for deterministic routing checks.
- Keep `.env` values blank or dummy during CI; the tests rely on [`tests/conftest.py`](tests/conftest.py) to guard against environment leakage.

## Demos & Examples

- `run_demo.sh` — interactive bootstrap that validates Python, virtualenv, `.env`, and `config.yaml` before optionally launching the network.
- `demos/runner.py` and `demos/simple_demo.py` — orchestrated walkthroughs that exercise coordination and shared memory flows with mocked providers.
- `examples/coordination_agent_example.py` — minimal async script calling `CoordinationAgent.handle_message()`.
- `examples/shared_memory_usage.py` — programmatic reference for storing, searching, and inspecting Milvus-backed knowledge.
- `examples/openai_client_examples.py` — snippets showcasing chat and embedding usage through `OpenAIClientWrapper`.

Each script documents its prerequisites; prefer running them from an activated virtual environment.

## Troubleshooting

- **`agent_overrides` appear ignored** — Environment variables take precedence; unset conflicting `CHAT_API_*` / `EMBEDDING_API_*` entries and call `from utils.config_manager import reload_config; reload_config()` or restart the process.
- **Milvus connection failures** — Confirm `MILVUS_URI` points to a reachable endpoint and (for local development) Docker is running `make milvus-lite`. The troubleshooting table in [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) lists common error codes.
- **Unexpected network calls during tests** — Follow the fixtures in [tests/conftest.py](tests/conftest.py) and rely on `pytest.MonkeyPatch`; avoid `patch.dict` or loading `.env` files inline.
- **Rate limits or timeouts** — Adjust `CHAT_API_MAX_RETRIES`, `CHAT_API_MAX_RETRY_DELAY`, or switch providers using the configuration matrix above.

## Documentation Map

- [docs/README.md](docs/README.md) — navigation hub for all guides.
- [AGENTS.md](AGENTS.md) — detailed agent roles, escalation rules, and onboarding flow.
- [docs/testing/README.md](docs/testing/README.md) — pytest layout, Makefile helpers, and coverage workflow.
- [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) — extended diagnostics and resolutions.

Your feedback and contributions keep the multi-agent-brain evolving—thank you!
