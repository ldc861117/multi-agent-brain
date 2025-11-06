# Codemap.md - Complete Code Logic and Structure Mapping

创建一份详细的代码地图，完整映射整个 multi-agent-brain 项目的代码逻辑、结构和数据流。

## Codemap 目的
为开发者、review 人员和新贡献者提供清晰的代码导航，快速理解系统架构和模块间关系。

## 1. 系统架构总览

### 分层架构图
- **Agent Layer**: CoordinatorAgent + Expert Agents
- **Communication Layer**: OpenAgents HTTP Network (Port 8700)
- **Memory Layer**: Milvus Shared Memory + Embedding Cache
- **Client Layer**: OpenAI Client Wrapper + Custom Base URL
- **External Services**: OpenAI/DeepSeek/Milvus Lite

### 数据流示例
- **用户提问 → Coordinator 分析 → 并行执行专家 → 结果整合 → 返回答案**
- **知识累积**: Agent 执行 → 存储到 SharedMemory → 下次查询检索

## 2. 核心模块详解

### 2.1 utils/openai_client.py
- **OpenAIConfig (Dataclass)**: 配置管理
- **OpenAIClientWrapper**: 核心客户端
  - `get_chat_completion()`: 聊天补全
  - `get_embedding()`: embedding 生成
  - `_retry_with_backoff()`: 指数退避重试
- **关键特性**: 支持自定义 base_url, 重试机制, 错误处理
- **测试**: 27 个单元测试 (100% 通过)

### 2.2 agents/shared_memory.py
- **SharedMemory (同步接口)**:
  - `__init__()`: 初始化连接和集合
  - `store_knowledge()`: 存储单个知识
  - `search_knowledge()`: 语义搜索
  - `batch_store_knowledge()`: 批量存储
  - `batch_search_knowledge()`: 批量搜索
  - `health_check()`: 健康检查

- **3 个 Milvus Collections**:
  - `expert_knowledge`: 专家知识库 (tenant_id 多租户隔离)
  - `collaboration_history`: 协作历史
  - `problem_solutions`: 问题解决方案

- **EmbeddingCache**: LRU 缓存避免重复 API 调用
- **AsyncSharedMemory (异步接口, Medium Priority)**

### 2.3 agents/coordinator.py (待实现)
- **职责**: 分析问题, 协调专家, 整合答案
- **关键方法**: `analyze_question()`, `coordinate_experts()`, `on_message()`

### 2.4 agents/*_expert.py (待实现)
- **PythonExpertAgent, MilvusExpertAgent, DevOpsExpertAgent**
- **共同模式**: 查询 SharedMemory, 调用 OpenAI client, 存储知识

## 3. 关键业务流程

### 问题-回答流程
1. 用户提问 → Coordinator 接收
2. Coordinator 分析并查询 SharedMemory 历史
3. 向相关专家 channel 分发任务 (并行)
4. 各专家查询 SharedMemory, 调用 LLM, 存储知识
5. Coordinator 整合回答, 存储协作历史
6. 返回最终答案

### 知识累积流程
1. Agent 执行生成知识
2. 存储到 SharedMemory (3 个集合)
3. 下次查询时检索相似知识
4. 系统效能递增

## 4. 技术栈依赖
- `openagents>=0.6.11`: Agent 框架
- `pymilvus>=2.5.1`: 向量数据库
- `openai>=1.0.0`: LLM 调用
- `python-dotenv`: 环境变量加载
- `loguru`: 日志记录
- `pydantic`: 数据验证

## 5. 环境变量配置
- `OPENAI_API_KEY`: API 密钥
- `OPENAI_BASE_URL`: 自定义端点
  - OpenAI: https://api.openai.com/v1
  - DeepSeek: https://api.deepseek.com/v1
  - Moonshot: https://api.moonshot.cn/v1
  - Local: http://localhost:8000/v1
- `MILVUS_URI`: 数据库地址
- `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`

## 6. 测试策略
- **单元测试**: OpenAI client (27 tests), SharedMemory (待实现)
- **集成测试**: Agent 间通信, End-to-end 流程
- **性能测试**: 缓存命中率, 搜索延迟, 吞吐量

## 7. 代码规范
- **命名**: PascalCase (类), snake_case (方法/变量)
- **文档**: 所有公开方法需要 docstring
- **错误**: 自定义异常 + 详细日志
- **日志**: 使用 loguru

## 8. 开发路线图
- **Phase 1 ✅**: 基础设施 (Bootstrap, OpenAI client)
- **Phase 2 🔄**: 核心功能 (Milvus, 4 个 Agent)
- **Phase 3 📋**: 优化扩展 (异步, 性能, 部署)

## 9. 关键指标
- **Embedding 缓存命中率**: >70%
- **Search 延迟 (P99)**: <20ms
- **Agent 响应**: <5s
- **系统吞吐**: >100 QPS

## 10. 快速导航
- **如何添加新 Agent?** → 参考 agents/python_expert.py
- **如何自定义 LLM?** → 修改 .env OPENAI_BASE_URL
- **如何提高性能?** → 利用缓存和批量操作