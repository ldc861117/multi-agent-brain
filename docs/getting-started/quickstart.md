# Quickstart Guide

> Spin up the multi-agent-brain environment, configure providers, and launch the OpenAgents network in minutes.

## 1. Prerequisites

- **Python 3.11+** – verify with `python3 --version`.
- **Virtual environment tooling** – either the built-in `venv` module or a preferred alternative.
- **Docker (optional)** – required only when running the Milvus Lite container.

## 2. Bootstrap the Workspace

```bash
# Clone and enter the repository
# git clone https://github.com/<org>/multi-agent-brain.git
cd multi-agent-brain

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

Or run the automated Makefile helper:

```bash
make install
```

## 3. Configure Environment Variables

```bash
cp .env.example .env
# Populate CHAT_API_KEY / CHAT_API_BASE_URL
# Populate EMBEDDING_API_KEY / EMBEDDING_API_BASE_URL (optional fallback to chat API)
# Set MILVUS_URI (e.g. http://localhost:19530)
```

Refer to the [Configuration Guide](../configuration/guide.md) for precedence rules, provider-specific options, and agent overrides.

## 4. Provision Milvus

Choose one of the supported setups:

| Option | Command | Notes |
|--------|---------|-------|
| Milvus Lite (Docker) | `make milvus-lite` | Launches a lightweight standalone container. |
| Milvus Cloud | – | Set `MILVUS_URI` to the HTTPS endpoint provided by Milvus Cloud. |
| Existing Deployment | – | Ensure the URI is reachable and credentials (if any) are included in the `.env`. |

## 5. Launch the OpenAgents Network

```bash
make run-network        # Starts HTTP and gRPC transports
```

Optional extras:

```bash
make studio             # Launch OpenAgents Studio UI
curl http://localhost:8700/health
```

Stop the processes with `Ctrl+C` or your process manager of choice.

## 6. Validate the Setup

```bash
make test-fast          # Unit tests only
make quick-verify       # Lightweight smoke verification script
```

Run the full matrix with `make test` once you are ready for a complete validation. Additional commands live in [Testing Reference](../testing/README.md).

## 7. Next Steps

- Explore per-agent configuration: [Configuration Guide](../configuration/guide.md)
- Understand the architecture: [Architecture Overview](../architecture/overview.md)
- Interact with the agent network: [Agent Interaction Patterns](../guides/interaction.md)
- Diagnose issues: [Troubleshooting](../guides/troubleshooting.md)
