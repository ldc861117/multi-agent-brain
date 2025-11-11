# ADR 2024-11-11: OpenAI Client Testing Isolation

## Status
Accepted

## Context
Rewriting the OpenAI client tests revealed sporadic failures caused by environment leakage and `.env` side effects. The existing test harness relied on `patch.dict`, which did not fully clean sensitive variables or prevent `dotenv.load_dotenv()` from populating values during collection.

## Decision
- Adopt pytest fixtures (`clean_env`, `mock_load_dotenv`) built on `pytest.MonkeyPatch` to guarantee deterministic environment state across tests.
- Provide reusable configuration fixtures (`openai_config_default`, `openai_config_custom`) to centralise baseline expectations.
- Enforce automatic cleanup with an `autouse=True` fixture that resets global state after each test class.
- Document precedence rules and fallback behaviour alongside the tests to keep configuration and runtime behaviour aligned.

## Consequences
- Tests can now run in any environment without inheriting developer-specific `.env` files.
- Future environment-related tests should reuse the fixture patterns instead of hand-crafted `patch.dict` blocks.
- The configuration guide references these patterns to help developers diagnose misconfigurations quickly.

## References
- [Testing Reference](../testing/README.md)
- [Archive: OPENAI_CLIENT_TEST_REWRITE_SUMMARY](../archive/OPENAI_CLIENT_TEST_REWRITE_SUMMARY.md)
- [Archive: ENV_CONFIG_TEST_DOCUMENTATION](../archive/ENV_CONFIG_TEST_DOCUMENTATION.md)
