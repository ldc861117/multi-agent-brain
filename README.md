# Multi-Agent Memory Scaffold

This repository bootstraps the project layout for a multi-channel agentic
workflow built on top of [OpenAgents](https://github.com/microsoft/openagents).
It establishes the directories, configuration files, and environment guidance
needed to bring a team of specialised agents online and connect them to a
Milvus-powered vector memory.

---

## Contents

- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [.env configuration](#env-configuration)
- [Custom OpenAI-compatible endpoints](#custom-openai-compatible-endpoints)
- [Running Milvus Lite](#running-milvus-lite)
- [Starting the OpenAgents network](#starting-the-openagents-network)
- [Launching the demo & Studio](#launching-the-demo--studio)
- [Helper commands](#helper-commands)
- [Next steps](#next-steps)

---

## Repository Layout

```text
.
├── agents/
│   ├── __init__.py
│   ├── base.py
│   ├── coordination/
│   ├── devops_expert/
│   ├── general/
│   ├── milvus_expert/
│   └── python_expert/
├── config.yaml
├── requirements.txt
├── utils/
│   └── __init__.py
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

Each agent sub-package exposes a lightweight placeholder class so the network
can be wired up before domain logic is implemented. The `config.yaml` file
contains the HTTP network definition that OpenAgents uses to start the routing
layer and connect each channel with its corresponding agent.

---

## Prerequisites

- **Python**: 3.10 or newer is recommended
- **Pip / virtualenv**: any modern Python environment manager (`venv`,
  `virtualenv`, `uv`, or `conda`)
- **Docker** *(optional but recommended)*: simplifies running Milvus Lite for
  local experimentation

If you plan to use OpenAgents Studio in the browser, ensure the machine can
access the configured OpenAI-compatible endpoint.

---

## Environment Setup

1. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Replace with your preferred environment tooling if needed (`uv venv`,
   `conda`, etc.).

2. **Install the Python dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Configure environment variables** by copying the sample file:

   ```bash
   cp .env.example .env
   ```

   Update the copied `.env` with the credentials and model selections that suit
   your deployment.

---

## .env configuration

The `.env.example` file documents the variables consumed by the scaffold.
Update the copy you made in the previous section with real values:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | API key for OpenAI or an OpenAI-compatible provider. |
| `OPENAI_BASE_URL` | Base URL for the completions/chat API. Defaults to the public OpenAI endpoint. |
| `OPENAI_MODEL` | Chat model identifier (e.g. `gpt-4o-mini`, `azure/gpt-4`). |
| `MILVUS_URI` | Connection string pointing to Milvus Lite or a remote Milvus cluster. |
| `EMBEDDING_MODEL` | Embedding model name (e.g. `text-embedding-3-large`). |
| `EMBEDDING_DIMENSION` | Dimension that matches the embedding model output. |
| `OPENAI_PROJECT_ID`, `OPENAI_TENANT_ID` | Optional tenant metadata for multi-tenant deployments. |

The `python-dotenv` dependency will be used later to load these variables in
local development scripts.

---

## Custom OpenAI-compatible endpoints

To point the agents toward a non-OpenAI provider (such as Azure OpenAI,
Mistral, Together AI, or a self-hosted LLM gateway), update the following
values in your `.env` file:

- `OPENAI_BASE_URL`: set to the provider's REST endpoint
- `OPENAI_MODEL`: set to the provider-specific deployment or model name
- `OPENAI_API_KEY`: set to the provider's API key or bearer token

OpenAgents relies on the official `openai` Python client which supports custom
`base_url` and `api_key` values out of the box. Any additional headers required
by the provider can be injected later through utility modules inside `utils/`.

---

## Running Milvus Lite

For prototyping, Milvus Lite can run entirely in-process without additional
infrastructure.

### Option A – Docker container

```bash
docker run --rm -it \
  -p 19530:19530 \
  -p 9091:9091 \
  -v "$(pwd)/.milvus:/var/lib/milvus" \
  milvusdb/milvus:v2.4.4-liteserve
```

### Option B – Milvus Lite inside Python (no Docker)

```bash
pip install milvus-lite
python -m milvus_lite --uri ${MILVUS_URI:-"milvus://:@localhost/multi_agent_memory.db"}
```

Update `MILVUS_URI` in your `.env` if you expose Milvus on a different host or
port.

---

## Starting the OpenAgents network

With dependencies installed and Milvus running, launch the HTTP network using
`config.yaml`:

```bash
openagents network http --config config.yaml
```

The command binds to `0.0.0.0:8700` by default. Adjust the port in
`config.yaml` if the default conflicts with existing services.

The `channels` section of the configuration file already maps:

- **general** → `GeneralAgent`
- **coordination** → `CoordinationAgent`
- **python_expert** → `PythonExpertAgent`
- **milvus_expert** → `MilvusExpertAgent`
- **devops_expert** → `DevOpsExpertAgent`

Handoff routes are pre-defined so that the general channel escalates to the
coordination channel, which can then enlist the specialist agents.

---

## Launching the demo & Studio

OpenAgents ships with a lightweight Studio UI which communicates with the
HTTP network defined above.

```bash
openagents studio --config config.yaml
```

Once the Studio server is running, open the provided URL in your browser. Use
the general channel to initiate a conversation and observe how requests can be
handed off between the specialised agents.

If you prefer to script interactions, the `openagents` CLI also exposes
`openagents chat --channel general --config config.yaml`.

---

## Helper commands

A `Makefile` is included to streamline routine tasks:

- `make install` – create a virtual environment (if missing) and install deps
- `make run-network` – start the OpenAgents HTTP network with `config.yaml`
- `make studio` – launch OpenAgents Studio wired to the same configuration
- `make milvus-lite` – run Milvus Lite via Docker with a persisted volume
- `make clean` – remove the local virtual environment and Milvus cache

Feel free to expand the Makefile with additional workflows as the project
matures.

---

## Next steps

- Replace the placeholder agent implementations with real OpenAgents
  integrations (tools, memories, planning APIs, etc.)
- Script migrations that initialise Milvus collections aligned with the
  embedding model you choose
- Add tests covering agent routing logic once the behaviours are implemented

This scaffold provides the foundation for collaborative agent development.
Iterate on the agents, utilities, and configuration to tailor the network to
your product vision.
