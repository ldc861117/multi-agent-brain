# Testing Guide

> Comprehensive instructions for exercising the multi-agent-brain test matrix after the root cleanup. Includes environment isolation requirements, suite organization, coverage workflow, and common pitfalls.

## 1. Test Layout

All automated tests now live under the consolidated `tests/` package:

```
tests/
├── conftest.py            # Global fixtures & automatic test markers
├── fixtures/              # Shared pytest fixtures (future expansion)
├── unit/                  # Deterministic unit test suites
│   ├── test_config_validator.py
│   ├── test_env_config.py
│   ├── test_imports_smoke.py
│   ├── test_openai_client.py
│   ├── test_shared_memory.py
│   ├── test_shared_memory_minimal.py
│   └── test_utils_coverage_boost.py
├── integration/           # Lightweight integration & smoke tests
│   ├── test_demo_cli_smoke.py
│   └── test_lm.py
└── e2e/                   # Placeholder for future full end-to-end flows
```

`tests/conftest.py` injects project root onto `sys.path`, isolates sensitive environment variables, and auto-labels files with `unit`, `integration`, or `e2e` markers based on their directory. This ensures consistent `-m` selection without touching individual test files.

## 2. Running the Suites

### Quick Commands (Makefile)

| Command | Description |
|---------|-------------|
| `make test` | Runs the full pytest suite via `scripts/run_tests.sh` with default quiet verbosity. |
| `make test-fast` | Executes unit tests only (`-q -m "not slow and not integration"`). |
| `make cov` | Runs pytest with coverage reports (`coverage.xml`, `htmlcov/`). |
| `make cov-html` | Alias for `make cov` to refresh the HTML coverage artefact. |
| `make quick-verify` | Prints an overview of key unit files and optionally executes them (`scripts/quick_verify.py --run`). |
| `make lint` / `make format` | Delegates to `scripts/lint.sh` / `scripts/format.sh` for consistent tooling. |
| `make ci` | Runs lint then coverage test run (mirrors GitHub Actions behaviour). |

### Direct pytest Usage

The project enforces strict markers. Thanks to `pytest_collection_modifyitems`, the following commands work without additional decorators:

```bash
# Run all unit tests
pytest -m unit

# Run only integration smoke tests
pytest -m integration

# Exclude slow + integration (mirrors make test-fast)
pytest -m "not slow and not integration"

# Target an individual module
pytest tests/unit/test_env_config.py -vv

# Target a single test case
pytest tests/unit/test_env_config.py::TestChatAPIConfiguration::test_api_key_loading -vv
```

### Helper Scripts

- `scripts/run_tests.sh` – wraps `python -m pytest`, injects `PYTHONPATH`, and defaults to `-q` when no arguments are supplied.
- `scripts/quick_verify.py` – prints file sizes/class counts for the core unit modules; pass `--run` to execute them immediately.
- `scripts/verify_test.py` – convenience runner for a single target (defaults to `tests/unit/test_env_config.py`).

## 3. Environment Isolation & Fixtures

- **Automatic cleanup**: `conftest.py` removes all `CHAT_API_*`, `EMBEDDING_API_*`, `OPENAI_*`, `MILVUS_URI`, and logging-related variables before each test via the `isolate_environment` fixture.
- **No `.env` leakage**: `dotenv.load_dotenv` is monkeypatched to a no-op to prevent accidental test pollution.
- **Shared mocks**: Many unit modules mock `pymilvus` and `numpy` to avoid heavyweight dependencies; these mocks live inside the tests themselves to keep fixture scopes tight.

When adding new tests, prefer `pytest.MonkeyPatch` over `patch.dict` for environment manipulation and reuse shared fixtures from `tests/fixtures/` when they become available.

## 4. Coverage & Reporting

Coverage settings are defined in `.coveragerc`. Notable points:

- Only `agents/` and `utils/` count towards coverage; `tests/`, `scripts/`, and generated artefacts are excluded.
- Run `make cov` locally before opening a PR; CI requires a minimum coverage threshold (currently 60%).
- HTML reports live in `htmlcov/index.html`; XML output is stored as `coverage.xml` for CI artefacts.

## 5. Common Pitfalls

1. **Missing API keys** – `tests/integration/test_lm.py` skips automatically when neither `CHAT_API_KEY` nor `OPENAI_API_KEY` is set. Provide throwaway keys only when necessary.
2. **Forgotten markers** – Do not apply manual `@pytest.mark.unit` / `@pytest.mark.integration` decorators unless absolutely required. Directory placement handles markers automatically.
3. **Environment bleed** – Avoid referencing `os.environ` directly in assertions; use the `clean_env` fixture pattern for deterministic behaviour.
4. **Path-sensitive imports** – Always import project modules (`utils`, `agents`, etc.) without manipulating `sys.path`; `conftest.py` already handles root insertion.

## 6. Adding New Tests

1. Place deterministic logic under `tests/unit/`.
2. Use `tests/integration/` for smoke / CLI / network interactions that may rely on external services.
3. Drop future full workflows into `tests/e2e/` and mark them appropriately.
4. Update this document and `Codemap.md` if you introduce new suites or helper scripts.

---

For additional historical context refer to:
- `OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md` – deep dive on environment isolation patterns.
- `ENV_CONFIG_TEST_DOCUMENTATION.md` – exhaustive breakdown of configuration-focused tests.
