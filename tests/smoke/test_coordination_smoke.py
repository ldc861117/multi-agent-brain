"""Offline smoke tests for the CoordinationAgent orchestration pipeline."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from agents.coordination.agent import CoordinationAgent
from utils.openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType

pytestmark = pytest.mark.smoke


class DummyMetrics:
    """Collect metric calls without requiring the real observability stack."""

    def __init__(self) -> None:
        self.requests: List[tuple[str, str, float]] = []
        self.retrieval_hits: List[tuple[str, int]] = []
        self.synthesis_tokens: List[tuple[str, int]] = []

    def record_request(self, agent: str, status: str, latency_seconds: float) -> None:
        self.requests.append((agent, status, float(latency_seconds)))

    def record_retrieval_hits(self, agent: str, hits: int) -> None:
        self.retrieval_hits.append((agent, int(hits)))

    def record_synthesis_tokens(self, agent: str, tokens: int) -> None:
        self.synthesis_tokens.append((agent, int(tokens)))


class DummyMemory:
    """Minimal in-memory replacement for SharedMemory."""

    def __init__(self) -> None:
        self.problem_results: List[Dict[str, Any]] = []
        self.collaboration_results: List[Dict[str, Any]] = []
        self.raise_on_search: bool = False
        self.search_calls: List[Dict[str, Any]] = []
        self.store_calls: List[Dict[str, Any]] = []

    def search_knowledge(
        self,
        collection: str,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        self.search_calls.append(
            {
                "collection": collection,
                "tenant_id": tenant_id,
                "query": query,
                "top_k": top_k,
                "threshold": threshold,
            }
        )

        if self.raise_on_search:
            raise RuntimeError("search unavailable")

        if collection == "problem_solutions":
            return list(self.problem_results)
        if collection == "collaboration_history":
            return list(self.collaboration_results)
        return []

    def store_knowledge(
        self,
        collection: str,
        tenant_id: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
        embedding: List[float] | None = None,
    ) -> int:
        self.store_calls.append(
            {
                "collection": collection,
                "tenant_id": tenant_id,
                "content": content,
                "metadata": metadata or {},
                "embedding": embedding,
            }
        )
        return len(self.store_calls)


class DummyClient:
    """LLM client stub that keeps the agent offline."""

    def __init__(self, config: OpenAIConfig | None = None) -> None:
        self.config = config

    def get_chat_completion(self, *args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
        )

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * 3 for _ in texts]


def _build_stub_config() -> OpenAIConfig:
    return OpenAIConfig(
        chat_api=ChatAPIConfig(
            api_key="stub-chat-key",
            base_url=None,
            model="stub-chat-model",
            provider=ProviderType.OPENAI,
            timeout=10,
            max_retries=0,
            retry_delay=0.1,
            max_retry_delay=0.1,
        ),
        embedding_api=EmbeddingAPIConfig(
            api_key="stub-embed-key",
            base_url=None,
            model="stub-embed-model",
            provider=ProviderType.OPENAI,
            dimension=256,
            timeout=10,
            max_retries=0,
            retry_delay=0.1,
            max_retry_delay=0.1,
        ),
    )


@pytest.fixture
def coordination_env(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    metrics = DummyMetrics()
    monkeypatch.setattr("agents.coordination.agent.metrics_registry", metrics)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", lambda *_, **__: DummyMemory())
    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", DummyClient)
    monkeypatch.setattr("agents.coordination.agent.get_agent_config", lambda _: _build_stub_config())
    monkeypatch.setattr("agents.coordination.agent.get_agent_answer_verbose", lambda _: False)
    return SimpleNamespace(metrics=metrics)


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
