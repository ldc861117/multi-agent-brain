# Codemap.md - multi-agent-brain 代码地图 / Code Map

> 聚焦于目录结构、核心模块以及配置数据流，帮助贡献者与 AI Agents 快速定位代码入口。
> *English summary: High-resolution map of the multi-agent-brain repository covering layout, key modules, config flow, and test surfaces.*

---

## 0. 导航速览 / Navigation

| 主题 | 内容 | 跳转 |
|------|------|------|
| 目录鸟瞰 | 顶层与关键子目录 | [§1](#1-目录鸟瞰-directory-overview) |
| 核心模块 | config_manager / coordination / shared_memory / tests | [§2](#2-核心模块关键模块-key-modules) |
| 配置数据流 | config.yaml → 环境 → OpenAIClient → Agents | [§3](#3-配置数据流-configuration-data-flow) |
| 消息处理路径 | 用户问题 → 协调 → 专家 → Memory | [§4](#4-消息处理路径-runtime-message-flow) |
| 测试矩阵 | 单测与集成测试覆盖范围 | [§5](#5-测试矩阵-testing-matrix) |
| 文档 & 脚本 | 重要文档、辅助脚本 | [§6](#6-文档--脚本-docs--scripts) |

---

## 1. 目录鸟瞰 (Directory Overview)

```text
multi-agent-brain/
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent & AgentResponse
│   ├── coordination/              # CoordinationAgent orchestrator
│   ├── general/                   # Default user-facing agent
│   ├── python_expert/             # Python scaffold
│   ├── milvus_expert/             # Milvus scaffold
│   ├── devops_expert/             # DevOps scaffold
│   └── shared_memory.py           # Milvus-backed knowledge store
├── utils/
│   ├── __init__.py                # Public utilities exports
│   ├── config_manager.py          # YAML + env + overrides loader
│   ├── config_validator.py        # Schema validation & CLI
│   └── openai_client.py           # LLM client abstraction
├── tests/
│   ├── conftest.py                # Pytest fixtures (env isolation, markers)
│   ├── fixtures/                  # Shared pytest fixtures
│   ├── unit/                      # Unit suites (config, OpenAI, shared memory)
│   │   ├── test_config_validator.py
│   │   ├── test_env_config.py
│   │   ├── test_imports_smoke.py
│   │   ├── test_openai_client.py
│   │   ├── test_shared_memory.py
│   │   ├── test_shared_memory_minimal.py
│   │   └── test_utils_coverage_boost.py
│   ├── integration/
│   │   ├── test_demo_cli_smoke.py
│   │   └── test_lm.py
│   └── e2e/                       # Placeholder for future end-to-end tests
├── config.yaml                    # Production-ready network config
├── config.default.yaml            # Template for validator repair
├── requirements.txt               # Dependency lock
├── Makefile                       # install/test/coverage helpers
├── README.md                      # 人类友好 & 英文摘要
├── AGENTS.md                      # 机器可读 Agent 手册
└── Codemap.md                     # 当前文档
```

---

## 2. 核心模块关键模块 (Key Modules)

| 模块 | 主要类型 / 方法 | 作用（中文） | Key Notes (EN) | 相关测试 |
|------|------------------|--------------|----------------|----------|
| `utils/config_manager.py` | `ConfigManager`, `get_agent_config`, `get_agent_answer_verbose` | 统一加载 `config.yaml` + 环境变量 + agent overrides，提供每个 Agent 的模型/维度配置。 | Caches per-agent OpenAIConfig instances and exposes verbose flag. | `tests/unit/test_env_config.py` `TestPerAgentOverrides` |
| `utils/openai_client.py` | `OpenAIClientWrapper`, `OpenAIConfig`, `ChatAPIConfig`, `EmbeddingAPIConfig` | 封装 Chat & Embedding API，支持自定义 provider、指数退避、批量 Embedding。 | Shared by all agents; embedding falls back to chat when unset. | `tests/unit/test_openai_client.py` |
| `agents/coordination/agent.py` | `CoordinationAgent`, `analyze_question`, `dispatch_to_experts`, `synthesize_answer`, `store_collaboration` | 核心编排器：解析任务、检索 SharedMemory、并发调度专家、生成最终回复并记录协作。 | Async orchestration with heuristics + config-driven verbose mode. | `examples/coordination_agent_example.py` (usage) |
| `agents/shared_memory.py` | `SharedMemory`, `EmbeddingCache`, `Metrics` | Milvus 向量存储封装：多租户集合、批量读写、缓存指标。 | Provides sync API, optional async version, integrates LLM embedding. | `tests/unit/test_shared_memory.py` `tests/unit/test_shared_memory_minimal.py` |
| `agents/base.py` | `BaseAgent`, `AgentResponse` | 定义所有 Agent 必须遵循的接口与响应封装。 | Supplies metadata, async `handle_message` contract. | 被所有 Agent 测试间接覆盖 |
| `tests/unit/test_env_config.py` | Pytest classes `TestEnvironmentVariableLoading` 等 | 验证 `.env`、`CHAT_API_*`、`EMBEDDING_API_*`、`agent_overrides` 行为。 | Monkeys environment to avoid leakage, checks precedence. | - |
| `tests/unit/test_config_validator.py` | `ConfigValidator` 集成测试 | 确保 `config.yaml` 与模板一致或可自动修复。 | CLI style checks & diff logging. | - |

---

## 3. 配置数据流 (Configuration Data Flow)

> *English summary: How configuration travels from YAML and environment variables into running agents.*

```text
config.yaml (api_config & agent_overrides)
        │
        ▼
utils.config_manager.ConfigManager
  ├─ get_global_config()   ← 读取环境变量 `.env` (CHAT_API_*, EMBEDDING_API_*)
  ├─ get_agent_config(name)
  │    └─ 合并 agent_overrides.<name>
  └─ get_agent_answer_verbose(name)
        │
        ▼
utils.openai_client.OpenAIClientWrapper(config)
        │
        ▼
agents.<*>.handle_message()  // 使用统一客户端和 SharedMemory
```

**优先级（逻辑顺序）**
1. `config.yaml` 提供默认值 + agent 覆盖。
2. `.env` / 系统环境覆盖相同字段（若存在 `CHAT_API_*`, `EMBEDDING_API_*`）。
3. 兼容性变量 `OPENAI_*`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION` 兜底。

> 若发现 YAML 修改未生效，请删除对应环境变量并调用 `utils.reload_config()`。

---

## 4. 消息处理路径 (Runtime Message Flow)

1. **入口**：
   - 用户消息通过 `general` or `coordination` channel 进入。
   - `GeneralAgent` 直接回覆或转交 `CoordinationAgent`。
2. **协调**：`CoordinationAgent.handle_message()`
   - `analyze_question()` 依据关键词、上下文 & `agent_overrides` 的 verbose 设置确定目标专家。
   - `retrieve_similar_knowledge()` 调用 `SharedMemory.search_knowledge()` 获取上下文。
   - `dispatch_to_experts()` 并发调用专家的 `handle_message()`。
3. **专家执行**：各专家使用 `OpenAIClientWrapper` 和 `SharedMemory`（模板阶段返回占位回应）。
4. **汇总与存储**：
   - `synthesize_answer()` 合成最终答复。
   - `store_collaboration()` 写入 `collaboration_history`，包含参与者、内容摘要、时间戳。
5. **响应**：返回 `AgentResponse(content, metadata)` 给调用方。

---

## 5. 测试矩阵 (Testing Matrix)

| 测试文件 | 覆盖范围 | 关键夹具 / 技术点 |
|----------|----------|------------------|
| `tests/unit/test_env_config.py` | `.env` & `config.yaml` 解析、provider 支持、agent overrides、fallback 行为 | `clean_env` (monkeypatch), `mock_load_dotenv`, 临时 YAML 文件 |
| `tests/unit/test_openai_client.py` | Chat/Embedding 客户端初始化、重试机制、provider 兼容性、错误处理 | `openai_client_instance`, `monkeypatch` for OpenAI SDK |
| `tests/unit/test_shared_memory.py` + `tests/unit/test_shared_memory_minimal.py` | SharedMemory 集合初始化、批量操作、缓存命中率、Milvus mock | `FakeMilvus`, `memory_factory` |
| `tests/unit/test_config_validator.py` | `ConfigValidator` CLI 行为、缺失键修复、差异输出 | `tmp_path_factory`, `monkeypatch` CLI args |
| `tests/integration/test_demo_cli_smoke.py` | Demo CLI import & guard smoke | `pytest.mark.smoke`, `monkeypatch` asyncio.run |
| `tests/integration/test_lm.py` | 语言模型辅助函数 & 基础工具 | 需要真实/模拟 API Key，默认 skip |

> 执行方式：`make test`（完整），`make test-fast`（排除 slow/integration），`make cov`（带覆盖率报告）。

---

## 6. 文档 & 脚本 (Docs & Scripts)

| 资源 | 描述 | 用法 |
|------|------|------|
| `README.md` | 项目总览、Quickstart、配置优先级、Troubleshooting | 面向人类 + 英文补充 |
| `AGENTS.md` | AI Agent 作业手册（中文主、英文辅） | 自动化 Agent 读取、任务映射 |
| `Codemap.md` | **当前文档**，结构 & 数据流 | 代码定位与审查参考 |
| `examples/openai_client_examples.py` | OpenAIClient 基础示例 | `python examples/openai_client_examples.py` |
| `examples/shared_memory_usage.py` | SharedMemory CRUD + 检索示例 | `python examples/shared_memory_usage.py` |
| `Makefile` | 快捷命令：`make install`、`make run-network`、测试/覆盖率封装 | 推荐统一入口 |
| `scripts/quick_verify.py` | 快速校验测试文件存在性/命名 | `python scripts/quick_verify.py --run` |
| `scripts/run_tests.sh` | Pytest 运行封装（环境变量、默认参数） | `./scripts/run_tests.sh -q` |
| `scripts/lint.sh` / `scripts/format.sh` | Lint / Format 工具统一入口 | `make lint`、`make format` |

> 如需更多上下文，可对照 `DOCUMENTATION_INDEX.md` 与 `OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md` 获取历史变更记录。
