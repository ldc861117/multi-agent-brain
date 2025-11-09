# multi-agent-brain

[![Python CI](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml/badge.svg)](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml)

A distributed multi-agent collaboration system built on **OpenAgents** and **Milvus** vector database, enabling intelligent agents to share knowledge and work together seamlessly.

## 🎯 Core Value Proposition

multi-agent-brain provides a robust framework for building sophisticated multi-agent systems with:

- **🤝 Multi-Agent Collaboration**: Distributed, non-centralized architecture where specialized agents work together
- **🧠 Shared Memory System**: Milvus-powered vector database for semantic knowledge sharing across agents
- **🔧 Flexible LLM Support**: Compatible with OpenAI, DeepSeek, Moonshot, Azure OpenAI, and other OpenAI-compatible APIs
- **🏗️ Modular Design**: Easy to extend with new agents and capabilities
- **⚡ Performance Optimized**: Built-in embedding caching and batch operations for efficiency

---

## 📊 Project Status

- ✅ **Task 1**: Bootstrap project layout - **COMPLETED**
- ✅ **Task 2**: OpenAI client implementation + Code Review - **COMPLETED**
- 🔄 **Task 3**: Milvus shared memory system - **IN PROGRESS**
- ⏳ **Task 4**: Create expert agents - **PENDING**
- ⏳ **Task 5**: Build demo runner - **PENDING**

## ✅ Continuous Integration

- **Workflow**: [Python CI](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml) runs on every push and pull request across Python 3.10 and 3.11.
- **Tests**: Installs pinned dependencies from `requirements.txt` and runs `pytest` with coverage enabled.
- **Coverage policy**: Uses `--cov-fail-under=60` to keep builds stable while allowing early iteration.
- **Artifacts**: Publishes `coverage.xml` and the generated `htmlcov/` report for each matrix entry.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│         OpenAgents HTTP Network (Port 8700)          │
│  ┌──────────────┬──────────────┬──────────────────┐ │
│  │ Coordinator  │ Python Expert│ Milvus Expert    │ │
│  │   Agent      │   Agent      │   Agent          │ │
│  │              │              │ + DevOps Expert  │ │
│  └──────────────┴──────────────┴──────────────────┘ │
└─────────────────────────────────────────────────────┘
         ↓ (queries/stores knowledge)
┌─────────────────────────────────────────────────────┐
│     Milvus Shared Memory + Embedding Cache          │
│  ┌────────────────────────────────────────────┐    │
│  │ • expert_knowledge (multi-tenant)          │    │
│  │ • collaboration_history                    │    │
│  │ • problem_solutions                        │    │
│  │ • LRU Cache for Embeddings (1000 entries)  │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         ↓ (embedding generation)
┌─────────────────────────────────────────────────────┐
│   OpenAI Client Wrapper (Custom Base URL Support)   │
│  • Chat Completions with Retry Logic               │
│  • Embedding Generation                             │
│  • Error Handling & Logging                        │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Create and activate conda environment
conda create -n multi-agent-brain python=3.11
conda activate multi-agent-brain
```

### 2. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys and configuration
nano .env  # or use your preferred editor
```

### 4. Start Milvus (Optional - for persistent storage)

**Option A - Using Milvus Lite (embedded, no Docker):**
```bash
# Milvus Lite will automatically start when you use file-based URI
# Just set MILVUS_URI=./milvus_data.db in your .env file
```

**Option B - Using Docker (for production):**
```bash
docker run --rm -it \
  -p 19530:19530 \
  -p 9091:9091 \
  -v "$(pwd)/.milvus:/var/lib/milvus" \
  milvusdb/milvus:v2.4.4-liteserve
```

### 5. Start the OpenAgents Network

```bash
# Start the HTTP network with agents
openagents network http --config config.yaml
```

### 6. Launch OpenAgents Studio (Optional)

```bash
# In a new terminal window
openagents studio --config config.yaml
```

Then open your browser to `http://localhost:8050` to interact with the agents.

### 7. Run the Demo

```bash
# In another terminal (when implemented)
python multi_agent_demo.py
```

---

## ⚙️ Configuration

The system is configured through environment variables in the `.env` file. See `.env.example` for all available options.

### Essential Configuration

| Variable | Description | Example Values |
|----------|-------------|----------------|
| `OPENAI_API_KEY` | API key for your LLM provider | `sk-...` |
| `OPENAI_BASE_URL` | API endpoint URL | See table below |
| `OPENAI_MODEL` | Model name to use | `gpt-4o`, `deepseek-chat` |
| `MILVUS_URI` | Milvus connection string | `./milvus_data.db` or `http://localhost:19530` |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `1536`, `3072` |

### Supported LLM Providers

| Provider | OPENAI_BASE_URL | Example Model |
|----------|-----------------|---------------|
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **Moonshot** | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **Azure OpenAI** | `https://your-resource.openai.azure.com/` | `gpt-4` |
| **Local/Custom** | `http://localhost:8000/v1` | Your custom model |

### Advanced Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_TIMEOUT` | Request timeout in seconds | `30` |
| `OPENAI_MAX_RETRIES` | Maximum retry attempts | `3` |
| `OPENAI_RETRY_DELAY` | Initial retry delay | `1.0` |
| `OPENAI_MAX_RETRY_DELAY` | Maximum retry delay | `60.0` |

### `config.yaml` Essentials

The OpenAgents network now requires a `network` section with explicit transports and workspace mods alongside the LLM `api_config`. A minimal template looks like this:

```yaml
network:
  name: "multi-agent-brain"
  transports:
    - type: "http"
      config:
        port: 8700
  mods:
    - name: "openagents.mods.workspace.default"
      enabled: true

api_config:
  chat_api:
    provider: "openai"
    model: "gpt-3.5-turbo"
  embedding_api:
    provider: "openai"
    model: "text-embedding-3-small"
    dimension: 1536
```

Additional keys (gRPC transport, workspace messaging, per-agent overrides, `prompts`) can be customised as needed. Use the bundled validator to confirm your configuration before starting the network:

```bash
python3 -m utils.config_validator --path config.yaml
python3 -m utils.config_validator --path config.yaml --repair  # Restore from config.default.yaml
AUTO_REPAIR_CONFIG=1 ./run_demo.sh           # Non-interactive repair via run_demo
```

`run_demo.sh` automatically invokes the validator and (with confirmation or `AUTO_REPAIR_CONFIG=1`) can repair missing sections by copying the default template without overwriting your config silently.

---

## 📁 Project Structure

```
multi-agent-brain/
├── agents/                      # Agent implementations
│   ├── __init__.py
│   ├── base.py                  # Base agent class
│   ├── shared_memory.py         # ✅ Milvus shared memory system
│   ├── general/                 # General conversation agent
│   ├── coordination/            # ⏳ Coordinator agent (pending)
│   ├── python_expert/           # ⏳ Python specialist (pending)
│   ├── milvus_expert/           # ⏳ Milvus specialist (pending)
│   └── devops_expert/           # ⏳ DevOps specialist (pending)
├── utils/                       # Utility modules
│   ├── __init__.py
│   ├── openai_client.py         # ✅ OpenAI client wrapper
│   └── test_openai_client.py    # ✅ Client unit tests (27 tests)
├── examples/                    # Usage examples
│   ├── openai_client_examples.py
│   └── shared_memory_usage.py
├── config.yaml                  # ✅ OpenAgents network configuration
├── requirements.txt             # ✅ Project dependencies
├── .env.example                 # ✅ Environment template
├── .gitignore                   # Git ignore rules
├── Makefile                     # Helper commands
├── README.md                    # This file
├── Codemap.md                   # Code architecture mapping
├── OPENAI_CLIENT_REVIEW.md      # Client code review
├── SHARED_MEMORY_IMPLEMENTATION.md  # Memory system docs
├── test_shared_memory.py        # 🔄 Memory unit tests (in progress)
└── multi_agent_demo.py          # ⏳ Main demo entry (pending)
```

---

## 💡 Core Features

### Feature 1: OpenAI Client Wrapper

A production-ready OpenAI client with support for custom endpoints, automatic retries, and comprehensive error handling.

```python
from utils import get_openai_client

# Automatically loads configuration from .env
client = get_openai_client()

# Chat completion with retry logic
response = client.get_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "How do I use Milvus with Python?"}
    ],
    temperature=0.7,
    max_tokens=500
)
print(response.choices[0].message.content)

# Generate embeddings (automatically cached)
embeddings = client.get_embedding("What is vector database?")
print(f"Embedding dimension: {len(embeddings)}")

# Batch embedding generation
texts = ["Question 1", "Question 2", "Question 3"]
all_embeddings = client.get_embeddings_batch(texts)
```

**Key Features:**
- ✅ Custom base URL support for any OpenAI-compatible API
- ✅ Exponential backoff retry with configurable delays
- ✅ Comprehensive error handling and logging
- ✅ Type-safe interfaces using Pydantic models
- ✅ Environment-based configuration with dotenv

**Test Coverage:** 27 unit tests with 100% pass rate

---

### Feature 2: Milvus Shared Memory System

A powerful vector-based knowledge sharing system with multi-tenant support and automatic caching.

```python
from agents.shared_memory import SharedMemory

# Initialize shared memory
memory = SharedMemory()

# Store knowledge with multi-tenant isolation
doc_id = memory.store_knowledge(
    collection="expert_knowledge",
    tenant_id="project_alpha",
    content={
        "expert_domain": "milvus",
        "question": "How to create a collection?",
        "answer": "Use Collection.create() with a schema definition...",
        "tags": ["milvus", "database", "collection"]
    }
)

# Semantic search with similarity threshold
results = memory.search_knowledge(
    collection="expert_knowledge",
    tenant_id="project_alpha",
    query="How do I create a Milvus collection?",
    top_k=5,
    threshold=0.7
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content']}")
    print("---")

# Batch operations for efficiency
contents = [
    {"domain": "python", "content": "..."},
    {"domain": "devops", "content": "..."},
    {"domain": "milvus", "content": "..."}
]
doc_ids = memory.batch_store_knowledge(
    collection="problem_solutions",
    tenant_id="project_alpha",
    contents=contents
)

# Health check and metrics
is_healthy = memory.health_check()
metrics = memory.get_metrics()
print(f"Cache hit ratio: {metrics.cache_hit_ratio:.2%}")
print(f"Avg search latency: {metrics.get_average_latency():.3f}ms")
```

**Key Features:**
- ✅ Three specialized collections: `expert_knowledge`, `collaboration_history`, `problem_solutions`
- ✅ Multi-tenant support with partition keys
- ✅ LRU embedding cache (1000 entries) to reduce API calls
- ✅ Automatic retry logic for transient failures
- ✅ Performance metrics tracking
- ✅ Both synchronous and asynchronous interfaces (async coming soon)

**Test Coverage:** Comprehensive unit tests with >80% coverage (in progress)

---

### Feature 3: Agent Collaboration (Coming Soon)

Agents work together through event-driven coordination:

```python
# Future implementation example:
# 
# 1. User asks a complex question
# 2. Coordinator Agent analyzes and breaks down the problem
# 3. Multiple Expert Agents work in parallel:
#    - Python Expert handles code-related questions
#    - Milvus Expert handles database queries
#    - DevOps Expert handles infrastructure concerns
# 4. All knowledge is stored in Shared Memory
# 5. Coordinator synthesizes results and responds
# 6. Future queries benefit from accumulated knowledge
```

---

## 🛠️ Development Guidelines

### Code Style

- **Naming Conventions:**
  - Classes: `PascalCase` (e.g., `SharedMemory`, `OpenAIClientWrapper`)
  - Functions/Methods: `snake_case` (e.g., `get_chat_completion`, `store_knowledge`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)

- **Documentation:**
  - All public methods must have docstrings
  - Use NumPy-style docstrings for consistency
  - Include parameter types and return value descriptions

- **Error Handling:**
  - Use custom exceptions for domain-specific errors
  - Always log errors with context using `loguru`
  - Provide actionable error messages

### Agent Development

All agents should:
1. Inherit from `WorkerAgent` base class
2. Use the shared `OpenAIClientWrapper` for LLM calls
3. Store important knowledge in `SharedMemory`
4. Use `loguru` for structured logging
5. Follow async patterns where appropriate

### Example Agent Pattern

```python
from agents.base import WorkerAgent
from agents.shared_memory import SharedMemory
from utils import get_openai_client

class MyExpertAgent(WorkerAgent):
    def __init__(self):
        super().__init__()
        self.memory = SharedMemory()
        self.client = get_openai_client()
    
    async def on_message(self, message):
        # 1. Search existing knowledge
        results = self.memory.search_knowledge(
            collection="expert_knowledge",
            tenant_id="default",
            query=message.content
        )
        
        # 2. Call LLM if needed
        response = self.client.get_chat_completion(
            messages=[{"role": "user", "content": message.content}]
        )
        
        # 3. Store new knowledge
        self.memory.store_knowledge(
            collection="expert_knowledge",
            tenant_id="default",
            content={"query": message.content, "answer": response}
        )
        
        return response
```

---

## 🧪 Testing

### Test Suite Status

| Component | Tests | Status | Coverage |
|-----------|-------|--------|----------|
| OpenAI Client | 27 | ✅ 100% Pass | High |
| Shared Memory | In Progress | 🔄 | >80% |
| Agent Integration | Pending | ⏳ | - |
| End-to-End | Pending | ⏳ | - |

### Running Tests

```bash
# Run OpenAI client tests
pytest tests/test_openai_client.py -v

# Run shared memory tests
pytest tests/test_shared_memory.py -v

# Run all tests
make test

# Run with coverage (coverage.xml + htmlcov/)
make cov
```

### Common Pitfalls

- Run tests from the project root so the consolidated `tests/` tree is picked up by `pytest`.
- Avoid exporting production API keys when running the suite; the shared `tests/conftest.py` fixture cleans known variables but custom keys may still leak into the environment.
- Always invoke coverage via `make cov` or `make cov-html` so both `coverage.xml` and `htmlcov/` are refreshed consistently.

### Test Examples

The `examples/` directory contains practical usage examples:

```bash
# Test OpenAI client functionality
python examples/openai_client_examples.py

# Test shared memory operations
python examples/shared_memory_usage.py
```

---

## 🎯 Future Roadmap

### Phase 3: Agent Implementation (In Progress)
- [ ] Implement Coordinator Agent for task orchestration
- [ ] Implement Python Expert Agent
- [ ] Implement Milvus Expert Agent
- [ ] Implement DevOps Expert Agent

### Phase 4: Demo and Integration
- [ ] Build comprehensive demo runner
- [ ] Add end-to-end integration tests
- [ ] Create interactive examples

### Phase 5: Optimization and Scale
- [ ] Add async support for all agents
- [ ] Implement performance benchmarking (QPS, latency)
- [ ] Optimize embedding cache strategies
- [ ] Add distributed tracing

### Phase 6: Production Ready
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] Monitoring and alerting setup
- [ ] Production deployment guide

---

## 📚 Reference Resources

- **[OpenAgents Documentation](https://github.com/microsoft/openagents)** - Multi-agent framework
- **[Milvus Vector Database](https://milvus.io/)** - High-performance vector database
- **[OpenAI API Reference](https://platform.openai.com/docs/api-reference)** - LLM API documentation
- **[Project Code Mapping](./Codemap.md)** - Detailed code architecture
- **[OpenAI Client Review](./OPENAI_CLIENT_REVIEW.md)** - Implementation review
- **[Shared Memory Docs](./SHARED_MEMORY_IMPLEMENTATION.md)** - Memory system details

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue: Milvus Connection Failed

```bash
# Error: Cannot connect to Milvus server
```

**Solutions:**
1. Check if Milvus is running (if using Docker):
   ```bash
   docker ps | grep milvus
   ```
2. Verify `MILVUS_URI` in `.env` matches your setup:
   - Local file: `./milvus_data.db`
   - Docker: `http://localhost:19530`
3. For Milvus Lite, ensure pymilvus is properly installed:
   ```bash
   pip install pymilvus
   ```

#### Issue: OpenAI API Timeout

```bash
# Error: Request timeout after 30 seconds
```

**Solutions:**
1. Increase timeout in `.env`:
   ```bash
   OPENAI_TIMEOUT=60
   ```
2. Check your network connection to the API endpoint
3. Verify `OPENAI_BASE_URL` is correct for your provider
4. For custom endpoints, ensure the server is running and accessible

#### Issue: Embedding Dimension Mismatch

```bash
# Error: Embedding dimension does not match collection schema
```

**Solutions:**
1. Verify your embedding model's dimension:
   - `text-embedding-3-small`: 1536
   - `text-embedding-3-large`: 3072
2. Update `EMBEDDING_DIMENSION` in `.env` to match
3. If changing models, you may need to recreate Milvus collections:
   ```python
   from agents.shared_memory import SharedMemory
   memory = SharedMemory()
   # Collections will be recreated with correct dimensions
   ```

#### Issue: Environment Variables Not Loading

```bash
# Error: OPENAI_API_KEY environment variable is required
```

**Solutions:**
1. Ensure `.env` file exists in the project root:
   ```bash
   ls -la .env
   ```
2. Copy from example if missing:
   ```bash
   cp .env.example .env
   ```
3. Check that `python-dotenv` is installed:
   ```bash
   pip install python-dotenv
   ```
4. Verify no syntax errors in `.env` file (no spaces around `=`)

#### Issue: Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'agents' or 'utils'
```

**Solutions:**
1. Ensure you're running from the project root directory
2. Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
3. Check your Python environment is activated:
   ```bash
   conda activate multi-agent-brain
   ```

#### Issue: OpenAgents Network Won't Start

```bash
# Error: Port 8700 already in use
```

**Solutions:**
1. Change the port in `config.yaml`:
   ```yaml
   network:
     settings:
       port: 8701
   ```
2. Or stop the process using port 8700:
   ```bash
   lsof -ti:8700 | xargs kill -9
   ```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Follow the existing code style and conventions
2. Add tests for new features
3. Update documentation as needed
4. Ensure all tests pass before submitting

---

## 📄 License

This project is part of a multi-agent scaffolding framework. Please refer to the LICENSE file for details.

---

## 🙋 Support

For questions, issues, or suggestions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review existing documentation in the `/docs` folder
3. Check the [Codemap.md](./Codemap.md) for architectural details
4. Open an issue on the project repository

---

**Built with ❤️ using OpenAgents and Milvus**
