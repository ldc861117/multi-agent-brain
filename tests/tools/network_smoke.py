#!/usr/bin/env python3
"""网络 API 冒烟测试工具。

该模块在本地或 CI 环境中执行一次 API 交互流程：注册 → 发送消息 → 注销。
导入本模块不会产生任何副作用，可作为测试工具在其他脚本中复用。

English summary: helper utilities for running a register/send/unregister smoke
check against the OpenAgents HTTP API.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

import requests

DEFAULT_BASE_URL = "http://localhost:8700/api"
REGISTER_PATH = "/register"
SEND_EVENT_PATH = "/send_event"
UNREGISTER_PATH = "/unregister"


@dataclass
class SmokeTestResult:
    """Structured result describing the smoke test interaction."""

    agent_id: str
    secret: str
    event_payload: Dict[str, Any]
    response_json: Dict[str, Any]
    unregister_response: Optional[Dict[str, Any]]


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"  # pragma: no cover - trivial helper


def register_agent(agent_id: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0) -> str:
    """Register the agent and return the issued secret."""

    response = requests.post(
        _url(base_url, REGISTER_PATH),
        json={"agent_id": agent_id},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("success"):
        raise RuntimeError(payload.get("error_message", "registration failed"))

    secret = payload.get("secret")
    if not secret:
        raise RuntimeError("registration succeeded but no secret was returned")

    return str(secret)


def send_message(
    agent_id: str,
    secret: str,
    message_text: str,
    target_channel: str = "general",
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 30.0,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Send a message event and return the payload plus response JSON."""

    event_payload: Dict[str, Any] = {
        "event_id": f"event-{uuid.uuid4()}",
        "event_name": "user.message",
        "source_id": agent_id,
        "target_agent_id": target_channel,
        "payload": {"text": message_text},
        "metadata": {},
        "secret": secret,
    }

    response = requests.post(
        _url(base_url, SEND_EVENT_PATH),
        headers={"Content-Type": "application/json"},
        json=event_payload,
        timeout=timeout,
    )
    response.raise_for_status()

    return event_payload, response.json()


def unregister_agent(
    agent_id: str,
    secret: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Unregister the agent; errors propagate for visibility."""

    response = requests.post(
        _url(base_url, UNREGISTER_PATH),
        json={"agent_id": agent_id, "secret": secret},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def run_smoke_test(
    message_text: str,
    target_channel: str = "general",
    base_url: str = DEFAULT_BASE_URL,
) -> SmokeTestResult:
    """Execute the full smoke test workflow."""

    agent_id = f"network-smoke-{uuid.uuid4()}"
    secret = register_agent(agent_id, base_url=base_url)

    event_payload: Dict[str, Any] = {}
    response_json: Dict[str, Any] = {}
    unregister_response: Optional[Dict[str, Any]] = None

    try:
        event_payload, response_json = send_message(
            agent_id,
            secret,
            message_text,
            target_channel=target_channel,
            base_url=base_url,
        )
    finally:
        try:
            unregister_response = unregister_agent(agent_id, secret, base_url=base_url)
        except requests.exceptions.RequestException:
            unregister_response = None

    return SmokeTestResult(
        agent_id=agent_id,
        secret=secret,
        event_payload=event_payload,
        response_json=response_json,
        unregister_response=unregister_response,
    )


def _format_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-Agent Brain network smoke test")
    parser.add_argument("message", nargs="?", default="What is Milvus?", help="user message to send")
    parser.add_argument("--channel", default="general", help="target channel (default: general)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the OpenAgents HTTP API")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output; still exits non-zero on failure",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_smoke_test(
            message_text=args.message,
            target_channel=args.channel,
            base_url=args.base_url,
        )
    except requests.exceptions.RequestException as exc:  # pragma: no cover - network dependent
        print(f"❌ Request error: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"❌ Smoke test failed: {exc}")
        return 1

    if not args.quiet:
        print("=== Smoke Test Summary ===")
        print(f"Agent ID: {result.agent_id}")
        print(f"Target Channel: {args.channel}")
        if result.event_payload:
            print("\n--- Sent Payload ---")
            print(_format_json(result.event_payload))
        if result.response_json:
            print("\n--- Network Response ---")
            print(_format_json(result.response_json))
        if result.unregister_response is not None:
            print("\n--- Unregister Response ---")
            print(_format_json(result.unregister_response))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
