# AGENTS.md - AI Coding Agent Developer Guide

为 AI Coding Systems（如 cto）创建一份结构化、机器可读的项目开发指南。

## AGENTS.md 的目标

这个文件是为 AI coding agents 写的，不是为人写的。目标：
- 极度结构化（表格、列表、代码块，避免长段文字）
- 立即可用（复制粘贴代码片段，无需理解即可执行）
- 快速导航（表格形式的任务→文件→方法映射）
- 明确约束（anti-patterns 列表）
- 具体位置（精确的文件路径、行号、方法名）
- 决策树（清晰的条件判断流程）
- 交叉引用（README.md/Codemap.md 的精确指向）

## 1. 项目快速概览（2-3 行足够）

```
- 项目名: multi-agent-brain
- 核心技术: OpenAgents + Milvus + OpenAI Client
- 主要组件: CoordinatorAgent + PythonExpertAgent + MilvusExpertAgent + DevOpsExpertAgent + SharedMemory
- 关键特性: 多租户隔离、向量搜索、自定义LLM端点、指数退避重试
- 主要语言: Python 3.11+
```

## 3. Build & Run 指令（完全自动化）

```bash
# 环境检查
python --version  # 需要 3.11+

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
# 复制 .env.example 到 .env 并配置
cp .env.example .env
# 编辑 .env 文件，配置你的 API 密钥和端点

# 3. 启动 OpenAgents 网络
openagents network http --config config.yaml  # 后台运行或新终端

# 4. 启动 Studio UI（新终端，可选）
openagents studio --config config.yaml

# 5. 验证服务
curl http://localhost:8700/health

# 6. 访问 Studio（如果启动）
http://localhost:8050
```

## 4. 文件导航快速查询表

**格式：任务 → 文件 → 主要方法 → 注意事项**

| 任务 | 文件 | 方法/类 | 注意事项 |
|------|------|--------|---------|
| 添加新 Agent | `agents/my_expert/agent.py` | `class MyExpertAgent(BaseAgent)` | 继承 BaseAgent，实现 handle_message() |
| 修改 LLM 调用 | `utils/openai_client.py` | `OpenAIClientWrapper.get_chat_completion()` | 支持分离的 chat 和 embedding 端点 |
| 生成 Embedding | `utils/openai_client.py` | `OpenAIClientWrapper.get_embedding_vector()` | 自动支持自定义 base_url 和 provider |
| 存储知识 | `agents/shared_memory.py` | `SharedMemory.store_knowledge()` | 需传入 tenant_id 做多租户隔离 |
| 搜索知识 | `agents/shared_memory.py` | `SharedMemory.search_knowledge()` | 返回相似度排序的结果列表 |
| 批量操作 | `agents/shared_memory.py` | `batch_store/search_knowledge()` | 性能优化，处理 >10 条记录 |
| 配置 Chat API | `.env` | `CHAT_API_*` 变量 | 支持 OpenAI/DeepSeek/Moonshot/本地LLM |
| 配置 Embedding API | `.env` | `EMBEDDING_API_*` 变量 | 可独立配置，支持 Ollama 等本地服务 |
| Agent 模型覆盖 | `config.yaml` | `api_config.agent_overrides` | per-agent 模型和维度配置 |
| 添加消息频道 | `config.yaml` | `channels` 部分 | 新 channel 需在此注册 |
| 配置管理 | `utils/config_manager.py` | `ConfigManager.get_agent_config()` | 支持环境变量 + YAML 配置 |
| 启动 Agent 实例 | `agents/my_expert/agent.py` | `MyExpertAgent()` | 创建实例并调用 handle_message() |

## 5. 核心 API 速查表

**复制即用的代码片段**

### 5.1 获取 OpenAI 客户端

```python
from utils import get_openai_client, get_agent_config, OpenAIClientWrapper

# 获取全局客户端（默认配置）
client = get_openai_client()

# 获取特定 Agent 配置的客户端
agent_config = get_agent_config("coordination")
client = OpenAIClientWrapper(config=agent_config)

# 聊天补全
response = client.get_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Milvus?"}
    ],
    temperature=0.7,
    max_tokens=500
)
print(response.choices[0].message.content)

# 单个 Embedding
embedding = client.get_embedding_vector("What is Milvus?")
print(f"Embedding dim: {len(embedding)}")  # 输出: 1536 (text-embedding-3-small) 或 3072 (text-embedding-3-large)

# 批量 Embedding（推荐）
texts = ["Milvus is a vector DB", "OpenAI is an LLM provider"]
embeddings = client.get_embeddings_batch(texts)
for emb in embeddings:
    print(f"Dimension: {len(emb.embedding)}")
```

### 5.2 操作共享记忆

```python
from agents.shared_memory import SharedMemory

# 初始化（使用默认配置）
memory = SharedMemory()

# 初始化（使用特定 Agent 配置）
memory = SharedMemory(agent_name="coordination")

# 存储知识
doc_id = memory.store_knowledge(
    collection="expert_knowledge",
    tenant_id="project_a",
    content={
        "expert_domain": "milvus",
        "content": "Milvus is a vector database supporting CRUD operations..."
    },
    metadata={"source": "python_expert", "category": "tutorial"}
)

# 搜索知识
results = memory.search_knowledge(
    collection="expert_knowledge",
    tenant_id="project_a",
    query="How to use Milvus?",
    top_k=5,
    threshold=0.7  # 相似度阈值
)
for result in results:
    print(f"ID: {result['id']}, Score: {result['similarity_score']}")
    print(f"Content: {result['content']['content'][:100]}...")

# 批量存储（性能优化）
doc_ids = memory.batch_store_knowledge(
    collection="problem_solutions",
    tenant_id="project_a",
    contents=[
        {"problem": "Q1", "solution": "A1"},
        {"problem": "Q2", "solution": "A2"},
        # ...
    ]
)

# 批量搜索（性能优化）
queries = ["Q1", "Q2"]
batch_results = memory.batch_search_knowledge(
    collection="problem_solutions",
    tenant_id="project_a",
    queries=queries,
    top_k=3,
    threshold=0.7
)

# 健康检查
health = memory.health_check()
print(health)  # {"milvus_connected": true, "collections": {...}}

# 删除租户数据（GDPR）
deleted_count = memory.delete_by_tenant("expert_knowledge", "project_a")
```

### 5.3 创建新 Agent

```python
from agents.base import BaseAgent, AgentResponse
from utils import get_agent_config, OpenAIClientWrapper
from agents.shared_memory import SharedMemory
from loguru import logger
from typing import Any, Mapping, MutableMapping, Optional

class MyExpertAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.name = "my_expert"
        self.description = "My custom expert agent"
        
        # 获取 Agent 特定配置
        agent_config = get_agent_config(self.name)
        self.client = OpenAIClientWrapper(config=agent_config)
        
        # 使用 Agent 特定配置初始化共享记忆
        self.memory = SharedMemory(agent_name=self.name)
    
    async def handle_message(
        self,
        message: Mapping[str, Any],
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        """处理消息的主逻辑"""
        # 1. 从消息中提取内容
        text_content = message.get('content', {}).get('text', '')
        logger.info(f"Received message: {text_content}")
        
        # 2. 查询共享记忆获取历史知识
        similar_docs = self.memory.search_knowledge(
            collection="expert_knowledge",
            tenant_id="default",
            query=text_content,
            top_k=3
        )
        logger.info(f"Found {len(similar_docs)} similar documents")
        
        # 3. 调用 LLM 生成回答
        context_text = "\n".join([d["content"]["content"] for d in similar_docs])
        response = self.client.get_chat_completion(
            messages=[
                {"role": "system", "content": f"You are a helpful expert. Context: {context_text}"},
                {"role": "user", "content": text_content}
            ],
            temperature=0.7
        )
        answer = response.choices[0].message.content
        logger.info(f"Generated answer: {answer}")
        
        # 4. 存储重要知识到共享记忆
        self.memory.store_knowledge(
            collection="collaboration_history",
            tenant_id="default",
            content={
                "interaction_id": str(message.get('id', 'unknown')),
                "initiator_agent": "user",
                "participating_agents": "my_expert",
                "task_description": text_content
            },
            metadata={"answer": answer}
        )
        
        # 5. 返回回答
        return AgentResponse(content=answer)
```

## 6. 常见开发任务（决策树）

### 6.1 我想添加一个新的 Expert Agent

```
步骤 1: 在 agents/ 目录创建文件夹
  文件夹: agents/my_expert/
  文件: agents/my_expert/__init__.py, agents/my_expert/agent.py
  
步骤 2: 实现 Agent 类
  继承: BaseAgent (from agents.base)
  必实现: __init__() 和 handle_message()
  推荐: 初始化时创建 client 和 memory 实例
  
步骤 3: 在 config.yaml 注册 channel
  位置: config.yaml 的 channels 部分
  添加: 
    my_expert:
      description: "My custom expert agent"
      entrypoint: agents.my_expert:MyExpertAgent
      visibility: internal
  
步骤 4: 在 routing 中添加路由（可选）
  位置: config.yaml 的 routing.escalations 部分
  添加: - my_expert
  
步骤 5: 创建 __init__.py 文件
  文件: agents/my_expert/__init__.py
  内容: from .agent import MyExpertAgent
  
步骤 6: 编写单元测试
  文件: tests/test_my_expert.py
  覆盖: handle_message() 逻辑和错误处理
  
参考代码: agents/general/agent.py (模板)
Codemap: 2.3-2.4
```

### 6.2 我想修改 LLM 端点（OpenAI → DeepSeek）

```
步骤 1: 编辑 .env 文件
  改: CHAT_API_KEY=your_openai_key
  为: CHAT_API_KEY=your_deepseek_key
  
  改: CHAT_API_BASE_URL=https://api.openai.com/v1
  为: CHAT_API_BASE_URL=https://api.deepseek.com/v1
  
  改: CHAT_API_MODEL=gpt-3.5-turbo
  为: CHAT_API_MODEL=deepseek-chat
  
步骤 2: 修改模型名称（可选）
  改: CHAT_API_MODEL=gpt-3.5-turbo
  为: CHAT_API_MODEL=deepseek-chat
  
步骤 3: 无需改代码！
  utils/openai_client.py 会自动加载 .env 配置
  所有 Agent 会自动使用新端点

验证: 调用任何 Agent，查看日志确认使用的端点
```

### 6.3 我想扩展知识库（添加新 Collection）

```
步骤 1: 在 shared_memory.py 中定义新集合
  位置: agents/shared_memory.py 的 _setup_collections()
  
  fields = [
      FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
      FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=65535),
      FieldSchema(name="my_field1", dtype=DataType.VARCHAR, max_length=65535),
      FieldSchema(name="my_field2", dtype=DataType.FLOAT_VECTOR, dim=3072),
      # ... 其他字段
  ]
  schema = CollectionSchema(fields, primary_field="id", partition_key="tenant_id")
  collection = Collection("my_collection", schema)
  
步骤 2: 在 store_knowledge() 中处理新集合
  位置: agents/shared_memory.py 的 store_knowledge() 方法
  
  if collection == "my_collection":
      entity = {
          "tenant_id": tenant_id,
          "my_field1": content["my_field1"],
          "my_field2": content["my_field2"],
      }
      # ... 插入逻辑
  
步骤 3: 在 search_knowledge() 中支持查询
  位置: agents/shared_memory.py 的 search_knowledge() 方法
  
  if collection == "my_collection":
      # ... 搜索逻辑
  
步骤 4: 测试
  创建 → 存储 → 搜索 → 验证结果
```

### 6.4 我想使用本地 LLM（Ollama）

```
步骤 1: 启动 Ollama
  ollama serve
  ollama pull qwen2:7b  # 或其他模型
  
步骤 2: 编辑 .env
  CHAT_API_KEY=ollama  # 占位符
  CHAT_API_BASE_URL=http://localhost:11434/v1
  CHAT_API_MODEL=qwen2:7b
  CHAT_API_PROVIDER=ollama
  
  EMBEDDING_API_KEY=ollama
  EMBEDDING_API_BASE_URL=http://localhost:11434/v1
  EMBEDDING_API_MODEL=nomic-embed-text
  EMBEDDING_API_PROVIDER=ollama
  EMBEDDING_DIMENSION=768
  
步骤 3: 验证连接
  curl http://localhost:11434/v1/models
  
步骤 4: 启动系统
  openagents network http --config config.yaml

注意: 本地 LLM 可能较慢，调整 timeout
```

### 6.5 我想优化性能（缓存命中率）

```
问题: 频繁调用 get_embedding()，成本和延迟高

解决方案:
  1. 使用 batch_store_knowledge() 而非循环 store_knowledge()
  2. 使用 batch_search_knowledge() 而非循环 search_knowledge()
  3. EmbeddingCache 自动缓存生成的 embedding
  
监控:
  memory.metrics.cache_hit_ratio  # 查看命中率
  len(memory.embedding_cache._cache)  # 查看缓存大小
  
调整:
  SharedMemory(cache_size=2000)  # 增大缓存
  
目标: cache_hit_ratio > 70%
```

## 6. 代码约定（必须遵守）

### 6.1 命名规范

```python
# 类: PascalCase
class MyExpertAgent(BaseAgent):
    pass

# 方法: snake_case
def handle_message(self, message):
    pass

# 私有方法: _leading_underscore
def _setup_collections(self):
    pass

# 常量: UPPER_CASE
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3

# 变量: snake_case
tenant_id = "project_a"
embedding_dimension = 3072
```

### 6.2 导入规范

```python
# ❌ 错误：直接导入第三方
import openai
client = openai.OpenAI(...)  # 不要这样！

# ✅ 正确：使用封装的客户端
from utils import get_openai_client
client = get_openai_client()

# 包内导入：相对路径
from .openai_client import OpenAIClientWrapper

# 跨包导入：绝对路径
from agents.shared_memory import SharedMemory

# 避免循环导入
# 不要: from agents.coordinator import CoordinatorAgent 在 shared_memory.py 中
```

### 6.3 错误处理

```python
# ❌ 错误：吞掉异常
try:
    memory.search_knowledge(...)
except:
    pass

# ✅ 正确：捕获特定异常并记录
from openai import RateLimitError
try:
    memory.search_knowledge(...)
except RateLimitError as e:
    logger.error(f"Rate limit hit: {e}", extra={"retry_after": e.retry_after})
    # 由 client 的重试机制处理
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return []  # 优雅降级
```

### 6.4 日志记录

```python
from loguru import logger

# ❌ 错误
print("Agent started")

# ✅ 正确
logger.info("Agent started", extra={"agent_id": self.name})

# ❌ 错误：记录敏感信息
logger.info(f"API key: {api_key}")

# ✅ 正确：隐藏敏感信息
logger.info(f"API key: {api_key[:10]}...")

# ✅ 记录关键指标
import time
start = time.time()
result = memory.search_knowledge(...)
duration = time.time() - start
logger.info(
    "Search completed",
    extra={
        "query": query,
        "results_count": len(result),
        "duration_ms": int(duration * 1000),
        "cache_hit": was_cached
    }
)
```

## 7. 不应该做的（Anti-Patterns）

| 反模式 | 为什么不行 | 正确做法 |
|--------|----------|---------|
| `import openai; openai.OpenAI(...)` | 硬编码配置，不支持自定义 base_url | 使用 `get_openai_client()` |
| `print("debug info")` | 无法被监控系统捕获 | 使用 `logger.info()` |
| `api_key = "sk-xxx"` | 硬编码密钥泄露风险 | 使用 `.env` 和环境变量 |
| 操作不传 `tenant_id` | 破坏多租户隔离 | 所有操作都明确传入 `tenant_id` |
| 同步调用 async 方法 | 会阻塞事件循环 | 在 async 函数中用 `await` |
| 异常发生后继续执行 | 状态不一致 | 记录日志后 raise 或 return |
| 直接修改 `config.yaml` | Agent 重启不应用 | 使用环境变量或 API 重新加载 |
| 创建多个客户端实例 | 浪费资源和连接 | 使用全局单例 `get_openai_client()` |
| embedding 维度不匹配 | Milvus 插入失败 | 确保 EMBEDDING_DIMENSION 与模型匹配 (small=1536, large=3072) |
| 不记录错误就 try-except | 无法排查问题 | 使用 `logger.exception()` |

## 8. 常见错误排查

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Milvus connection refused` | Milvus 服务未启动或路径错误 | 检查 MILVUS_URI，确保文件路径正确 |
| `OpenAI RateLimitError` | API 调用频繁或配额超 | client 会自动重试，检查 API 配额 |
| `embedding dimension 3072 != 1536` | embedding 模型不匹配 | 确保 EMBEDDING_DIMENSION 与模型匹配 (text-embedding-3-small=1536, text-embedding-3-large=3072) |
| `Channel not found in config` | 新 channel 未在 config.yaml 注册 | 在 `channels` 部分添加定义 |
| `Agent failed to start` | 网络配置错误或 channel 不存在 | 检查 config.yaml 和日志输出 |
| `asyncio.run() called from running event loop` | 在 async 环境中调用 asyncio.run() | 改用 `await` 而非 `asyncio.run()` |
| `Pydantic validation error` | 环境变量类型不匹配 | 检查 OpenAIConfig 的类型定义 |
| `Cannot import module` | Python 路径问题 | 确保项目根目录在 PYTHONPATH 中 |

## 9. 性能和最佳实践

### 9.1 优化查询

```python
# ❌ 低效：循环查询
for query in queries:
    result = memory.search_knowledge(..., query=query)

# ✅ 高效：批量查询
results = memory.batch_search_knowledge(..., queries=queries)
```

### 9.2 优化存储

```python
# ❌ 低效：循环插入
for doc in docs:
    memory.store_knowledge(..., content=doc)

# ✅ 高效：批量插入
memory.batch_store_knowledge(..., contents=docs)
```

### 9.3 利用 Embedding 缓存

```python
# ❌ 重复调用同一查询，浪费 API 调用
for i in range(100):
    memory.search_knowledge(..., query="same_query")  # 100 次 embedding

# ✅ 自动缓存
# 第 1 次: 调用 OpenAI API 并缓存
result1 = memory.search_knowledge(..., query="same_query")

# 第 2-100 次: 使用缓存，无 API 调用
result2 = memory.search_knowledge(..., query="same_query")

# 监控
logger.info(f"Cache hit ratio: {memory.metrics.cache_hit_ratio:.2%}")
```

### 9.4 关键监控指标

```python
# Embedding 缓存
cache_metrics = {
    "hit_ratio": memory.metrics.cache_hit_ratio,      # 目标 >70%
    "size": len(memory.embedding_cache._cache),       # 当前大小
    "max_size": memory.embedding_cache.max_size       # 配置大小
}

# 搜索性能
search_metrics = {
    "latency_p99": 20,      # ms，目标 <20ms
    "avg_similarity": 0.85, # 平均相似度
    "results_count": 5      # 返回结果数
}

# API 调用
api_metrics = {
    "embedding_calls": memory.metrics.embedding_calls,
    "storage_operations": memory.metrics.storage_operations,
    "errors_count": memory.metrics.errors_count
}

# 监控和记录这些指标
logger.info("Performance metrics", extra={**cache_metrics, **search_metrics, **api_metrics})
```

## 10. 配置快速参考

### 10.1 环境变量（.env）

```ini
# Chat API 配置（必需）
CHAT_API_KEY=sk-xxx

# 可选，但推荐配置
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_MODEL=gpt-3.5-turbo
CHAT_API_PROVIDER=openai
CHAT_API_TIMEOUT=30
CHAT_API_MAX_RETRIES=3
CHAT_API_RETRY_DELAY=1.0
CHAT_API_MAX_RETRY_DELAY=60.0

# Embedding API 配置（可选）
EMBEDDING_API_KEY=sk-xxx  # 可为空，用于本地服务
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_MODEL=text-embedding-3-small
EMBEDDING_API_PROVIDER=openai
EMBEDDING_DIMENSION=1536
EMBEDDING_API_TIMEOUT=30
EMBEDDING_API_MAX_RETRIES=3
EMBEDDING_API_RETRY_DELAY=1.0
EMBEDDING_API_MAX_RETRY_DELAY=60.0

# Milvus
MILVUS_URI=./multi_agent_memory.db

# 兼容性配置（向后兼容）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_TIMEOUT=30
OPENAI_MAX_RETRIES=3
OPENAI_RETRY_DELAY=1.0
OPENAI_MAX_RETRY_DELAY=60.0
```

### 10.2 网络配置（config.yaml）

```yaml
# API 配置
api_config:
  # 全局默认 Chat API
  chat_api:
    provider: "openai"  # openai, ollama, custom
    model: "gpt-3.5-turbo"
    timeout: 30
    max_retries: 3
    retry_delay: 1.0
    max_retry_delay: 60.0
  
  # 全局默认 Embedding API
  embedding_api:
    provider: "openai"  # openai, ollama, custom
    model: "text-embedding-3-small"
    dimension: 1536
    timeout: 30
    max_retries: 3
    retry_delay: 1.0
    max_retry_delay: 60.0
  
  # Agent 特定覆盖（可选）
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
    python_expert:
      chat_model: "gpt-4"
    milvus_expert:
      chat_model: "gpt-3.5-turbo"
    devops_expert:
      chat_model: "gpt-3.5-turbo"

# 添加新 channel
channels:
  my_new_channel:
    description: "My custom agent channel"
    entrypoint: agents.my_expert:MyExpertAgent
    visibility: internal
    targets:
      - coordination

# 路由配置
routing:
  default_target: general
  escalations:
    coordination:
      - python_expert
      - milvus_expert
      - devops_expert
      - my_new_channel  # 新增
```

## 11. 常用命令速查表

```bash
# 启动系统
openagents network http --config config.yaml
openagents studio --config config.yaml  # 可选

# 验证服务
curl http://localhost:8700/health
curl http://localhost:8050  # Studio

# 测试
python -m pytest utils/test_openai_client.py -v
python -m pytest test_shared_memory.py -v
python -m pytest --cov=agents --cov=utils --cov-report=html

# 运行示例
python examples/openai_client_examples.py
python examples/shared_memory_usage.py

# 清理
rm -rf multi_agent_memory.db  # 重置数据库
```

## 12. 测试指南

```python
# 单元测试模板
import pytest
from agents.my_expert.agent import MyExpertAgent
from agents.shared_memory import SharedMemory

@pytest.mark.asyncio
async def test_my_agent_handle_message():
    agent = MyExpertAgent()
    
    # 模拟消息
    message = {
        "content": {"text": "What is Python?"},
        "id": "test_123"
    }
    
    # 调用处理方法
    response = await agent.handle_message(message)
    
    # 验证结果
    assert response.content is not None
    assert len(response.content) > 0
    
    # 验证知识存储
    memory = SharedMemory()
    results = memory.search_knowledge(
        collection="collaboration_history",
        tenant_id="default",
        query="What is Python?",
        top_k=1
    )
    assert len(results) > 0

# 运行测试
pytest test_my_expert.py -v  # 如果在根目录
pytest --cov=agents --cov=utils --cov-report=html  # 覆盖率
```

## 13. 文档交叉引用

```
更多信息:
- 快速开始: README.md#快速开始
- 架构详解: Codemap.md#系统架构总览
- 配置说明: README.md#配置说明
- Agent 实现: Codemap.md#核心模块详解
- 使用示例: README.md#核心特性
- OpenAI 客户端: utils/openai_client.py
- 共享内存: agents/shared_memory.py
- 基础 Agent: agents/base.py
- 网络配置: config.yaml
```