"""General purpose agent placeholder.

The initial scaffold keeps the agent implementation deliberately light-weight
so that the network can be wired without depending on upstream services.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from agents.base import AgentResponse, BaseAgent


class GeneralAgent(BaseAgent):
    """Default entry point for ad-hoc conversation handling."""

    name = "general"
    description = "Handles open-ended user messages across the network."

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        user_content = _coerce_content(message)
        reply = (
            "Hello! I'm the generalist placeholder agent. "
            "Once the specialised agents are implemented, I'll orchestrate "
            "handoffs and provide high-level assistance."
        )
        metadata = {
            "channel": self.name,
            "received": user_content,
        }
        return AgentResponse(content=reply, metadata=metadata)


def _coerce_content(message: Mapping[str, Any] | Any) -> str:
    if isinstance(message, Mapping):
        for key in ("content", "text", "message"):
            if key in message and message[key]:
                return str(message[key])
    return str(message)
