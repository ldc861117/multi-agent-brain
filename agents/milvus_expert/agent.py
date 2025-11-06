"""Milvus expert agent placeholder."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from agents.base import AgentResponse, BaseAgent


class MilvusExpertAgent(BaseAgent):
    """Guides Milvus configuration, schema design, and troubleshooting."""

    name = "milvus_expert"
    description = "Helps with Milvus vector database operations and tuning."

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        focus = _extract_focus(message)
        reply = (
            "Milvus expert standing by. Describe your collection layout or "
            "embedding strategy and future revisions will return concrete advice."
        )
        metadata = {
            "channel": self.name,
            "focus": focus,
        }
        return AgentResponse(content=reply, metadata=metadata)


def _extract_focus(message: Mapping[str, Any] | Any) -> str:
    if isinstance(message, Mapping):
        for key in ("collection", "task", "content"):
            if key in message and message[key]:
                return str(message[key])
    return str(message)
