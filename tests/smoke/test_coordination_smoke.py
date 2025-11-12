"""Offline smoke tests for the CoordinationAgent orchestration pipeline."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents.coordination.agent import CoordinationAgent

pytestmark = pytest.mark.smoke


@pytest.fixture
def coordination_env(
    monkeypatch: pytest.MonkeyPatch,
    fake_openai_client_class,
    fake_shared_memory,
    fake_registry,
    dummy_metrics,
    stub_agent_settings,
) -> SimpleNamespace:
    metrics = dummy_metrics
    memory = fake_shared_memory
    config = stub_agent_settings

    monkeypatch.setattr("agents.coordination.agent.metrics_registry", metrics)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", lambda *_, **__: memory)
    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", fake_openai_client_class)
    monkeypatch.setattr("agents.coordination.agent.get_agent_config", lambda _: config)
    monkeypatch.setattr("agents.coordination.agent.get_agent_answer_verbose", lambda _: False)
    monkeypatch.setattr("agents.coordination.agent.get_expert_registry", lambda: fake_registry)

    return SimpleNamespace(metrics=metrics, memory=memory, registry=fake_registry, config=config)


@pytest.mark.asyncio
async def test_coordination_handle_message_happy_path(coordination_env: SimpleNamespace) -> None:
    agent = CoordinationAgent()
    agent.memory.problem_results = [
        {"content": "cached answer", "similarity_score": 0.92}
    ]
    agent.memory.collaboration_results = [
        {"content": "collaboration trace", "similarity_score": 0.81}
    ]

    agent.analyze_question = lambda question: {
        "required_experts": ["python"],
        "complexity": "simple",
        "summary": "analysis-stub",
    }

    async def fake_dispatch(question, analysis, similar, tenant_id):
        return {
            "status": "success",
            "expert_responses": {"python": "Use pathlib for deterministic file I/O."},
            "interaction_id": "interaction-123",
            "correlation_id": "corr-123",
        }

    async def fake_synthesize(question, analysis, responses, tenant_id, verbose):
        return (
            "Synthesized answer with sufficient detail to exceed the fifty character "
            "threshold and verify collaboration storage."
        )

    agent.dispatch_to_experts = fake_dispatch  # type: ignore[assignment]
    agent.synthesize_answer = fake_synthesize  # type: ignore[assignment]

    response = await agent.handle_message(
        {
            "id": "message-1",
            "tenant_id": "test-tenant",
            "text": "How should I structure offline smoke tests?",
        }
    )

    assert response.content.startswith("Synthesized answer")
    assert response.metadata["interaction_id"] == "interaction-123"
    assert response.metadata["experts_involved"] == ["python"]
    assert response.metadata["correlation_id"] == "corr-123"
    assert response.metadata["knowledge_used"] is True

    stored_collections = {call["collection"] for call in agent.memory.store_calls}
    assert stored_collections == {"collaboration_history", "problem_solutions"}

    assert coordination_env.metrics.requests
    last_request = coordination_env.metrics.requests[-1]
    assert last_request[0] == "coordination"
    assert last_request[1] == "success"


@pytest.mark.asyncio
async def test_retrieve_similar_knowledge_returns_empty_on_failure(coordination_env: SimpleNamespace) -> None:
    agent = CoordinationAgent()
    agent.memory.raise_on_search = True

    results = await agent.retrieve_similar_knowledge("Explain caching behavior", tenant_id="tenant-99")

    assert results == []


@pytest.mark.asyncio
async def test_coordination_handles_missing_registry(
    monkeypatch: pytest.MonkeyPatch, coordination_env: SimpleNamespace
) -> None:
    def _raise_registry():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr("agents.coordination.agent.get_expert_registry", _raise_registry)

    agent = CoordinationAgent()
    assert agent.registry is None
