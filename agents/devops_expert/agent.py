"""DevOps expert agent placeholder."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from agents.base import AgentResponse, BaseAgent


class DevOpsExpertAgent(BaseAgent):
    """Handles CI/CD, infrastructure, and deployment topics."""

    name = "devops_expert"
    description = (
        "Lends support for infrastructure automation, observability, and releases."
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        question = _extract_question(message)
        reply = (
            "DevOps expert ready. Share pipeline challenges or deployment "
            "concerns and future iterations will respond with actionable steps."
        )
        metadata = {
            "channel": self.name,
            "question": question,
        }
        return AgentResponse(content=reply, metadata=metadata)


def _extract_question(message: Mapping[str, Any] | Any) -> str:
    if isinstance(message, Mapping):
        for key in ("issue", "content", "topic"):
            value = message.get(key)
            if value:
                return str(value)
    return str(message)
