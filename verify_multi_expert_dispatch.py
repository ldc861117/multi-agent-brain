#!/usr/bin/env python3
"""Verification harness for multi-expert routing and synthesis.

This script exercises the CoordinationAgent with representative questions and
verifies that:

1. Different question types engage the appropriate domain experts
2. Expert contributions surface in the synthesized answer
3. Collaboration history persists expert attribution metadata

The harness stubs external dependencies (LLM + Milvus) so it can run in offline
environments yet still validate routing behaviour after the new heuristic
fallbacks were introduced.
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set
from types import SimpleNamespace
from unittest.mock import patch

from loguru import logger

from agents.coordination import CoordinationAgent


@dataclass
class VerificationCase:
    """Represents a routing verification scenario."""

    question: str
    expected_experts: Set[str]
    description: str
    minimum_experts: int = 1


class StubOpenAIClientWrapper:
    """OpenAI client stub that forces heuristic fallbacks."""

    def __init__(self, config: Any):
        self.config = config

    def get_chat_completion(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - always raises
        raise RuntimeError("LLM unavailable for verification harness")

    def get_embedding_vector(
        self, text: str, model_override: Optional[str] = None
    ) -> Sequence[Sequence[float]]:  # pragma: no cover - deterministic stub
        dimension = getattr(getattr(self.config, "embedding_api", None), "dimension", 1536)
        return [[0.0 for _ in range(dimension)]]


class InMemorySharedMemory:
    """Minimal SharedMemory stub that records collaboration metadata."""

    COLLECTION_COLLABORATION_HISTORY = "collaboration_history"
    COLLECTION_PROBLEM_SOLUTIONS = "problem_solutions"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.records: Dict[str, List[Dict[str, Any]]] = {
            self.COLLECTION_COLLABORATION_HISTORY: [],
            self.COLLECTION_PROBLEM_SOLUTIONS: [],
        }

    # --- API surface used by CoordinationAgent ---
    def search_knowledge(
        self,
        collection: str,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        return []

    def store_knowledge(
        self,
        collection: str,
        tenant_id: str,
        content: Mapping[str, Any],
        metadata: Optional[Mapping[str, Any]] = None,
        embedding: Optional[Sequence[float]] = None,
    ) -> int:
        stored = {
            "tenant_id": tenant_id,
            "content": dict(content),
            "metadata": dict(metadata or {}),
        }
        self.records.setdefault(collection, []).append(stored)
        return len(self.records[collection])

    def get_collection_stats(self, collection: str, tenant_id: str) -> Dict[str, Any]:
        matching = [
            item
            for item in self.records.get(collection, [])
            if item.get("tenant_id") == tenant_id
        ]
        return {
            "total_records": len(matching),
            "tenant_id": tenant_id,
        }

    def health_check(self) -> Dict[str, Any]:
        return {"milvus_connected": True}


def build_dummy_config() -> Any:
    """Construct configuration namespace expected by CoordinationAgent."""

    chat_api = SimpleNamespace(
        api_key="dummy-key",
        base_url=None,
        model="stub-chat",
        provider="custom",
        timeout=5,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=1.0,
    )
    embedding_api = SimpleNamespace(
        api_key=None,
        base_url=None,
        model="stub-embed",
        provider="custom",
        dimension=1536,
        timeout=5,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=1.0,
    )
    return SimpleNamespace(chat_api=chat_api, embedding_api=embedding_api)


TEST_CASES: List[VerificationCase] = [
    VerificationCase(
        question="How to optimize Milvus query performance?",
        expected_experts={"milvus", "python"},
        description="Milvus tuning should route to Milvus (and Python for client guidance).",
        minimum_experts=2,
    ),
    VerificationCase(
        question="What are best practices for Python async/await?",
        expected_experts={"python"},
        description="Python concurrency should stay with the Python expert.",
        minimum_experts=1,
    ),
    VerificationCase(
        question="How to set up CI/CD pipeline?",
        expected_experts={"devops"},
        description="CI/CD requests must engage the DevOps expert.",
        minimum_experts=1,
    ),
    VerificationCase(
        question="Compare vector database options for embeddings",
        expected_experts={"milvus"},
        description="Cross-domain comparison should include multiple experts with Milvus involved.",
        minimum_experts=2,
    ),
]


async def run_verification() -> None:
    """Execute verification workflow and report results."""

    dummy_config = build_dummy_config()

    with ExitStack() as stack:
        stack.enter_context(
            patch("agents.coordination.agent.get_agent_config", return_value=dummy_config)
        )
        stack.enter_context(
            patch("agents.coordination.agent.OpenAIClientWrapper", StubOpenAIClientWrapper)
        )
        stack.enter_context(patch("agents.coordination.agent.SharedMemory", InMemorySharedMemory))

        agent = CoordinationAgent()
        memory: InMemorySharedMemory = agent.memory  # type: ignore[assignment]

        overall_passed = True
        for case in TEST_CASES:
            logger.info(f"Evaluating: {case.question}")
            response = await agent.handle_message(
                {
                    "content": {"text": case.question},
                    "tenant_id": "verification",
                }
            )

            experts = set(response.metadata.get("experts_involved", []))
            if not case.expected_experts.issubset(experts):
                logger.error(
                    "Expected experts missing",
                    extra={
                        "question": case.question,
                        "expected": sorted(case.expected_experts),
                        "actual": sorted(experts),
                    },
                )
                overall_passed = False

            if len(experts) < case.minimum_experts:
                logger.error(
                    "Not enough experts involved",
                    extra={
                        "question": case.question,
                        "minimum": case.minimum_experts,
                        "actual": len(experts),
                    },
                )
                overall_passed = False

            answer = response.content or ""
            for expert in experts:
                marker = f"{expert.upper()} EXPERT"
                if marker not in answer.upper():
                    logger.error(
                        "Expert response missing from final answer",
                        extra={"question": case.question, "expert": expert},
                    )
                    overall_passed = False

        collab_records = memory.records.get(memory.COLLECTION_COLLABORATION_HISTORY, [])
        for case in TEST_CASES:
            record = next(
                (
                    item
                    for item in collab_records
                    if item.get("content", {}).get("task_description") == case.question
                ),
                None,
            )
            if record is None:
                logger.error(
                    "Collaboration history missing entry",
                    extra={"question": case.question},
                )
                overall_passed = False
                continue

            participants_raw = record.get("content", {}).get("participating_agents", "")
            participants = {chunk.strip() for chunk in participants_raw.split(",") if chunk.strip()}
            if not case.expected_experts.issubset(participants):
                logger.error(
                    "Collaboration history missing expected experts",
                    extra={
                        "question": case.question,
                        "expected": sorted(case.expected_experts),
                        "stored": sorted(participants),
                    },
                )
                overall_passed = False

        if overall_passed:
            logger.success("✅ Multi-expert dispatch verification passed")
        else:
            raise SystemExit("❌ Multi-expert dispatch verification failed")


def main() -> None:
    asyncio.run(run_verification())


if __name__ == "__main__":
    main()
