"""Tests for BaseAgent legacy handle_message compatibility shim."""

from __future__ import annotations

import pytest

from agents.base import AgentResponse, BaseAgent
from agents.types import ExpertKind, Layer


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


@pytest.mark.asyncio
async def test_role_defaults_follow_expert_kind_and_layer_coercion() -> None:
    class DevOpsAgent(BaseAgent):
        name = "devops_agent"
        expert_kind = ExpertKind.DEVOPS_EXPERT
        layer = "expert"
        role = ""

        async def handle_message(self, message, conversation_state=None):
            return AgentResponse("ok", {"message": "seen"})

    agent = DevOpsAgent()

    assert agent.role == "devops_expert"
    assert agent.layer is Layer.EXPERT

    route_payload = await agent.route({"question": "status?"})
    assert route_payload["layer"] == Layer.EXPERT.value
    assert route_payload["expert_kind"] == ExpertKind.DEVOPS_EXPERT.value


@pytest.mark.asyncio
async def test_coerce_agent_response_handles_edge_cases() -> None:
    class CoercionAgent(BaseAgent):
        name = "coercion_agent"

        async def handle_message(self, message, conversation_state=None):
            return AgentResponse("ok", {})

    agent = CoercionAgent()

    tuple_response = agent._coerce_agent_response(("tuple", 42))
    assert tuple_response.content == "tuple"
    assert tuple_response.metadata == {"value": 42}

    mapping_response = agent._coerce_agent_response({"metadata": 7, "other": "data"})
    assert mapping_response.content == "{'other': 'data'}"
    assert mapping_response.metadata == {"value": 7}

    scalar_response = agent._coerce_agent_response(123)
    assert scalar_response.content == "123"
    assert scalar_response.metadata == {}
