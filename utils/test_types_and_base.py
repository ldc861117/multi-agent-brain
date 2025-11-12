from __future__ import annotations

import pytest

from agents.base import AgentResponse, BaseAgent, BaseAgentProtocol
from agents.coordination import CoordinationAgent
from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer


def test_layer_roundtrip_and_fallback() -> None:
    assert Layer.coerce("entry") is Layer.ENTRY
    assert Layer.from_value("coordination") is Layer.COORDINATION
    assert Layer.coerce(Layer.EXPERT) is Layer.EXPERT
    assert Layer.coerce("made-up") is Layer.UNKNOWN


def test_expert_kind_roundtrip_and_aliases() -> None:
    assert ExpertKind.coerce("python_expert") is ExpertKind.PYTHON_EXPERT
    assert ExpertKind.coerce("python") is ExpertKind.PYTHON_EXPERT
    assert ExpertKind.coerce("general") is ExpertKind.GENERAL
    assert ExpertKind.coerce("unsupported-agent") is ExpertKind.UNKNOWN


def test_agent_capabilities_all_view() -> None:
    analysis = CapabilityDescriptor(
        name="analysis",
        description="Understand incoming requests.",
        outputs=("analysis",),
    )
    synthesis = CapabilityDescriptor(
        name="synthesis",
        description="Merge outputs into a unified response.",
        outputs=("answer",),
    )
    capabilities = AgentCapabilities(primary=(analysis,), auxiliary=(synthesis,))

    assert capabilities.all_capabilities() == (analysis, synthesis)
    assert list(capabilities) == [analysis, synthesis]


@pytest.mark.asyncio
async def test_base_agent_act_delegates_to_handle_message() -> None:
    class LegacyEchoAgent(BaseAgent):
        async def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            payload = ""
            if isinstance(message, dict) and message.get("content"):
                payload = str(message["content"])
            else:
                payload = str(message)
            return AgentResponse(content=f"echo:{payload}")

    agent = LegacyEchoAgent()

    response = await agent.act({"content": "hello"})
    assert response.content == "echo:hello"
    assert response.metadata == {}

    plan = await agent.plan({})
    assert plan["status"] == "noop"

    reflection = await agent.reflect({}, response)
    assert reflection["status"] == "noop"

    route = await agent.route({})
    assert route["layer"] == Layer.UNKNOWN.value
    assert isinstance(agent, BaseAgentProtocol)


@pytest.mark.asyncio
async def test_string_configuration_is_coerced() -> None:
    class StringConfiguredAgent(BaseAgent):
        layer = "coordination"
        expert_kind = "python"

        async def handle_message(self, message, conversation_state=None):  # type: ignore[override]
            return AgentResponse(content="ok")

    agent = StringConfiguredAgent()

    assert agent.layer is Layer.COORDINATION
    assert agent.expert_kind is ExpertKind.PYTHON_EXPERT


def test_coordination_agent_instantiates_with_hierarchy(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        def __init__(self, *_, **__):
            self.created = True

    class DummyMemory:
        def __init__(self, *args, **kwargs):
            self.agent_name = kwargs.get("agent_name") or (args[0] if args else None)

        def health_check(self):  # pragma: no cover - defensive stub
            return {"status": "ok"}

    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", DummyClient)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", DummyMemory)
    monkeypatch.setattr("agents.coordination.agent.get_agent_config", lambda *_: {"model": "stub"})
    monkeypatch.setattr("agents.coordination.agent.get_agent_answer_verbose", lambda *_: False)

    agent = CoordinationAgent()

    assert agent.layer is Layer.COORDINATION
    assert agent.expert_kind is ExpertKind.COORDINATION
    capabilities = agent.capabilities.all_capabilities()
    assert len(capabilities) >= 2
    assert all(descriptor.description for descriptor in capabilities)
