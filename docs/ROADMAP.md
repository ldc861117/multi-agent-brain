# Roadmap · multi-agent-brain

> Forward-looking delivery plan that extends the existing multi-agent architecture with UI/UX capabilities while keeping today’s channels, configuration model, and memory integrations intact.

## Overview

- **Scope**: Documentation-only roadmap that sequences foundational hardening, UI/UX enablement, and productization of the OpenAgents-based network. All milestones respect current agent entrypoints, `ConfigManager` overrides, and Milvus-backed shared memory contracts.
- **Time Horizons**: Three incremental horizons (H1 → H3) that build upon each other without introducing breaking changes to the coordination or provider abstraction layers.
- **Planning Constructs**: Each milestone lists acceptance slices (thin, verifiable increments) and success metrics so the work can be tracked in future tickets.

## Horizon Breakdown

### H1 · Foundations (Stability & Developer ergonomics)

1. **Milestone: Stabilize agent orchestration (`CoordinationAgent`)**
   - **Intent**: Ensure the orchestrator reliably analyzes prompts, dispatches experts, and stores collaboration traces with repeatable offline validation.
   - **Acceptance slices**:
     1. Offline smoke harness in `scripts/` exercises analyze → retrieve → dispatch → synthesize path with mocked providers.
     2. `tests/unit` coverage for coordination, shared memory, and config utilities reaches ≥60% line coverage (captured via `pytest --cov`).
     3. Regression checklist codified in `docs/testing/README.md` to run before merging coordination-affecting changes.
   - **Success metrics**: Stable offline run (`make quick-verify`) without intermittent failures; coverage dashboard ≥60%; <5% of tickets reopened due to orchestration regressions.

2. **Milestone: Developer ergonomics**
   - **Intent**: Reduce onboarding friction by consolidating command entrypoints and finalizing testing documentation.
   - **Acceptance slices**:
     1. Curated Makefile targets (`make install`, `make test-fast`, `make run-network`, `make quick-verify`) documented with examples in `README` and `docs/README.md`.
     2. `scripts/` directory populated with linted utilities (e.g., `verify_multi_expert_dispatch.py`, `run_demo.sh`) referenced from docs with usage notes.
     3. `TESTING.md` (or equivalent section in `docs/testing/README.md`) finalized with environment isolation patterns (monkeypatch fixtures, dotenv guidance).
   - **Success metrics**: New contributors complete setup + first test run in <30 minutes; zero open documentation TODOs; positive sentiment in dev retro (#docs channel).

> **Exit Criteria for H1**: Coordination flows pass offline smoke tests, and the developer workflow is reproducible via documented commands.

### H2 · UI/UX Enablement (Operator visibility & interaction)

1. **Milestone: Minimal operator dashboard (CLI TUI or lightweight web UI)**
   - **Intent**: Provide live insight into agents, queued tasks, logs, and effective configuration without introducing new orchestration semantics.
   - **Acceptance slices**:
     1. Select delivery format (text-based TUI vs. minimal web app) based on contributor capacity and deployment constraints.
     2. Read-only view listing active agents, recent coordination requests, and per-agent overrides (`ConfigManager.get_agent_config`).
     3. Log pane wired to structured logs (see observability milestone) with filtering by correlation ID.
   - **Success metrics**: Operators can identify active agents and last 10 tasks in <3 clicks (or keystrokes); <200ms latency to refresh data snapshot on local stack.

2. **Milestone: Visual orchestration concept (LangGraph or equivalent)**
   - **Intent**: Illustrate plan → dispatch → synthesis graph while preserving companionship-first routing.
   - **Acceptance slices**:
     1. Evaluate LangGraph integration or alternative open-source graph visualiser; produce spike report documenting API compatibility.
     2. Prototype visual flow using existing `CoordinationAgent` events (no runtime mutations) surfaced in dashboard or standalone notebook.
     3. Document interoperability constraints and back-off plan (e.g., fallback to static sequence diagram) in `docs/ui-ux/`.
   - **Success metrics**: Visual prototype renders within 2 seconds for sample trace; stakeholder review sign-off recorded in issue tracker.

3. **Milestone: Observability baseline**
   - **Intent**: Surface latency, success rates, and correlation IDs through structured logging and a minimally maintained metrics page.
   - **Acceptance slices**:
     1. Adopt consistent structured logging schema (`logger.bind(correlation_id=...)`) across agents without altering business logic.
     2. Aggregate latency and success counters (e.g., in-memory or lightweight time-series store) exposed via dashboard panel or `/metrics` endpoint stub.
     3. Document alert thresholds and manual triage steps in `docs/guides/troubleshooting.md`.
   - **Success metrics**: 95th percentile coordination latency displayed; errors include correlation IDs; operators can trace a failing request end-to-end within 5 minutes.

> **Exit Criteria for H2**: Operators observe real-time agent activity and trace orchestrations visually without modifying dispatch mechanics.

### H3 · Productization (Extensibility & packaging)

1. **Milestone: Plugin/tooling gallery for experts**
   - **Intent**: Showcase and manage auxiliary tools available to specialist agents (e.g., Python execution, Milvus diagnostics) with hot-reloadable prompts/configs.
   - **Acceptance slices**:
     1. Define plugin manifest format (YAML/JSON) referencing runtime adapters already supported by agent scaffolds.
     2. Implement hot-reload mechanism (config reload or message-driven) that updates prompts/config without restart, guarded by existing tests.
     3. Provide dashboard/gallery section enumerating available tools, per-agent compatibility, and activation status.
   - **Success metrics**: Plugin add/remove cycle completes in <2 minutes without process restart; prompts reload without breaking ongoing sessions; documentation contains at least three curated tool examples.

2. **Milestone: Scenario-based demos with UI affordances**
   - **Intent**: Offer scripted walkthroughs (data retrieval, code analysis, DevOps triage) that highlight UI/UX flows and multi-agent collaboration.
   - **Acceptance slices**:
     1. Curate demo scenarios aligned with existing expert agents; map each scenario to required prompts and shared memory seeds.
     2. Integrate scenario launchers into dashboard/TUI with preflight checks (credentials, Milvus availability).
     3. Publish end-to-end guides in `docs/demos/` including expected outcomes and troubleshooting tips.
   - **Success metrics**: Each demo completes under 5 minutes on reference hardware; ≥80% participant satisfaction in user testing surveys.

3. **Milestone: Packaging & deployment guidance**
   - **Intent**: Lower effort to deploy the network with UI components in varied environments.
   - **Acceptance slices**:
     1. Produce packaging scripts or containers covering backend, UI, and supporting services (Milvus optional overlay).
     2. Document deployment topologies (local Docker, cloud, hybrid) referencing existing Makefile targets.
     3. Establish post-deployment validation checklist (health endpoints, UI smoke, configuration sanity) in `docs/deployment/`.
   - **Success metrics**: Deployment guide followed by two independent testers without blocking issues; automated smoke script exits successfully on new environment; rollback plan documented.

> **Exit Criteria for H3**: The project presents a cohesive, extensible product experience with documented deployment paths and showcase demos.

## Dependencies & Decision Points

| Topic | Decision Points | Notes |
| --- | --- | --- |
| **Vector store** | Continue with Milvus vs. evaluate lightweight alternatives (e.g., Chroma, PGVector) | Milvus integration is mature; evaluate alternatives only if footprint becomes a blocker. Decision slated for H2 observability review. |
| **LLM providers** | OpenAI-compatible SaaS vs. local providers (Ollama, vLLM) | `ConfigManager` already supports provider overrides. UI must expose current provider without hard-coding assumptions. Revisit before H2 dashboard milestone. |
| **UI technology** | Text-first TUI, lightweight web app (FastAPI + HTMX), or static telemetry viewer | Select in H2 dashboard slice. Preference for minimal web UI if dependency overhead remains low; otherwise start with TUI for quicker iteration. |
| **Metrics backend** | In-memory counters, Prometheus exporter, or SaaS APM | H2 observability slices begin with in-process metrics; upgrade path outlined in docs if Prometheus adoption is approved. |
| **Plugin distribution** | Local filesystem manifests vs. remote registry | Decide ahead of H3 plugin gallery; default to repository-managed manifests for simplicity. |

## Risks & Mitigations

| Risk | Horizon | Impact | Mitigation |
| --- | --- | --- | --- |
| UI scope creep delays stability work | H1/H2 | Slows delivery of foundational hardening | Enforce H1 exit criteria before UI tasks start; limit H2 initial dashboard to read-only features. |
| Provider rate limits blocking visual demos | H2/H3 | Demo readiness & UX fidelity | Expand mock/test harnesses; allow UI to switch to stub providers for demos. |
| Dependency surface of web UI introduces security/maintenance burden | H2/H3 | Operational overhead | Prefer lightweight frameworks (HTMX/FastAPI) and document patch cadence; consider CLI TUI fallback. |
| Hot-reload introduces configuration drift | H3 | Runtime instability | Gate reload actions behind explicit operator confirmation and emit audit logs. |
| Milvus availability in UI demos | H2/H3 | Demo reliability | Provide local alternatives (lite mode) and pre-seed fallback data in SharedMemory stubs. |

## Tracking & Next Steps

- Convert acceptance slices into individual issues per horizon, tagged with `h1-foundations`, `h2-uiux`, `h3-productization`.
- Reassess roadmap quarterly (or after major architecture changes) to ensure alignment with agent roster and provider support.
- UI/UX implementation work will be scheduled in follow-up tickets; this document serves as the authoritative reference for scope and sequencing.
