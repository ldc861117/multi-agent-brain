"""Base protocol for OpenAgents-compatible agent scaffolding.

This module intentionally keeps the interface extremely small so that the
initial project layout can be validated without requiring the full
OpenAgents runtime to be present during development. Concrete agents can
extend :class:`BaseAgent` and override :meth:`handle_message` to plug into
OpenAgents once the richer behaviour is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Optional


@dataclass
class AgentResponse:
    """Tiny container mirroring the OpenAgents response contract."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    """Minimal asynchronous-friendly agent abstraction.

    Real agent implementations should subclass this and implement
    :meth:`handle_message`. The signature mirrors the semantics commonly
    used across the OpenAgents ecosystem while staying lightweight for unit
    testing and bootstrapping purposes.
    """

    #: Canonical name used when wiring the agent into a channel definition.
    name: str = "base"

    #: Short summary that can be surfaced by the coordination layer or UI.
    description: str = "Base agent scaffold"

    async def handle_message(
        self,
        message: Mapping[str, Any],
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        """Process an incoming message.

        Parameters
        ----------
        message:
            The payload received from the OpenAgents network. The contract is
            intentionally flexible to make scaffolding easy.
        conversation_state:
            Optional shared state that can persist across turns.

        Returns
        -------
        AgentResponse
            Placeholder response to keep the network responsive during
            development.
        """

        raise NotImplementedError("Agent subclasses must implement handle_message().")
