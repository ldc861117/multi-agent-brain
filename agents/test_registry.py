from __future__ import annotations

from typing import Any, Dict

import pytest

from agents.base import AgentResponse, BaseAgent
from agents.coordination import CoordinationAgent
from agents.milvus_expert import MilvusExpertAgent
from agents.python_expert import PythonExpertAgent
from agents.registry import ExpertRegistry, bootstrap_registry
from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer


class DummyExpertAgent(BaseAgent):
    name = "dummy_expert"
    description = "Handles dummy capability for tests."
    layer = Layer.EXPERT
    expert_kind = ExpertKind.PYTHON_EXPERT
    capabilities = AgentCapabilities(
        primary=(
            CapabilityDescriptor(
                name="dummy_capability",
                description="Perform dummy operations.",
                outputs=("result",),
                tags=("dummy", "test"),
            ),
        )
    )

    async def handle_message(self, message: Any, conversation_state: Any = None) -> AgentResponse:  # type: ignore[override]
        return AgentResponse(content="dummy-response", metadata={"message": message})


def test_register_and_lookup_aliases() -> None:
    registry = ExpertRegistry()
    registry.register("dummy_expert", agent_cls=DummyExpertAgent, aliases=("dummy",))

    canonical = registry.get("dummy_expert")
    assert canonical is not None
    assert canonical.layer is Layer.EXPERT

    alias_entry = registry.get("dummy")
    assert alias_entry is canonical
    assert alias_entry.has_capability("dummy_capability")
    assert "dummy" in alias_entry.capabilities

    matches = registry.select_by_capability("dummy_capability")
    assert matches and matches[0].name == "dummy_expert"


def test_enable_disable_affects_selection() -> None:
    registry = ExpertRegistry()
    registry.register("dummy_expert", agent_cls=DummyExpertAgent, aliases=("dummy",))

    assert registry.select_by_capability("dummy_capability")
    registry.disable("dummy")
    assert registry.select_by_capability("dummy_capability") == ()
    disabled_entries = registry.list(include_disabled=True)
    assert disabled_entries and not disabled_entries[0].enabled

    registry.enable("dummy")
    assert registry.select_by_capability("dummy_capability")


def test_registry_list_filters() -> None:
    registry = ExpertRegistry()
    registry.register(
        "coordination",
        agent_cls=DummyExpertAgent,
        aliases=("router",),
        layer=Layer.COORDINATION,
        expert_kind=ExpertKind.COORDINATION,
        capabilities=("routing", "analysis"),
    )
    registry.register(
        "support",
        agent_cls=DummyExpertAgent,
        layer=Layer.SUPPORT,
        expert_kind=ExpertKind.SUPPORT,
        aliases=("helper",),
    )

    coord_entries = registry.list(layer=Layer.COORDINATION)
    assert len(coord_entries) == 1
    assert coord_entries[0].name == "coordination"

    support_entries = registry.list(expert_kind=ExpertKind.COORDINATION)
    assert support_entries and support_entries[0].name == "coordination"

    capability_matches = registry.list(capabilities=("routing",))
    assert capability_matches and capability_matches[0].name == "coordination"


def test_healthcheck_invocation() -> None:
    registry = ExpertRegistry()
    registry.register(
        "health_agent",
        agent_cls=DummyExpertAgent,
        aliases=("health",),
        healthcheck=lambda: {"status": "ok", "detail": "healthy"},
    )

    status = registry.run_healthcheck("health")
    assert status["status"] == "ok"
    assert status["detail"] == "healthy"

    unknown = registry.run_healthcheck("unknown")
    assert unknown["status"] == "unknown"


def test_bootstrap_registry_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ExpertRegistry()

    class FakeConfigManager:
        def get_registry_bootstrap(self) -> Dict[str, Dict[str, Any]]:
            return {
                "python_expert": {
                    "entrypoint": "agents.python_expert:PythonExpertAgent",
                    "aliases": ["python"],
                },
                "devops_expert": {
                    "entrypoint": "agents.devops_expert:DevOpsExpertAgent",
                    "aliases": ["devops"],
                    "enabled": False,
                },
            }

    bootstrap_registry(registry=registry, config_manager=FakeConfigManager(), reset=True)

    python_entry = registry.get("python")
    assert python_entry is not None
    assert python_entry.agent_cls is PythonExpertAgent

    devops_entry = registry.get("devops")
    assert devops_entry is not None
    assert not devops_entry.enabled


@pytest.mark.asyncio
async def test_coordination_agent_respects_disabled_experts(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = ExpertRegistry()
    registry.register(
        "python_expert",
        agent_cls=PythonExpertAgent,
        aliases=("python",),
    )
    registry.register(
        "milvus_expert",
        agent_cls=MilvusExpertAgent,
        aliases=("milvus",),
    )
    registry.disable("python")

    class DummyClient:
        def __init__(self, *_, **__):
            self.created = True

        def get_chat_completion(self, *_, **__):  # pragma: no cover - defensive stub
            class DummyChoice:
                message = type("Msg", (), {"content": "stub"})

            return type("Resp", (), {"choices": [DummyChoice()]})

    class DummyMemory:
        def __init__(self, *args, **kwargs):
            self.agent_name = kwargs.get("agent_name") or (args[0] if args else None)

        def search_knowledge(self, *_, **__):
            return []

        def store_knowledge(self, *_, **__):  # pragma: no cover - defensive stub
            return None

    async def fake_get_expert_response(self, expert: str, task_message: Dict[str, Any]) -> str:  # type: ignore[override]
        return f"response-from-{expert}"

    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", DummyClient)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", DummyMemory)
    monkeypatch.setattr("agents.coordination.agent.get_expert_registry", lambda: registry)
    monkeypatch.setattr(CoordinationAgent, "_get_expert_response", fake_get_expert_response)

    agent = CoordinationAgent()

    analysis = {"required_experts": ["python", "milvus"]}
    dispatch_result = await agent.dispatch_to_experts(
        question="How do I structure Milvus indexes?",
        analysis=analysis,
        similar_knowledge=[],
    )

    assert "python" not in dispatch_result["expert_responses"]
    assert "milvus" in dispatch_result["expert_responses"]
    assert dispatch_result["registry_entries"]
    assert "python" not in dispatch_result["registry_entries"]
    assert dispatch_result["skipped_registry_experts"]
    assert analysis["required_experts"] == ["milvus"]

    # Ensure the disabled expert remained disabled in the registry
    assert not registry.get("python").enabled  # type: ignore[union-attr]
