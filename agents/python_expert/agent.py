"""Python expert agent placeholder."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from agents.base import AgentResponse, BaseAgent


class PythonExpertAgent(BaseAgent):
    """A scaffold for code-focused support within the network."""

    name = "python_expert"
    description = (
        "Responds to Python development questions and eventually executes snippets."
    )

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        prompt = _extract_prompt(message)
        reply = (
            "Python expert ready. Supply code or debugging prompts and I'll "
            "return walkthroughs once the runtime tools are connected."
        )
        metadata = {
            "channel": self.name,
            "prompt": prompt,
        }
        return AgentResponse(content=reply, metadata=metadata)


def _extract_prompt(message: Mapping[str, Any] | Any) -> str:
    if isinstance(message, Mapping):
        for key in ("code", "prompt", "content"):
            if key in message and message[key]:
                return str(message[key])
    return str(message)
