"""End-to-end hierarchy flow test covering actor, critic, and reflection layers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional

import pytest

from agents.base import AgentResponse, BaseAgent
from agents.coordination import CoordinationAgent
from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer


class GovernanceCriticAgent(BaseAgent):
    """Stub governance critic that forces a failure verdict."""

    name = "governance_critic"
    description = "Reviews actor outputs and can veto low-confidence plans."
    layer = Layer.SUPPORT
    expert_kind = ExpertKind.SUPPORT
    capabilities = AgentCapabilities(
        primary=(
            CapabilityDescriptor(
                name="governance_review",
                description="Assesses actor plans for policy compliance.",
                outputs=("verdict", "reason"),
                tags=("critic", "governance"),
            ),
        ),
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        actors = tuple(message.get("actors", ())) if isinstance(message, Mapping) else ()
        transcript = message.get("transcript", []) if isinstance(message, Mapping) else []
        summary = (
            f"Critic reviewed {len(actors)} actors and "
            f"{len(transcript)} transcript entries."
        )
        verdict = "fail"
        reason = "deliberate failure to exercise reflection flow"
        metadata = {"verdict": verdict, "reason": reason, "score": 0.18}
        content = f"{summary} Verdict={verdict.upper()} because {reason}."
        return AgentResponse(content=content, metadata=metadata)


class MetaReflectionAgent(BaseAgent):
    """Stub meta-agent that persists reflection artifacts."""

    name = "meta_reflection"
    description = "Writes remediation artifacts when critic vetoes outputs."
    layer = Layer.SUPPORT
    expert_kind = ExpertKind.SUPPORT
    capabilities = AgentCapabilities(
        primary=(
            CapabilityDescriptor(
                name="meta_reflection",
                description="Records reflection artifacts for failed runs.",
                outputs=("artifact_path", "summary"),
                tags=("reflection", "meta"),
            ),
        ),
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        artifact_path_value = (
            message.get("artifact_path") if isinstance(message, Mapping) else None
        )
        if not artifact_path_value:
            raise ValueError("artifact_path is required for reflection output")
        artifact_path = Path(str(artifact_path_value))
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "summary": message.get("summary") if isinstance(message, Mapping) else None,
            "critic": message.get("critic_metadata") if isinstance(message, Mapping) else None,
            "timestamp": "2024-01-01T00:00:00Z",
        }
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        content = f"Reflection stored at {artifact_path.name}"
        metadata = {
            "artifact_path": str(artifact_path),
            "status": "written",
        }
        return AgentResponse(content=content, metadata=metadata)


@pytest.mark.asyncio
async def test_hierarchy_flow_three_layer_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_openai_client_class,
    fake_shared_memory,
    fake_registry,
    dummy_metrics,
    stub_agent_settings,
) -> None:
    """Simulate full hierarchy flow with actors, critic, and reflection layers."""

    metrics = dummy_metrics
    memory = fake_shared_memory
    registry = fake_registry
    config = stub_agent_settings

    registry.register("governance_critic", agent_cls=GovernanceCriticAgent, aliases=("critic",))
    registry.register("meta_reflection", agent_cls=MetaReflectionAgent, aliases=("meta",))

    memory.problem_results = [
        {
            "problem": "How to coordinate multi-agent hierarchy?",
            "solution": "Leverage actors, a critic gate, and meta reflection.",
            "similarity_score": 0.91,
        }
    ]
    memory.collaboration_results = [
        {
            "interaction_id": "prev-run",
            "summary": "Previous run captured actor and critic trace logs.",
            "similarity_score": 0.84,
        }
    ]

    artifact_dir = tmp_path / "hierarchy_artifacts"
    artifact_dir.mkdir()

    lookups: list[str] = []

    def stub_analyze_question(self: CoordinationAgent, question: str) -> dict[str, Any]:
        return {
            "required_experts": ["python_expert", "milvus_expert"],
            "complexity": "complex",
            "keywords": ["hierarchy", "flow", "multi-agent"],
            "reasoning": "deterministic analysis for hierarchy flow test",
        }

    async def stub_synthesize_answer(
        self: CoordinationAgent,
        question: str,
        analysis: dict[str, Any],
        expert_responses: dict[str, str],
        tenant_id: str = "default",
        verbose: Optional[bool] = None,
    ) -> str:
        actor_summary = " | ".join(
            f"{agent}: {content.split('.')[0]}"
            for agent, content in expert_responses.items()
            if agent in {"python_expert", "milvus_expert"}
        )
        critic_summary = expert_responses.get("governance_critic", "")
        reflection_note = expert_responses.get("meta_reflection", "")
        return (
            "Hierarchy synthesis complete. Actors responded with actionable guidance. "
            f"{actor_summary}. Critic review: {critic_summary} Reflection: {reflection_note}"
        )

    async def hierarchical_dispatch(
        self: CoordinationAgent,
        question: str,
        analysis: dict[str, Any],
        similar_knowledge: list[dict[str, Any]],
        tenant_id: str = "default",
    ) -> dict[str, Any]:
        correlation_id = "corr-hierarchy"
        interaction_id = "hierarchy-collab"
        actor_labels = list(dict.fromkeys(analysis.get("required_experts", [])))
        analysis["required_experts"] = actor_labels

        self.active_collaborations[interaction_id] = {
            "status": "in_progress",
            "experts": actor_labels,
            "responses": {},
            "started_at": time.time(),
            "correlation_id": correlation_id,
        }

        transcript = [
            {
                "role": "selector",
                "agent": "group_selector",
                "selected": actor_labels,
                "note": "deterministic hierarchy group selection",
            }
        ]
        scoreboard: dict[str, Any] = {
            "actors": {},
            "critic": {},
            "reflection": {},
        }
        registry_entries: dict[str, Any] = {}
        expert_responses: dict[str, str] = {}

        for label in actor_labels:
            lookups.append(label)
            entry = self.registry.get(label)
            assert entry is not None, f"Expert {label} missing from registry"
            registry_entries[label] = entry.to_dict()
            instance = entry.create_instance()
            actor_message = {
                "question": question,
                "tenant_id": tenant_id,
                "context": similar_knowledge,
                "role": "actor",
            }
            response = await instance.handle_message(actor_message)
            expert_responses[label] = response.content
            scoreboard["actors"][label] = {
                "status": "completed",
                "content": response.content,
            }
            transcript.append(
                {
                    "role": "actor",
                    "agent": label,
                    "content": response.content,
                }
            )

        critic_label = "governance_critic"
        lookups.append(critic_label)
        critic_entry = self.registry.get(critic_label)
        assert critic_entry is not None, "Critic entry missing"
        registry_entries[critic_label] = critic_entry.to_dict()
        critic_instance = critic_entry.create_instance()
        critic_payload = {
            "actors": actor_labels,
            "transcript": list(transcript),
            "tenant_id": tenant_id,
        }
        critic_response = await critic_instance.handle_message(critic_payload)
        expert_responses[critic_label] = critic_response.content
        scoreboard["critic"] = {
            "agent": critic_label,
            "verdict": critic_response.metadata.get("verdict"),
            "reason": critic_response.metadata.get("reason"),
            "content": critic_response.content,
        }
        transcript.append(
            {
                "role": "critic",
                "agent": critic_label,
                "content": critic_response.content,
            }
        )

        meta_label = "meta_reflection"
        lookups.append(meta_label)
        meta_entry = self.registry.get(meta_label)
        assert meta_entry is not None, "Meta reflection entry missing"
        registry_entries[meta_label] = meta_entry.to_dict()
        meta_instance = meta_entry.create_instance()
        artifact_path = artifact_dir / f"{interaction_id}_reflection.json"
        meta_payload = {
            "critic_metadata": critic_response.metadata,
            "summary": "Critic forced failure path to trigger reflection artifact",
            "artifact_path": str(artifact_path),
            "tenant_id": tenant_id,
        }
        meta_response = await meta_instance.handle_message(meta_payload)
        expert_responses[meta_label] = meta_response.content
        scoreboard["reflection"] = {
            "agent": meta_label,
            "artifact_path": meta_response.metadata.get("artifact_path"),
            "status": meta_response.metadata.get("status"),
            "content": meta_response.content,
        }
        transcript.append(
            {
                "role": "reflection",
                "agent": meta_label,
                "content": meta_response.content,
            }
        )

        collab_state = self.active_collaborations[interaction_id]
        collab_state["responses"] = expert_responses
        collab_state["status"] = "completed"
        collab_state["registry_entries"] = registry_entries
        collab_state["transcript"] = transcript
        collab_state["scoreboard"] = scoreboard

        return {
            "interaction_id": interaction_id,
            "expert_responses": expert_responses,
            "status": "completed",
            "correlation_id": correlation_id,
            "registry_entries": registry_entries,
            "transcript": transcript,
            "scoreboard": scoreboard,
        }

    monkeypatch.setattr("agents.coordination.agent.metrics_registry", metrics)
    monkeypatch.setattr("agents.coordination.agent.SharedMemory", lambda *_, **__: memory)
    monkeypatch.setattr("agents.coordination.agent.OpenAIClientWrapper", fake_openai_client_class)
    monkeypatch.setattr("agents.coordination.agent.get_agent_config", lambda *_: config)
    monkeypatch.setattr("agents.coordination.agent.get_agent_answer_verbose", lambda *_: False)
    monkeypatch.setattr("agents.coordination.agent.get_expert_registry", lambda: registry)

    monkeypatch.setattr(CoordinationAgent, "analyze_question", stub_analyze_question, raising=False)
    monkeypatch.setattr(CoordinationAgent, "synthesize_answer", stub_synthesize_answer, raising=False)
    monkeypatch.setattr(CoordinationAgent, "dispatch_to_experts", hierarchical_dispatch, raising=False)

    agent = CoordinationAgent()

    message = {
        "id": "msg-hierarchy-001",
        "tenant_id": "tenant-xyz",
        "text": "Walk through a three-layer hierarchy flow with critic gating.",
    }

    response = await agent.handle_message(message)

    assert isinstance(response, AgentResponse)
    assert response.metadata["experts_involved"] == ["python_expert", "milvus_expert"]
    assert response.metadata["complexity"] == "complex"
    assert response.metadata["knowledge_used"] is True
    assert response.metadata["interaction_id"] == "hierarchy-collab"
    assert "Hierarchy synthesis complete" in response.content

    assert metrics.requests
    metrics_agent, status, _ = metrics.requests[-1]
    assert metrics_agent == "coordination"
    assert status == "success"
    assert metrics.retrieval_hits
    assert metrics.retrieval_hits[-1][0] == "coordination"

    stored_collections = {call["collection"] for call in memory.store_calls}
    assert {"collaboration_history", "problem_solutions"}.issubset(stored_collections)

    assert lookups == [
        "python_expert",
        "milvus_expert",
        "governance_critic",
        "meta_reflection",
    ]

    interaction_id = response.metadata["interaction_id"]
    assert interaction_id in agent.active_collaborations
    collaboration_state = agent.active_collaborations[interaction_id]

    transcript = collaboration_state["transcript"]
    assert any(entry["role"] == "actor" and entry["agent"] == "python_expert" for entry in transcript)
    assert any(entry["role"] == "actor" and entry["agent"] == "milvus_expert" for entry in transcript)
    assert any(entry["role"] == "critic" for entry in transcript)
    assert any(entry["role"] == "reflection" for entry in transcript)

    scoreboard = collaboration_state["scoreboard"]
    assert set(scoreboard["actors"]) == {"python_expert", "milvus_expert"}
    assert scoreboard["critic"]["verdict"] == "fail"
    assert scoreboard["reflection"]["status"] == "written"

    registry_snapshot = collaboration_state["registry_entries"]
    assert {"python_expert", "milvus_expert", "governance_critic", "meta_reflection"}.issubset(
        registry_snapshot
    )

    artifact_path = Path(scoreboard["reflection"]["artifact_path"])
    assert artifact_path.is_file()
    assert artifact_path.parent == artifact_dir

    payload = json.loads(artifact_path.read_text())
    assert payload["critic"]["verdict"] == "fail"
    assert payload["summary"].startswith("Critic forced failure path")

    search_collections = {call["collection"] for call in memory.search_calls}
    assert {"problem_solutions", "collaboration_history"}.issubset(search_collections)
