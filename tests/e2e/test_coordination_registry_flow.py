"""End-to-end smoke tests for CoordinationAgent registry dispatch."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.coordination import CoordinationAgent
from agents.base import AgentResponse


@pytest.mark.asyncio
async def test_coordination_registry_dispatch_flow(
    monkeypatch: pytest.MonkeyPatch,
    fake_openai_client_class,
    fake_shared_memory,
    fake_registry,
    dummy_metrics,
    stub_agent_settings,
) -> None:
    """Ensure coordination → registry → expert execution works offline."""

    metrics = dummy_metrics
    memory = fake_shared_memory
    registry = fake_registry
    config = stub_agent_settings

    memory.problem_results = [
        {
            "problem": "Existing guidance",
            "solution": "Use dependency injection for testability.",
            "similarity_score": 0.87,
        }
    ]

    monkeypatch.setattr("agents.coordination.agent.metrics_registry", metrics)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", lambda *_, **__: memory)
    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", fake_openai_client_class)
    monkeypatch.setattr("agents.coordination.agent.get_agent_config", lambda _: config)
    monkeypatch.setattr("agents.coordination.agent.get_agent_answer_verbose", lambda _: False)
    monkeypatch.setattr("agents.coordination.agent.get_expert_registry", lambda: registry)

    async def synthesize_stub(
        self: CoordinationAgent,
        question: str,
        analysis,
        expert_responses,
        tenant_id: str = "default",
        verbose: bool | None = None,
    ) -> str:
        return (
            "This synthesized answer aggregates expert input and intentionally exceeds "
            "fifty characters to trigger collaboration persistence paths."
        )

    async def registry_backed_response(
        self: CoordinationAgent, expert: str, task_message: dict
    ) -> str:
        entry = self.registry.get(expert)
        assert entry is not None, f"expert {expert} missing from registry"
        instance = entry.create_instance()
        response = await instance.handle_message(task_message)
        assert isinstance(response, AgentResponse)
        return response.content

    monkeypatch.setattr(CoordinationAgent, "synthesize_answer", synthesize_stub, raising=False)
    monkeypatch.setattr(CoordinationAgent, "_get_expert_response", registry_backed_response, raising=False)

    agent = CoordinationAgent()
    agent.analyze_question = lambda question: {  # type: ignore[assignment]
        "required_experts": ["python"],
        "complexity": "simple",
        "keywords": ["python"],
        "reasoning": "stub-analysis",
    }

    message = {
        "id": "msg-1",
        "tenant_id": "tenant-42",
        "text": "How should I structure a Python coordination test harness?",
    }

    response = await agent.handle_message(message)

    assert response.metadata["experts_involved"] == ["python"]
    assert response.metadata["knowledge_used"] is True
    assert response.content.startswith("This synthesized answer")

    assert metrics.requests
    agent_name, status, _ = metrics.requests[-1]
    assert agent_name == "coordination"
    assert status == "success"

    assert any(call["collection"] == "collaboration_history" for call in memory.store_calls)
    assert any(call["collection"] == "problem_solutions" for call in memory.store_calls)

    assert agent.active_collaborations
    active_state = SimpleNamespace(**next(iter(agent.active_collaborations.values())))
    assert "registry_entries" in active_state.__dict__
    assert "python" in active_state.registry_entries
