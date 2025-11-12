"""Tests for BaseAgent legacy handle_message compatibility shim."""

from __future__ import annotations

import pytest

from agents.base import AgentResponse, BaseAgent


@pytest.mark.asyncio
async def test_sync_handle_message_converts_to_agent_response() -> None:
    class LegacyAgent(BaseAgent):
        name = "legacy_sync"

        def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            return f"legacy:{message}"

    agent = LegacyAgent()

    direct_response = await agent.handle_message("payload")
    assert isinstance(direct_response, AgentResponse)
    assert direct_response.content == "legacy:payload"
    assert direct_response.metadata == {}

    act_response = await agent.act("payload")
    assert isinstance(act_response, AgentResponse)
    assert act_response.content == "legacy:payload"
    assert act_response.metadata == {}


@pytest.mark.asyncio
async def test_tuple_and_mapping_payloads_are_coerced() -> None:
    class TupleAgent(BaseAgent):
        name = "tuple_agent"

        def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            return ("tuple-response", {"source": "tuple"})

    class MappingAgent(BaseAgent):
        name = "mapping_agent"

        def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            return {"content": "mapping-response", "metadata": {"source": "mapping"}}

    tuple_agent = TupleAgent()
    mapping_agent = MappingAgent()

    tuple_response = await tuple_agent.handle_message("ignored")
    assert tuple_response.content == "tuple-response"
    assert tuple_response.metadata == {"source": "tuple"}

    mapping_response = await mapping_agent.handle_message("ignored")
    assert mapping_response.content == "mapping-response"
    assert mapping_response.metadata == {"source": "mapping"}


@pytest.mark.asyncio
async def test_none_payload_defaults_to_empty_response() -> None:
    class NoneAgent(BaseAgent):
        name = "none_agent"

        def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            return None

    agent = NoneAgent()
    response = await agent.handle_message("unused")
    assert response.content == ""
    assert response.metadata == {}
