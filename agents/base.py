"""Base protocol and compatibility adapter for OpenAgents-style agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Protocol, Sequence, Union, runtime_checkable

from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer, ToolDescriptor

AgentMessage = Union[Mapping[str, Any], Any]
ConversationState = Optional[MutableMapping[str, Any]]
PlanResult = Mapping[str, Any]
ReflectionResult = Mapping[str, Any]
RouteDecision = Mapping[str, Any]


@dataclass
class AgentResponse:
    """Tiny container mirroring the OpenAgents response contract."""

    content: str
    metadata: Mapping[str, Any]

    def __init__(self, content: str, metadata: Optional[Mapping[str, Any]] = None) -> None:
        self.content = content
        self.metadata = dict(metadata or {})


@runtime_checkable
class BaseAgentProtocol(Protocol):
    """Protocol describing the modern agent surface area."""

    name: str
    role: str
    description: str
    layer: Layer
    expert_kind: ExpertKind
    capabilities: AgentCapabilities

    async def plan(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **kwargs: Any,
    ) -> PlanResult:
        ...

    async def act(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **kwargs: Any,
    ) -> AgentResponse:
        ...

    async def reflect(
        self,
        message: AgentMessage,
        result: AgentResponse,
        conversation_state: ConversationState = None,
        **kwargs: Any,
    ) -> ReflectionResult:
        ...

    async def route(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **kwargs: Any,
    ) -> RouteDecision:
        ...

    def tools(self) -> Sequence[ToolDescriptor]:
        ...

    async def handle_message(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
    ) -> AgentResponse:
        ...


class BaseAgent(BaseAgentProtocol):
    """Compatibility adapter that keeps legacy :meth:`handle_message` agents working."""

    name: str = "base"
    role: str = "agent"
    description: str = "Base agent scaffold"
    layer: Layer = Layer.UNKNOWN
    expert_kind: ExpertKind = ExpertKind.UNKNOWN
    capabilities: AgentCapabilities = AgentCapabilities()

    def __init_subclass__(cls, **kwargs: Any) -> None:  # pragma: no cover - exercised indirectly
        super().__init_subclass__(**kwargs)
        cls.layer = Layer.coerce(getattr(cls, "layer", Layer.UNKNOWN))
        cls.expert_kind = ExpertKind.coerce(
            getattr(cls, "expert_kind", getattr(cls, "name", None))
        )
        declared_capabilities = getattr(cls, "capabilities", AgentCapabilities())
        if isinstance(declared_capabilities, CapabilityDescriptor):
            cls.capabilities = AgentCapabilities(primary=(declared_capabilities,))
        elif isinstance(declared_capabilities, AgentCapabilities):
            cls.capabilities = declared_capabilities
        elif isinstance(declared_capabilities, (list, tuple)) and all(
            isinstance(item, CapabilityDescriptor) for item in declared_capabilities
        ):
            cls.capabilities = AgentCapabilities(primary=tuple(declared_capabilities))
        else:
            cls.capabilities = AgentCapabilities()
        if not getattr(cls, "role", None):
            cls.role = (
                cls.expert_kind.value
                if cls.expert_kind is not ExpertKind.UNKNOWN
                else "agent"
            )

    async def plan(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **_: Any,
    ) -> PlanResult:
        """Return a no-op plan to keep scaffolding stable."""

        return {"status": "noop", "reason": "planning not implemented"}

    async def act(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **_: Any,
    ) -> AgentResponse:
        """Delegate to :meth:`handle_message` for backwards compatibility."""

        return await self.handle_message(message, conversation_state=conversation_state)

    async def reflect(
        self,
        message: AgentMessage,
        result: AgentResponse,
        conversation_state: ConversationState = None,
        **_: Any,
    ) -> ReflectionResult:
        """Return a minimal reflection payload to satisfy the protocol."""

        return {
            "status": "noop",
            "reason": "reflection not implemented",
            "last_response": result.content,
        }

    async def route(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
        **_: Any,
    ) -> RouteDecision:
        """Default routing simply echoes the agent's configured layer."""

        return {
            "layer": self.layer.value,
            "expert_kind": self.expert_kind.value,
            "targets": (),
        }

    def tools(self) -> Sequence[ToolDescriptor]:
        """Fallback to an empty toolset."""

        return ()

    async def handle_message(
        self,
        message: AgentMessage,
        conversation_state: ConversationState = None,
    ) -> AgentResponse:
        raise NotImplementedError("Agent subclasses must implement handle_message().")


__all__ = [
    "AgentMessage",
    "AgentResponse",
    "BaseAgent",
    "BaseAgentProtocol",
    "ConversationState",
    "PlanResult",
    "ReflectionResult",
    "RouteDecision",
]
