# multi-agent-brain

[![CI · Python & Docs](https://img.shields.io/github/actions/workflow/status/ldc861117/multi-agent-brain/python-ci.yml?branch=main&label=CI%20%C2%B7%20Python%20%26%20Docs&logo=github)](https://github.com/ldc861117/multi-agent-brain/actions/workflows/python-ci.yml)

> 多智能体协作平台，基于 **OpenAgents** 网络与 **Milvus** 向量数据库，支持自定义 LLM 提供商与多租户共享记忆。
> *English summary: A multi-agent collaboration system powered by OpenAgents, Milvus vector search, and a provider-agnostic OpenAI-compatible client.*

---

## 🌟 项目简介 (Project Overview)

- 🤝 **多智能体协作**：`CoordinationAgent` 调度 Python / Milvus / DevOps 专家，整合答案并沉淀知识。
- 🧠 **Milvus 共享记忆**：统一的向量检索层，支持批量写入、缓存命中追踪和多租户隔离。
- 🔧 **灵活的 LLM 提供商**：通过 `CHAT_API_*` / `EMBEDDING_API_*` 与 `config.yaml` 的 `agent_overrides`，可以自由切换 OpenAI、DeepSeek、Moonshot、Ollama 等后端。
- 🧩 **可扩展架构**：遵循 `BaseAgent` 接口即可快速接入新的专家 Agent；所有配置由 `ConfigManager` 管理。

---

## 🚀 快速开始 (Quick Start)

> *English summary: Create a virtualenv, install dependencies, configure .env, prepare Milvus, launch the OpenAgents network, and run tests via Makefile.*

1. **准备 Python 3.11+**
   ```bash
   python3 --version  # 确保返回 3.11 或更高
   ```
2. **创建虚拟环境并安装依赖**（或使用 `make install` 自动完成）
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 使用喜欢的编辑器填入 CHAT_API_KEY / EMBEDDING_API_KEY / MILVUS_URI 等
   ```
4. **准备 Milvus（任选其一）**
   - Docker：`make milvus-lite`
   - Milvus Cloud：在 `.env` 中设置 HTTPS URI
   - 本地服务：确保 `MILVUS_URI` 指向 `http://host:19530`
5. **启动 OpenAgents 网络（HTTP + gRPC）**
   ```bash
   make run-network   # 等价于 openagents network http --config config.yaml
   ```
6. **（可选）启动 Studio UI**
   ```bash
   make studio
   ```
7. **验证网络与健康状况**
   ```bash
   curl http://localhost:8700/health
   ```

---

## ⚙️ 配置优先级 (Configuration Precedence)

> *English summary: Config defaults originate from `config.yaml`, environment variables override them, and legacy `OPENAI_*` keys provide backward compatibility.*

| 优先级（高 → 低） | 来源 | 说明 |
|-------------------|------|------|
| 1 | `config.yaml` → `api_config` & `agent_overrides` | 提供默认 provider、模型、维度、`answer_verbose` 等。|
| 2 | `.env` / 系统环境 (`CHAT_API_*`, `EMBEDDING_API_*`) | 如设置同名变量，将覆盖 YAML 值；常用于临时切换模型或端点。|
| 3 | 兼容性变量 (`OPENAI_*`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`) | 仍被 `OpenAIConfig.from_env_with_fallback()` 识别，为旧脚本提供兜底。|

**行为提示**
- `ConfigManager` 会优先读取环境变量；若想强制使用 YAML 中的覆盖值，请移除相关环境变量并调用 `from utils import reload_config; reload_config()`。
- `agent_overrides.<agent>.answer_verbose` 控制是否生成长答案，默认 `false`。
- 嵌入模型维度可在 overrides 中单独配置（示例：`coordination` 使用 768 维 `qwen3-embedding:0.6b`）。

---

## 🔧 运行与测试命令 (Run & Test Commands)

| 命令 | 作用 | 说明 |
|------|------|------|
| `make install` | 创建 `.venv` 并安装依赖 | 推荐的首次操作 |
| `make run-network` | 启动 OpenAgents HTTP 网络 | 使用 `config.yaml` 中 transports 设置 |
| `make studio` | 启动 OpenAgents Studio UI | 便于可视化调试 |
| `make milvus-lite` | 启动 Milvus Docker 容器 | 适合本地开发 |
| `make test` | 调用 `scripts/run_tests.sh` 运行完整 pytest | 自动设置 `PYTHONPATH=.` |
| `make test-fast` | 过滤 slow / integration 标记 | 调用 `scripts/run_tests.sh -q -m "not slow and not integration"` |
| `make lint` | 调用 `scripts/lint.sh` 运行可用的静态检查 | 无可用工具时回退到 `python -m compileall` |
| `make format` | 调用 `scripts/format.sh` 执行格式化 | 优先使用 `ruff format`，备用 `black` |
| `make cov` | 生成覆盖率报告 (`coverage.xml`, `htmlcov/`) | 依赖 `scripts/run_tests.sh --cov ...` |
| `make cov-html` | 仅刷新 HTML 覆盖率 | 依赖 `make cov` |
| `make verify-tests` | 运行 `scripts/quick_verify.py` 输出布局概览 | 使用 `--run` 可触发 pytest |
| `make quick-verify` | 执行 `scripts/quick_verify.py --run` 快速验证核心单测 | 覆盖配置与 OpenAI 客户端路径 |
| `make ci` | 顺序运行 lint + 覆盖率测试 | 相当于 `scripts/lint.sh` + `scripts/run_tests.sh --cov ...` |

> 所有命令默认使用 `.venv`，若已有虚拟环境可直接运行 `pytest` / `openagents` 等。

---

## 🧠 架构概览 (Architecture Overview)

```text
┌────────────────────────────────────────────────────┐
│                OpenAgents Network (HTTP+gRPC)      │
│  ┌───────────────┬───────────────┬──────────────┐ │
│  │ Coordination  │ Python Expert │ Milvus Expert │ │
│  │    Agent      │    Agent      │    Agent      │ │
│  │               └───────────────┴──────────────┘ │
│  │            DevOps Expert + General Agent       │
└──┴─────────────────────────────────────────────────┘
           │ 共享知识 (向量检索 + 缓存)
           ▼
┌────────────────────────────────────────────────────┐
│     SharedMemory (Milvus + Embedding Cache)        │
│  • expert_knowledge  • collaboration_history       │
│  • problem_solutions • metrics & cache hit ratio   │
└────────────────────────────────────────────────────┘
           │ LLM 调用 (Chat + Embedding)
           ▼
┌────────────────────────────────────────────────────┐
│       OpenAIClientWrapper (Provider-agnostic)      │
│  • Separate chat/embedding configs                 │
│  • Exponential backoff retry                       │
│  • ProviderType: openai / ollama / custom          │
└────────────────────────────────────────────────────┘
```

---

## 🛠️ 核心组件 (Key Components)

| 位置 | 说明 | 亮点 |
|------|------|------|
| `agents/coordination/agent.py` | 协调中心：解析问题、检索历史数据、调度专家、汇总结果并存档 | 支持并发、可配置 `SUPPORTED_EXPERTS`、记录详细日志 |
| `agents/shared_memory.py` | Milvus backed knowledge store | 多租户集合、批量 CRUD、`EmbeddingCache` 与指标追踪 |
| `utils/config_manager.py` | 合并 `config.yaml` + 环境变量 + overrides | 缓存每个 Agent 的 `OpenAIConfig`，提供 `get_agent_answer_verbose` |
| `utils/openai_client.py` | Chat/Embedding 客户端封装 | provider 无关、指数退避、批量 embedding、fallback 策略 |
| `tests/unit/test_env_config.py` | 配置加载单测 | 通过 monkeypatch 确保环境隔离，覆盖所有优先级场景 |

---

## 📦 LLM Provider 设置速查 (Provider Setup Cheatsheet)

```ini
# OpenAI
CHAT_API_KEY=sk-xxxx
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_MODEL=gpt-4o-mini

# DeepSeek
CHAT_API_KEY=deepseek-xxx
CHAT_API_BASE_URL=https://api.deepseek.com/v1
CHAT_API_MODEL=deepseek-chat
CHAT_API_PROVIDER=custom

# Moonshot
CHAT_API_KEY=moonshot-xxx
CHAT_API_BASE_URL=https://api.moonshot.cn/v1
CHAT_API_MODEL=moonshot-v1-8k

# 本地 Ollama Embedding (示例)
EMBEDDING_API_KEY=ollama
EMBEDDING_API_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_MODEL=qwen3-embedding:0.6b
EMBEDDING_API_PROVIDER=ollama
EMBEDDING_DIMENSION=768
```

> 需要覆盖某个 Agent：在 `config.yaml` 添加 `api_config.agent_overrides.<agent>.chat_model` / `embedding_model`。

---

## 🧰 故障排查 (Troubleshooting)

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| `Milvus connection refused` | Milvus 未启动或 URI 错误 | 确认容器/服务运行；在 `.env` 中使用 `http://localhost:19530` 或云端 HTTPS URI；可用 `make milvus-lite` 启动本地实例。 |
| `embedding dimension mismatch (expected 768, got 1536)` | 模型维度与配置不符 | 在 `config.yaml` 的 `agent_overrides` 或 `.env` 中同步更新 `EMBEDDING_DIMENSION`。 |
| `OpenAIError: Rate limit` | Provider 限流 | 调整 `CHAT_API_MAX_RETRIES` / `CHAT_API_MAX_RETRY_DELAY`，或切换到备用 API Key。 |
| `agent_overrides` 未生效 | 同名环境变量仍存在 | 清除 `.env` 中相关变量，运行<br>`python - <<'PY'`<br>`from utils import reload_config`<br>`reload_config()`<br>`PY` 重载配置。 |
| Studio 无法连接 | Network transport 未启动或端口冲突 | 确认 `make run-network` 正常运行且 8700/8050 端口未被占用。 |

> 日志默认输出到 stdout，格式由 `config.yaml` 中 `logging` 段定义（`loguru`）。

---

## 📚 文档导航 (Documentation Hub)

| 文档 | 作用 | 链接 |
|------|------|------|
| `AGENTS.md` | 机器可读 Agent 开发指南（中文主） | [查看](AGENTS.md) |
| `Codemap.md` | 代码结构与配置数据流地图 | [查看](Codemap.md) |
| `OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md` | OpenAI 客户端测试重写记录 | [查看](OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md) |
| `SHARED_MEMORY_IMPLEMENTATION.md` | SharedMemory 设计与实现细节 | [查看](SHARED_MEMORY_IMPLEMENTATION.md) |

---

## 📈 CI 与质量保障 (CI & QA)

- GitHub Actions Workflow：`python-ci.yml` 覆盖 Python 3.10/3.11，执行 `pip install -r requirements.txt`、`pytest --cov`。
- 重要 Artefacts：`coverage.xml`、`htmlcov/`（可在 Actions 页面下载）。
- 推荐在本地执行 `make test-fast` 获取快速反馈，合入前运行 `make cov` 确保覆盖率与静态检查通过。
- 若配置有改动，请使用 `python -m utils.config_validator --path config.yaml` 验证并根据提示修复差异。

---

> 欢迎提交 Issue / PR，与我们一起完善多智能体协作体验！
