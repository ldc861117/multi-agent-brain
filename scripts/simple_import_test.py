#!/usr/bin/env python3
"""Sanity checks for core utils imports."""

def check_imports() -> int:
    status = 0

    try:
        from utils.openai_client import (  # type: ignore  # local import for side effects
            ChatAPIConfig,
            EmbeddingAPIConfig,
            OpenAIConfig,
            OpenAIClientWrapper,
            ProviderType,
        )
        print("OpenAI client imports: OK")
    except Exception as exc:  # pragma: no cover - dev-only helper
        print(f"OpenAI client imports failed: {exc}")
        status = 1

    try:
        from utils.config_manager import ConfigManager, get_agent_config  # type: ignore
        print("Config manager imports: OK")
    except Exception as exc:  # pragma: no cover - dev-only helper
        print(f"Config manager imports failed: {exc}")
        status = 1

    return status


def main() -> int:
    additional_status = 0
    try:
        from utils import get_agent_config, OpenAIClientWrapper  # type: ignore
        _ = (get_agent_config, OpenAIClientWrapper)
        print("utils exports: OK")
    except Exception as exc:  # pragma: no cover - dev-only helper
        print(f"Utils exports failed: {exc}")
        additional_status = 1

    return max(check_imports(), additional_status)


if __name__ == "__main__":
    raise SystemExit(main())
