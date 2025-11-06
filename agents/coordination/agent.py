"""Coordination agent stub.

This agent will eventually orchestrate specialised experts and maintain
conversation-wide context.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from agents.base import AgentResponse, BaseAgent


class CoordinationAgent(BaseAgent):
    """Placeholder coordination agent that documents the intended contract."""

    name = "coordination"
    description = (
        "Routes work between the specialist agents and keeps the team aligned."
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        summary = _summarise(message)
        reply = (
            "Coordination agent ready. Once fully implemented, I'll analyse "
            "incoming tasks, engage the relevant experts, and blend their "
            "responses into a cohesive plan."
        )
        metadata = {
            "channel": self.name,
            "summary": summary,
        }
        return AgentResponse(content=reply, metadata=metadata)


def _summarise(message: Mapping[str, Any] | Any) -> str:
    if isinstance(message, Mapping):
        parts = []
        for key in ("content", "intent", "topic"):
            value = message.get(key)
            if value:
                parts.append(f"{key}={value}")
        if parts:
            return ", ".join(parts)
    return str(message)
