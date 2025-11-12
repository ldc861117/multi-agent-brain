"""Reusable test doubles for offline agent testing."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from agents.base import AgentResponse, BaseAgent
from agents.devops_expert import DevOpsExpertAgent
from agents.milvus_expert import MilvusExpertAgent
from agents.python_expert import PythonExpertAgent
from agents.registry import ExpertRegistry
from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer
from utils.openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType


class DummyMetrics:
    """Collect metrics invocations without relying on observability stack."""

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


class FakeOpenAIClient:
    """Minimal LLM stub returning deterministic responses."""

    def __init__(self, responses: Optional[Iterable[str]] = None, **_: Any) -> None:
        self.responses: List[str] = list(responses or [])
        self.requests: List[Dict[str, Any]] = []
        self.embedding_requests: List[Sequence[str]] = []

    def get_chat_completion(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.requests.append({"args": args, "kwargs": kwargs})
        if self.responses:
            content = self.responses.pop(0)
        else:
            content = "{}"
        usage = SimpleNamespace(total_tokens=len(content))
        choice = SimpleNamespace(message=SimpleNamespace(content=content))
        return SimpleNamespace(choices=[choice], usage=usage)

    def get_embeddings_batch(self, texts: Sequence[str]) -> List[List[float]]:
        self.embedding_requests.append(tuple(texts))
        return [[0.0] * 3 for _ in texts]


class FakeSharedMemory:
    """In-memory stub for SharedMemory interactions."""

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
        metadata: Optional[Mapping[str, Any]] = None,
        embedding: Optional[Sequence[float]] = None,
    ) -> int:
        payload = {
            "collection": collection,
            "tenant_id": tenant_id,
            "content": dict(content),
            "metadata": dict(metadata or {}),
            "embedding": list(embedding) if embedding is not None else None,
        }
        self.store_calls.append(payload)
        return len(self.store_calls)


class DummyEchoAgent(BaseAgent):
    """Lightweight agent for registry-driven tests."""

    name = "dummy_expert"
    description = "Returns echo responses for testing dispatch flows."
    layer = Layer.EXPERT
    expert_kind = ExpertKind.PYTHON_EXPERT
    capabilities = AgentCapabilities(
        primary=(
            CapabilityDescriptor(
                name="dummy_capability",
                description="Echoes question text for verification.",
                outputs=("echo",),
                tags=("dummy",),
            ),
        )
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        question = ""
        if isinstance(message, Mapping):
            question = str(message.get("question") or message.get("text") or "")
        else:
            question = str(message)
        return AgentResponse(
            content=f"echo:{question}",
            metadata={"agent": self.name},
        )


def build_stub_openai_config() -> OpenAIConfig:
    """Return a deterministic OpenAIConfig for use in tests."""

    chat_config = ChatAPIConfig(
        api_key="stub-chat-key",
        base_url=None,
        model="stub-chat-model",
        provider=ProviderType.OPENAI,
        timeout=10,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=0.1,
    )
    embedding_config = EmbeddingAPIConfig(
        api_key="stub-embed-key",
        base_url=None,
        model="stub-embed-model",
        provider=ProviderType.OPENAI,
        dimension=128,
        timeout=10,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=0.1,
    )
    return OpenAIConfig(chat_api=chat_config, embedding_api=embedding_config)


def build_fake_registry(include_dummy: bool = False) -> ExpertRegistry:
    """Construct an ExpertRegistry populated with core scaffold agents."""

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
    registry.register(
        "devops_expert",
        agent_cls=DevOpsExpertAgent,
        aliases=("devops",),
    )
    if include_dummy:
        registry.register(
            "dummy_expert",
            agent_cls=DummyEchoAgent,
            aliases=("dummy",),
        )
    return registry


__all__ = [
    "DummyEchoAgent",
    "DummyMetrics",
    "FakeOpenAIClient",
    "FakeSharedMemory",
    "build_fake_registry",
    "build_stub_openai_config",
]
