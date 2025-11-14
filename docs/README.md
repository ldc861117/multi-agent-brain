# Documentation Hub

> Consolidated reference for the multi-agent-brain repository. Use this page to find the right guide for onboarding, configuration, testing, and architecture deep dives.

## How to Navigate

### Getting Started
- [Quickstart](getting-started/quickstart.md): Set up prerequisites, bootstrap the environment, and launch the OpenAgents network.

### Configuration
- [Configuration Guide](configuration/guide.md): Understand configuration precedence, environment variables, agent overrides, and provider-specific notes.

### Testing & Quality
- [Testing Reference](testing/README.md): Explore the pytest layout, Makefile helpers, coverage workflow, and common pitfalls.

### Architecture
- [Architecture Overview](architecture/overview.md): High-level diagram and component responsibilities.
- [Code Map](architecture/codemap.md): Detailed directory guide and runtime data flow.
- [Shared Memory Deep Dive](architecture/shared-memory.md): Internal design of the Milvus-backed knowledge store.

### Guides
- [Agent Interaction Patterns](guides/interaction.md): How to compose messages and orchestrate agents.
- [Quick Reference](guides/quick-reference.md): Snippets and command cheatsheets for daily work.
- [Troubleshooting](guides/troubleshooting.md): Diagnose common issues across the LLM client, Milvus, and agent coordination layers.

### Design Documents
- [Browser Tool Design](design/browser_tool.md): Web search and navigation capabilities for agents (Tavily/DuckDuckGo, Playwright, explicit memory persistence).

### Decisions & History
- [Architecture Decision Records](adr/README.md): Active decisions. Historical context lives in dated ADRs.
- [Archive](archive/README.md): Deprecated or legacy documents retained for reference.

## Related Resources

- [Root README](../README.md) · project overview and quick links.
- [AGENTS manual](../AGENTS.md) · machine-readable onboarding for agent implementations.
- [Makefile](../Makefile) · curated developer workflows referenced throughout the docs.
