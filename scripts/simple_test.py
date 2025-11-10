#!/usr/bin/env python3
"""Simple scripted interaction with the OpenAgents HTTP network."""

from __future__ import annotations

import json
import uuid
from typing import Any

import requests

BASE_URL = "http://localhost:8700/api"
REGISTER_URL = f"{BASE_URL}/register"
SEND_EVENT_URL = f"{BASE_URL}/send_event"
UNREGISTER_URL = f"{BASE_URL}/unregister"


def register() -> tuple[str, str | None]:
    agent_id = f"simple-test-script-{uuid.uuid4()}"
    print(f"--- 1. Registering Agent '{agent_id}' ---")
    try:
        reg_response = requests.post(REGISTER_URL, json={"agent_id": agent_id}, timeout=10)
        reg_response.raise_for_status()
        reg_data: dict[str, Any] = reg_response.json()
    except requests.exceptions.RequestException as exc:
        print(f"❌ Error during registration: {exc}")
        return agent_id, None

    if not reg_data.get("success"):
        print(f"❌ Registration failed: {reg_data.get('error_message', 'Unknown error')}")
        return agent_id, None

    secret = reg_data.get("secret")
    if not secret:
        print("❌ Registration successful, but no secret was provided.")
        return agent_id, None

    print("✅ Registration successful. Got secret.")
    return agent_id, secret


def send_message(agent_id: str, secret: str) -> None:
    print("\n--- 2. Sending Message ---")

    event_payload = {
        "event_id": f"event-{uuid.uuid4()}",
        "event_name": "user.message",
        "source_id": agent_id,
        "target_agent_id": "general",
        "payload": {"text": "What is Milvus?"},
        "metadata": {},
        "secret": secret,
    }

    print("Payload:")
    print(json.dumps(event_payload, indent=2))

    try:
        response = requests.post(
            SEND_EVENT_URL,
            headers={"Content-Type": "application/json"},
            json=event_payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"\n--- Error ---\nAn error occurred while sending the message: {exc}")
        return

    print("\n--- Agent Network Response ---")
    print(f"Status Code: {response.status_code}")
    response_json: dict[str, Any] = response.json()
    print("Response JSON:")
    print(json.dumps(response_json, indent=2))

    if response_json.get("data"):
        print("\n--- Agent's Reply ---")
        print(json.dumps(response_json["data"], indent=2))
    else:
        print(f"\nNo direct agent reply in 'data' field. Message: {response_json.get('message')}")


def unregister(agent_id: str, secret: str | None) -> None:
    if not secret:
        return

    print(f"\n--- 3. Unregistering Agent '{agent_id}' ---")
    try:
        unreg_response = requests.post(
            UNREGISTER_URL,
            json={"agent_id": agent_id, "secret": secret},
            timeout=10,
        )
        unreg_response.raise_for_status()
        payload: dict[str, Any] = unreg_response.json()
    except requests.exceptions.RequestException as exc:
        print(f"❌ Error during unregistration: {exc}")
        return

    if payload.get("success"):
        print("✅ Unregistration successful.")
    else:
        print(f"⚠️ Unregistration failed: {payload.get('error_message')}")


def main() -> int:
    agent_id, secret = register()
    if not secret:
        return 1

    try:
        send_message(agent_id, secret)
    finally:
        unregister(agent_id, secret)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
