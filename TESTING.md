# 测试指南 (Testing Guide)

> 中文为主的测试操作手册；*English note: end-to-end cheat sheet for local pytest runs, coverage, helpers, and CI expectations.*

---

## 1. 快速开始 / Quick Start

1. **安装依赖**：`make install`（或手动创建 `.venv` 并安装 `requirements.txt`）。
2. **激活虚拟环境**：`source .venv/bin/activate`（Windows 使用 `Scripts\activate`）。
3. **运行完整测试**：`make test`（等价于 `PYTHONPATH=. pytest -q`）。
4. **快速反馈**：`make test-fast`（排除 `slow` 与 `integration` 标记）。
5. **单文件调试**：`PYTHONPATH=. pytest tests/test_openai_client.py -vv`。

*Tip (EN): Always prefix manual pytest runs with `PYTHONPATH=.` so package imports resolve exactly like CI.*

---

## 2. 常用命令速查 (Core Commands)

| 命令 | 作用（中文） | English Hint |
|------|---------------|--------------|
| `make install` | 创建虚拟环境并安装依赖 | Bootstrap env |
| `make test` | 运行完整 pytest 套件（含 `-q` 与 `--strict-markers`） | Full suite |
| `make test-fast` | 跳过 `slow` / `integration` 测试，适合本地快速循环 | Fast lane |
| `make cov` | `pytest --cov`，生成 `coverage.xml` 与 `htmlcov/` | Coverage run |
| `make cov-html` | 刷新 HTML 覆盖率报告（依赖 `make cov`） | View HTML report |
| `make verify-tests` | 调用 `python -m tests.tools.verify_tests` 列出关键测试文件并可选择执行 | Suite skeleton overview |
| `python -m tests.tools.network_smoke` | HTTP API 冒烟测试（注册 → 发送 → 注销） | Smoke check |

---

## 3. Pytest 标记 (Markers)

`pytest.ini` 启用了 `--strict-markers`，未知标记会立即报错。

| 标记 | 用途（中文） | English Summary |
|------|---------------|-----------------|
| `@pytest.mark.unit` | 纯单元测试，完全隔离外部服务 | Unit-level |
| `@pytest.mark.integration` | 可能访问外部服务或依赖真实网络 | Integration-heavy |
| `@pytest.mark.slow` | 运行时间较长的测试；默认在 `make test-fast` 中跳过 | Long-running |
| `@pytest.mark.smoke` | 轻量级冒烟测试，适合部署后验证 | Smoke |

运行指定标记示例：
```bash
# 仅运行 smoke + unit (中文说明)
PYTHONPATH=. pytest -m "smoke or unit"

# 跳过 slow / integration (English hint)
PYTHONPATH=. pytest -m "not slow and not integration"
```

---

## 4. 覆盖率与输出 (Coverage & Reports)

- `make cov` 会启用分支覆盖率，统计 `agents/` 与 `utils/`，忽略 `tests/`。
- 报告位置：
  - **终端**：缺失行摘要（`--cov-report=term-missing`）。
  - **XML**：`coverage.xml`（供 CI 上传）。
  - **HTML**：`htmlcov/index.html`（本地浏览器查看）。
- `.coveragerc` 已排除 `pragma: no cover`、`if __name__ == "__main__"` 等样板代码。

*EN Note: CI enforces the same configuration—keep coverage gaps intentional and justified via `pragma: no cover`.*

---

## 5. 测试工具与脚本 (Helper Utilities)

所有测试相关脚本已集中在 `tests/tools/`，导入时不会产生副作用：

| 模块 | 功能 | 示例 |
|------|------|------|
| `tests.tools.verify_tests` | 列出核心测试文件数量、可选执行 | `python -m tests.tools.verify_tests --run -m "-vv"` |
| `tests.tools.network_smoke` | OpenAgents HTTP 冒烟流程 | `python -m tests.tools.network_smoke --channel coordination "Explain Milvus"` |
| `tests.tools.verify_multi_expert_dispatch` | 协调器路由验证（使用内存替身） | `python -m tests.tools.verify_multi_expert_dispatch` |
| `tests.tools.verify_demo_implementation` | DEMO 交付物完整性校验 | `python -m tests.tools.verify_demo_implementation` |

---

## 6. 常见坑与最佳实践 (Common Pitfalls & Best Practices)

1. **环境变量污染**：测试需使用 `pytest` 的 `monkeypatch` + `mock_load_dotenv` 夹具，避免读取真实 `.env`。(*EN: never rely on host env in tests.*)
2. **遗漏 `PYTHONPATH`**：直接运行 `pytest` 可能找不到 `agents/` 模块；使用 `PYTHONPATH=. pytest …` 或 Makefile 目标。
3. **未声明标记**：新增 `@pytest.mark.xxx` 之前先在 `pytest.ini` 注册，否则 `--strict-markers` 会失败。
4. **共享状态**：利用 `autouse` 级别夹具（例如 `clean_env`、`reset_global_state`）重置全局缓存。
5. **HTTP/外部依赖**：默认测试应 stub/mocker；仅在 `@pytest.mark.integration` 中访问真实服务。

---

## 7. CI 行为 (CI Expectations)

- GitHub Actions workflow `python-ci.yml` 在 **Python 3.10** 与 **3.11** 上运行 `pip install -r requirements.txt` 与 `pytest --cov`。
- 生成的 `coverage.xml` / `htmlcov/` 作为 artefact 上传，阈值保持与本地一致。
- PR 合入前建议在本地依次执行：`make test-fast` → `make cov`，确保与 CI 表现一致。
- *EN reminder: keep helper scripts side-effect free so CI imports remain deterministic.*

---

## 8. 故障排查 (Troubleshooting)

| 症状 | 原因 & 解决方案（中文） | English Tip |
|------|-------------------------|-------------|
| `ImportError: No module named agents` | 忘记设置 `PYTHONPATH=.`；通过 Makefile 调用或在命令前添加变量 | Add `PYTHONPATH=. ` |
| 覆盖率显著下降 | 新模块缺少测试，或未将文件加入 `agents/` / `utils/` | Add targeted tests |
| `RuntimeError: load_dotenv` 读取真实文件 | 在测试中缺少 `mock_load_dotenv` 夹具 | Stub dotenv |
| `pytest` 报 Unknown mark | 需要在 `pytest.ini` 注册标记 | Register mark |

---

如需进一步了解配置与历史背景，可参阅：
- `ENV_CONFIG_TEST_DOCUMENTATION.md`
- `OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md`
- `AGENTS.md` 与 `Codemap.md`

> Keep tests deterministic, isolate side effects, and rely on the consolidated tooling under `tests/tools/` for repeatable workflows.
