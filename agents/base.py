"""Base protocol and compatibility adapter for OpenAgents-style agents."""

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Protocol, Sequence, Union, runtime_checkable

from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer, ToolDescriptor
from utils import get_browser_tool_config

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
    
    def __init__(self) -> None:
        """Initialize base agent with lazy-loaded tools."""
        super().__init__()
        self._browser_tool: Optional[Any] = None

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

        handler = cls.__dict__.get("handle_message")
        if handler is not None and not inspect.iscoroutinefunction(handler):
            @functools.wraps(handler)
            async def _async_handle(
                self,
                message: AgentMessage,
                conversation_state: ConversationState = None,
            ) -> AgentResponse:
                result = handler(self, message, conversation_state)
                return self._coerce_agent_response(result)

            setattr(cls, "handle_message", _async_handle)

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

        result = await self.handle_message(message, conversation_state=conversation_state)
        return self._coerce_agent_response(result)

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
        """Return available tools including browser tool if enabled."""
        browser_config = get_browser_tool_config(getattr(self, 'name', 'base'))
        
        tools_list = []
        
        if browser_config.enabled:
            browser_tool_desc = ToolDescriptor(
                name="browser_tool",
                description=(
                    "Search the web and navigate pages to gather external information. "
                    "Supports web search via multiple providers and content extraction."
                ),
                returns="BrowserResult",
                parameters={
                    "action": {
                        "type": "string",
                        "enum": ["search", "search_and_visit", "visit"],
                        "description": "Action to perform: 'search' for web search only, "
                                     "'search_and_visit' to search and visit top results, "
                                     "'visit' to navigate to a specific URL"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query or URL to visit",
                        "required": True
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return",
                        "default": 5
                    },
                    "visit_top_n": {
                        "type": "integer",
                        "description": "Number of top search results to visit (for search_and_visit)",
                        "default": 2
                    }
                }
            )
            tools_list.append(browser_tool_desc)
        
        return tuple(tools_list)
    
    def _get_browser_tool(self) -> Any:
        """Lazy initialization of browser tool.
        
        Returns
        -------
        BrowserTool
            Browser tool instance configured for this agent
        """
        if self._browser_tool is None:
            from tools.browser_tool import BrowserTool
            self._browser_tool = BrowserTool(agent_name=getattr(self, 'name', 'base'))
        return self._browser_tool

    def _coerce_agent_response(self, payload: Any) -> AgentResponse:
        if isinstance(payload, AgentResponse):
            return payload
        if isinstance(payload, tuple) and len(payload) == 2:
            content, metadata = payload
            if not isinstance(metadata, Mapping):
                metadata = {"value": metadata}
            return AgentResponse(content=str(content), metadata=dict(metadata))
        if isinstance(payload, Mapping):
            content = payload.get("content")
            metadata = payload.get("metadata", {})
            if content is None:
                remaining = {k: v for k, v in payload.items() if k != "metadata"}
                content = remaining or ""
            if not isinstance(metadata, Mapping):
                metadata = {"value": metadata}
            return AgentResponse(content=str(content), metadata=dict(metadata))
        if payload is None:
            return AgentResponse(content="", metadata={})
        return AgentResponse(content=str(payload), metadata={})

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
