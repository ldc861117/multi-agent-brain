# Multi-Agent Brain DEMO

这是一个完整的多智能体协作系统演示，展示了 CoordinatorAgent 与各专家 Agent 的协作流程。

## 🎯 DEMO 目标

实现一个可交互的演示，展示完整的协作流程：
```
用户提问 → Coordinator 分析 → 专家并行处理 → 结果综合 → 知识存储 → 答案展示
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保使用 Python 3.8+
python --version

# 克隆项目（如果还没有）
git clone <repository-url>
cd multi-agent-brain

# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑 .env 文件，配置你的 API 密钥
nano .env  # 或使用你喜欢的编辑器
```

**必需配置：**
```env
# Chat API (必需)
CHAT_API_KEY=your_openai_or_other_api_key
CHAT_API_BASE_URL=https://api.openai.com/v1  # 或其他服务端点
CHAT_API_MODEL=gpt-3.5-turbo

# Embedding API (可选，但建议配置)
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Milvus 数据库
MILVUS_URI=./multi_agent_memory.db
```

### 3. 运行 DEMO

#### 方式一：使用启动脚本（推荐）

```bash
# 交互式模式（默认）
./run_demo.sh

# 自动化模式
./run_demo.sh automated

# 性能测试模式
./run_demo.sh benchmark

# 跳过环境检查（如果已确认环境正常）
./run_demo.sh --no-check
```

#### 方式二：直接运行 Python 脚本

```bash
# 交互式模式
python demo_runner.py

# 自动化模式
python demo_runner.py --mode automated

# 性能测试模式
python demo_runner.py --mode benchmark
```

## 🎮 DEMO 模式

### 1. 交互式模式 (Interactive)

用户可以自由输入问题，实时观察多智能体协作过程。

**特色功能：**
- 实时问题处理和回答
- 美观的处理过程可视化
- 知识库状态监控
- 错误处理和恢复

**示例问题：**
- 如何用 Python 优化列表推导式的性能？
- Milvus 向量数据库如何处理高维向量搜索？
- 如何在 Docker 中部署 multi-agent-brain 系统？

### 2. 自动化模式 (Automated)

使用预定义的问题集，自动测试系统在各种场景下的表现。

**包含问题类型：**
- Python 性能优化
- Milvus 数据库操作
- DevOps 部署实践
- 多技术栈集成
- 系统监控和优化

**输出内容：**
- 分类统计结果
- 成功率分析
- 性能指标
- 知识积累效果

### 3. 性能测试模式 (Benchmark)

测试系统在高并发情况下的性能表现。

**测试维度：**
- 不同并发级别的响应时间
- 系统吞吐量
- 错误率统计
- 资源使用情况

**并发级别：**
- 1 个并发请求
- 3 个并发请求
- 5 个并发请求

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Brain 架构                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   用户输入   │───▶│ CoordinatorAgent │───▶│   专家智能体网络      │
└─────────────┘    └──────────────────┘    └─────────────────────┘
                          │                           │
                          ▼                           ▼
                   ┌──────────────┐         ┌────────────────────┐
                   │ SharedMemory │         │ • PythonExpert     │
                   │   知识存储    │         │ • MilvusExpert     │
                   └──────────────┘         │ • DevOpsExpert      │
                          │                   └────────────────────┘
                          ▼                           │
                   ┌──────────────┐                   ▼
                   │  历史知识检索  │         ┌────────────────────┐
                   └──────────────┘         │   综合答案生成       │
                          │                   └────────────────────┘
                          ▼                           │
                   ┌──────────────┐                   ▼
                   │  上下文增强  │         ┌────────────────────┐
                   └──────────────┘         │   知识积累存储       │
                                               └────────────────────┘
```

## 🧠 核心组件

### 1. CoordinatorAgent
- **职责**: 问题分析、专家路由、结果综合
- **特点**: 智能问题分解、上下文管理、协作协调

### 2. Expert Agents
- **PythonExpertAgent**: Python 开发和性能优化
- **MilvusExpertAgent**: 向量数据库和搜索优化
- **DevOpsExpertAgent**: 部署、运维和基础设施

### 3. SharedMemory
- **功能**: 知识存储、语义搜索、历史检索
- **特性**: 多租户隔离、向量搜索、缓存优化

## 📁 文件结构

```
demo/
├── demo_runner.py          # 主程序入口
├── demo_modes.py           # DEMO 模式实现
├── demo_output.py          # 输出格式化和可视化
├── demo_setup.py           # 环境检查和设置
├── demo_questions.json     # 预定义问题集
├── run_demo.sh            # 启动脚本
└── README_DEMO.md         # 本文档
```

## 🔧 高级配置

### Agent 模型覆盖

在 `config.yaml` 中可以为不同 Agent 配置不同的模型：

```yaml
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
    python_expert:
      chat_model: "gpt-4"
    milvus_expert:
      chat_model: "gpt-3.5-turbo"
    devops_expert:
      chat_model: "gpt-3.5-turbo"
```

### 本地 LLM 配置

使用 Ollama 等本地服务：

```env
CHAT_API_KEY=ollama
CHAT_API_BASE_URL=http://localhost:11434/v1
CHAT_API_MODEL=qwen2:7b
CHAT_API_PROVIDER=ollama

EMBEDDING_API_KEY=ollama
EMBEDDING_API_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
EMBEDDING_API_PROVIDER=ollama
```

## 📈 性能指标

### 预期性能

- **单请求响应时间**: 2-5 秒
- **并发处理能力**: 3-5 请求/秒
- **缓存命中率**: >70%
- **成功率**: >95%

### 监控指标

- 平均响应时间
- 系统吞吐量
- 错误率
- 缓存命中率
- 知识库大小

## 🐛 故障排除

### 常见问题

1. **环境检查失败**
   ```bash
   # 手动运行详细检查
   python demo_setup.py
   ```

2. **OpenAI API 连接失败**
   - 检查 API 密钥是否正确
   - 确认网络连接正常
   - 验证端点 URL 是否正确

3. **Milvus 连接失败**
   - 检查 MILVUS_URI 配置
   - 确认文件权限
   - 尝试删除现有数据库文件重新初始化

4. **内存不足**
   - 关闭其他应用程序
   - 减少并发请求数量
   - 调整缓存大小

### 日志查看

```bash
# 查看详细日志
tail -f openagents.log

# 调试模式运行
python demo_runner.py --mode interactive 2>&1 | tee demo.log
```

## 🎯 验收标准

✅ **已完成功能:**

1. ✅ demo_runner.py 完整实现，支持 3 种执行模式
2. ✅ 能成功启动所有 Agent 并建立网络连接
3. ✅ 可处理 15 个预定义问题，覆盖所有专家领域
4. ✅ 正确展示 Agent 协作过程和可视化输出
5. ✅ 知识正确存储到 SharedMemory
6. ✅ 输出清晰美观，便于理解系统工作流
7. ✅ 包含完整的错误处理和日志记录
8. ✅ 可启动脚本 run_demo.sh 可正常执行
9. ✅ 完整的环境检查和配置验证
10. ✅ DEMO 能演示系统的知识积累能力

## 🚀 后续优化方向

- [ ] 集成 Web UI 展示系统
- [ ] 添加更多性能基准测试场景
- [ ] 实现实时可视化的 Agent 协作过程
- [ ] 记录完整的执行日志供分析
- [ ] 支持自定义问题和评估标准
- [ ] 添加多语言支持
- [ ] 集成更多专家 Agent
- [ ] 支持分布式部署

## 📞 支持和反馈

如果遇到问题或有改进建议，请：

1. 查看本文档的故障排除部分
2. 检查项目根目录的其他文档
3. 提交 Issue 或 Pull Request

---

**享受多智能体协作的奇妙之旅！🤖✨**