# AGENTS.md - AI Coding Agent Developer Guide

> 专为 AI Coding Agents 设计的结构化作战手册，帮助它们在 **multi-agent-brain** 项目中快速定位职责与接口。
> *English summary: Machine-readable playbook for autonomous coding agents working inside the multi-agent-brain repository.*
>
> 📚 Documentation hub: [docs/README.md](docs/README.md) · configuration, testing, and troubleshooting guides are referenced here rather than duplicated.

---

## 0. 快速索引 / Quick Index

| 主题 | 摘要 | 跳转 |
|------|------|------|
| 当前 Agent 阵列 | 频道、入口、职责一览 | [§1](#1-当前-agent-总览-current-agent-line-up) |
| 能力矩阵 | 各 Agent 能力与协作分工 | [§2](#2-能力矩阵-capability-matrix) |
| 协作调用流 | 接收消息 → 协调 → 专家 → 汇总 | [§3](#3-协作调用流-call-flow) |
| 配置与 overrides | `api_config.agent_overrides` 与优先级 | [§4](#4-配置管理与-agent_overrides-configuration--agent_overrides) |
| 新 Agent 快速上手 | 6 步注册新专家 | [§5](#5-新-agent-创建流程-how-to-add-a-new-agent) |
| LLM & Memory 速查 | OpenAI Client / SharedMemory 调用片段 | [§6](#6-llm--memory-速查表-llm--memory-quick-reference) |
| 反模式清单 | 禁止操作清单 | [§7](#7-常见反模式-anti-patterns) |
| 监控与排障 | 指标采集、常见问题 | [§8](#8-监控与排障-observability--troubleshooting) |
| 工具集成 | Browser Tool 与其他工具 | [§9](#9-工具集成-tool-integration) |

---

## 1. 当前 Agent 总览 (Current Agent Line-up)

| Channel 名称 | Python 入口 | 职责（中文主述） | Key Capability (EN) |
|--------------|-------------|-------------------|---------------------|
| `general` | `agents.general:GeneralAgent` | 对外公开入口，占位回答基础问题，负责将用户引导至协调层。 | Acts as public entry point and provides lightweight replies. |
| `coordination` | `agents.coordination:CoordinationAgent` | 核心协调中心：分析用户需求、检索历史知识、调度专家、合并答案并写入协作记录。 | Orchestrates experts, merges responses, persists collaboration traces. |
| `python_expert` | `agents.python_expert:PythonExpertAgent` | Python 相关问题的占位专家，等待接入真实执行环境。 | Python-focused scaffolding awaiting runtime tools. |
| `milvus_expert` | `agents.milvus_expert:MilvusExpertAgent` | Milvus/向量数据库问答专家，占位实现提供结构化回答。 | Milvus domain specialist scaffold. |
| `devops_expert` | `agents.devops_expert:DevOpsExpertAgent` | DevOps & 基础设施占位专家，未来负责 CI/CD、部署策略。 | DevOps subject-matter scaffold. |

**关键事实 Key facts**
- 所有 Agent 均继承自 `agents.base.BaseAgent` 并返回 `AgentResponse`。
- LLM 调用入口统一通过 `utils.get_openai_client()` 或 `OpenAIClientWrapper(config=...)`。
- 长期记忆共享组件：`agents.shared_memory.SharedMemory`，支持多租户、批量操作、缓存。

---

## 2. 能力矩阵 (Capability Matrix)

| 工作项 | Coordination | Python Expert | Milvus Expert | DevOps Expert | SharedMemory |
|--------|--------------|---------------|---------------|---------------|--------------|
| 问题解析 / Question analysis | ✅ `analyze_question()` | ⚪ （协作参与） | ⚪ | ⚪ | ❌ |
| 历史知识检索 | ✅ `retrieve_similar_knowledge()` | ⚪ | ⚪ | ⚪ | ✅ `search_knowledge()` |
| 专家调度 / Dispatch | ✅ `dispatch_to_experts()` | ⚪ | ⚪ | ⚪ | ❌ |
| 答案生成 | ✅ `synthesize_answer()` | ⚪ `handle_message()` | ⚪ | ⚪ | ❌ |
| 协作记录写入 | ✅ `store_collaboration()` | ⚪ | ⚪ | ⚪ | ✅ `store_knowledge()` |
| 向量生成 / Embedding | ✅ （通过 `OpenAIClientWrapper`） | ⚪ | ⚪ | ⚪ | ✅ `get_embeddings_batch()` |
| 缓存 & 性能指标 | ⚪ | ⚪ | ⚪ | ⚪ | ✅ `embedding_cache`, `metrics` |

> ⚪ 表示由 Agent 参与但非主导；✅ 表示核心职责。

---

## 3. 协作调用流 (Call Flow)

> *English summary: Step-by-step description of how a message traverses through the coordination agent and expert network.*

```text
用户消息 → General/Coordination Channel
 1. CoordinationAgent.handle_message()
    ├─ 调用 analyze_question() 判定涉及领域与任务类型
    ├─ 使用 retrieve_similar_knowledge() → SharedMemory.search_knowledge()
    ├─ 通过 dispatch_to_experts() 并发调用 _get_expert_response()
    │     └─ 调用目标 Agent 的 handle_message()
    ├─ synthesize_answer() 汇总消息 & 态势信息
    └─ store_collaboration() 写入 SharedMemory.collaboration_history
 2. 返回 AgentResponse(content, metadata)
```

**调度细节**
- 并发执行采用 `asyncio.gather`，出现失败时会自动重试并记录日志。
- `SUPPORTED_EXPERTS` + `HEURISTIC_KEYWORDS` 决定默认分发；可通过配置覆盖。
- `get_agent_answer_verbose(agent_name)` 控制输出长短，来自 `config.yaml` 的 `answer_verbose`。

---

## 4. 配置管理与 agent_overrides (Configuration & agent_overrides)

> *English summary: ConfigManager merges YAML defaults, environment overrides, and legacy variables.*

1. **全局配置**：`ConfigManager.get_global_config()` 读取 `.env`（`CHAT_API_*`, `EMBEDDING_API_*`）并在缺失时使用 `config.yaml` → `api_config.*` 默认值。
2. **Agent 覆盖**：`config.yaml` 内 `api_config.agent_overrides.<agent>` 可设置：
   - `chat_model`
   - `embedding_model`
   - `embedding_dimension`
   - `answer_verbose`
3. **优先级**（高 → 低）
   1. `config.yaml` 中 `agent_overrides`（针对特定 Agent）
   2. 运行时环境变量 `.env` / 系统环境 (`CHAT_API_*`, `EMBEDDING_API_*`)
   3. 兼容性变量 (`OPENAI_*`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`)

> 实际行为说明：`ConfigManager` 会优先读取环境变量；若想让 `config.yaml` 数值生效，请删除对应环境变量或改为仅在 YAML 中配置。

**配置片段参考**
```yaml
api_config:
  chat_api:
    provider: "custom"
    model: "gemini-2.5-flash"
  embedding_api:
    provider: "ollama"
    model: "qwen3-embedding:0.6b"
    dimension: 768
  agent_overrides:
    coordination:
      chat_model: "gemini-2.5-flash"
      embedding_model: "qwen3-embedding:0.6b"
      embedding_dimension: 768
      answer_verbose: false
```

**快速 API**
```python
from utils import get_agent_config, get_agent_answer_verbose

coord_config = get_agent_config("coordination")
verbose = get_agent_answer_verbose("coordination")
```

---

## 5. 新 Agent 创建流程 (How to Add a New Agent)

> *English summary: Six-step checklist to scaffold and register a brand new expert agent.*

1. **创建目录**：`agents/<my_agent>/__init__.py` 与 `agents/<my_agent>/agent.py`。
2. **实现类**：继承 `BaseAgent`，至少实现 `handle_message()`，推荐在 `__init__` 中初始化：
   - `self.config = get_agent_config(self.name)`
   - `self.client = OpenAIClientWrapper(config=self.config)`
   - `self.memory = SharedMemory(agent_name=self.name)`
3. **注册入口**：在 `agents/<my_agent>/__init__.py` 暴露 `MyAgent` 类。
4. **更新 config.yaml**：
   - `channels.<my_agent>.entrypoint = agents.my_agent:MyAgent`
   - 若需要协调调度，添加到 `routing.escalations.coordination`。
   - 根据需要增加 `api_config.agent_overrides.<my_agent>`。
5. **编写测试**：在 `tests/` 下创建 `test_my_agent.py`，覆盖消息处理、错误路径与配置加载（可复用 `tests/unit/test_env_config.py` 中的夹具）。
6. **运行验证**：
   ```bash
   make test-fast          # 排除 slow/integration
   make run-network        # 启动网络进行手动验证
   ```

> 参考模板：`agents/general/agent.py`（最小响应），`agents/coordination/agent.py`（完整工作流）。

---

## 6. LLM & Memory 速查表 (LLM & Memory Quick Reference)

### 6.1 OpenAI Client Wrapper

```python
from utils import get_openai_client, get_agent_config, OpenAIClientWrapper

# 全局客户端（基于环境配置或 YAML 默认）
global_client = get_openai_client()

# Agent 特定客户端
coord_config = get_agent_config("coordination")
coord_client = OpenAIClientWrapper(config=coord_config)

# 聊天补全
response = coord_client.get_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful coordinator."},
        {"role": "user", "content": "Explain the Milvus + Python integration."},
    ],
    temperature=0.2,
    max_tokens=400,
)
print(response.choices[0].message.content)

# 批量 Embedding（推荐）
prompts = ["Milvus collection schema", "DevOps deployment"]
embeddings = coord_client.get_embeddings_batch(prompts)
```

### 6.2 SharedMemory 操作

```python
from agents.shared_memory import SharedMemory

memory = SharedMemory(agent_name="coordination")

# 单条入库
memory.store_knowledge(
    collection="expert_knowledge",
    tenant_id="project_a",
    content={
        "expert_domain": "milvus",
        "summary": "How to configure Milvus for local development",
    },
    metadata={"source_agent": "coordination"},
)

# 语义检索
results = memory.search_knowledge(
    collection="expert_knowledge",
    tenant_id="project_a",
    query="Milvus local quickstart",
    top_k=3,
    threshold=0.72,
)

# 健康检查 & 指标
print(memory.health_check())
print({
    "cache_hit_ratio": memory.metrics.cache_hit_ratio,
    "embedding_calls": memory.metrics.embedding_calls,
})
```

---

## 7. 常见反模式 (Anti-Patterns)

| 反模式 | 风险 | 正确做法 |
|--------|------|----------|
| 直接 `import openai` 实例化客户端 | 破坏统一配置、无法支持多提供商 | 始终通过 `get_openai_client()` 或 `OpenAIClientWrapper` |
| 未传 `tenant_id` 调用 SharedMemory | 多租户数据串行 | 所有读写都必须携带 `tenant_id` |
| `print()` 调试 | 无法纳入 log pipeline | 使用 `loguru.logger`，附加 `extra` 字段 |
| 吞异常（`except Exception: pass`） | 排障困难，协作流程失真 | 捕获特定异常并 `logger.exception(...)` 后返回降级结果 |
| 重复生成相同 embedding | 成本与延迟增加 | 使用 `get_embeddings_batch()` + 内建缓存 |
| 在异步上下文调用 `asyncio.run()` | 阻塞事件循环 | 直接 `await` 协程或创建任务 |
| 硬编码 API Key | 泄露敏感信息 | 使用 `.env` + `config.yaml` |

---

## 8. 监控与排障 (Observability & Troubleshooting)

| 指标/问题 | 位置 | 解决方案 |
|-----------|------|----------|
| 嵌入缓存命中率 | `SharedMemory.metrics.cache_hit_ratio` | 调整 `SharedMemory(cache_size=...)`，优先使用批量接口 |
| Milvus 连接失败 | `memory.health_check()` 返回 `milvus_connected=False` | 确认 `MILVUS_URI` 为 HTTP(S) 或正确的本地端口，必要时使用 `make milvus-lite` |
| LLM Provider 超时 | `logger` 中 `OpenAIError` | 在 `.env` 中调高 `CHAT_API_TIMEOUT`，或在 `config.yaml` 修改 `max_retry_delay` |
| Browser Tool 搜索失败 | `logger` 中 `SearchProviderError` 或 `RateLimitError` | 检查 `BROWSER_SEARCH_API_KEY`；启用 fallback provider；调整 `BROWSER_RATE_LIMIT_DELAY` |
| Playwright 初始化失败 | `NavigationError: playwright is required` | 执行 `make setup-playwright` 或 `pip install playwright && playwright install chromium` |
| Browser Tool 延迟过高 | 搜索操作超过 10 秒 | 增加 `BROWSER_SEARCH_TIMEOUT`；启用缓存 `BROWSER_CACHE_ENABLED=true`；切换更快的 provider |
| agent_overrides 未生效 | `CoordinationAgent` 日志仍显示默认模型 | 确认删除同名环境变量，执行 `utils.reload_config()` 或重启进程 |
| 并发任务失败 | `CoordinationAgent.dispatch_to_experts` 日志 | 检查目标 Agent 是否注册，必要时将条目加入 `channels` 与 `routing` |

> 更多运行命令请参考 [README.md](README.md) 与 [Code Map](docs/architecture/codemap.md)。

---

## 9. 工具集成 (Tool Integration)

### 9.1 Browser Tool (Web Search & Navigation)

**Status**: ✅ Implemented and tested  
**Purpose**: Enable agents to search the web, navigate pages, and extract content.

**Quick Start**:
```python
from tools.browser_tool import BrowserTool, BrowserResult

# Initialize with agent-specific config
browser = BrowserTool(agent_name="coordination")

# Simple search
result = await browser.search("Milvus vector database", max_results=5)

# Search + visit top results
result = await browser.search_and_visit(
    query="Python async best practices",
    max_results=5,
    visit_top_n=2
)

# Access results
for search_result in result.search_results:
    print(f"{search_result.title}: {search_result.url}")

for page in result.visited_pages:
    print(f"Content from {page.title}: {page.text[:200]}...")
```

**Configuration** (in `config.yaml`):
```yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "tavily"  # or "bing", "google", "searxng", "duckduckgo"
    search_api_key: null  # Set via BROWSER_SEARCH_API_KEY
    fallback_provider: "duckduckgo"
    browser_engine: "playwright"
    search_timeout: 10
    navigation_timeout: 30
    max_retries: 3
```

**Memory Persistence** (explicit opt-in):
```python
# Agent decides whether to persist
if self._should_persist_web_results(user_query):
    memory = SharedMemory(agent_name=self.name)
    for page in browser_result.visited_pages:
        await memory.store_knowledge(
            collection="web_snapshots",
            tenant_id=self._get_tenant_id(),
            content={"url": page.url, "title": page.title, "text": page.text},
            metadata={"source": "browser_tool", "query": browser_result.query}
        )
```

**Key Design Principles**:
- **Search Provider Hierarchy**: Tavily (primary) → DuckDuckGo (fallback) → Optional (Bing, Google CSE)
- **Explicit Memory Control**: Agents choose when to persist (no automatic writes)
- **Configuration Reuse**: Browser tool inherits agent's `OpenAIClientWrapper` for synthesis
- **Error Handling**: Graceful degradation when search/navigation fails

**Related Documentation**:
- **User guide**: [docs/tools/browser_tool.md](docs/tools/browser_tool.md) - Complete usage guide
- **Configuration**: [docs/configuration/browser_tool.md](docs/configuration/browser_tool.md) - Configuration reference
- **Design**: [docs/design/browser_tool.md](docs/design/browser_tool.md) - Design decisions
- **Tests**: [tests/unit/test_browser_tool_integration.py](tests/unit/test_browser_tool_integration.py)
- **Example**: [examples/browser_tool_demo.py](examples/browser_tool_demo.py)
- **Roadmap**: [docs/ROADMAP.md](docs/ROADMAP.md#h3--productization-extensibility--packaging) (H3 milestone)

### 9.2 Tool Integration Patterns

**When to create a new tool**:
- Tool has standalone functionality (can be tested independently)
- Multiple agents may use the tool
- Tool requires separate configuration surface
- Tool has its own dependencies/external integrations

**Tool Module Structure**:
```
tools/
  __init__.py
  my_tool.py          # Main tool implementation
  my_tool_config.py   # Configuration dataclasses (if complex)
tests/
  unit/
    test_my_tool.py   # Unit tests with mocked dependencies
  integration/
    test_my_tool_integration.py  # Integration tests with real services
```

**Configuration Integration**:
1. Add config section to `api_config` in `config.yaml`
2. Create `MyToolConfig` dataclass in `utils/config_manager.py`
3. Add `get_my_tool_config(agent_name)` utility function
4. Support agent-specific overrides via `agent_overrides.<agent>.my_tool`

**Error Handling in Tools**:
```python
try:
    result = await tool.execute()
except ToolSpecificError as e:
    logger.exception(f"Tool failed: {e}")
    # Return partial/degraded result or raise
    return PartialResult(error=str(e))
```

**Testing Checklist**:
- [ ] Unit tests with mocked external dependencies
- [ ] Integration tests with real services (use env var to skip in CI)
- [ ] Configuration loading tests (env vars + YAML)
- [ ] Agent integration tests (tool invoked from agent)
- [ ] Error handling tests (timeouts, invalid responses)
- [ ] Memory persistence tests (if applicable)
