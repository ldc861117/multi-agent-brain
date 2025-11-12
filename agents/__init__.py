"""Agent package exposing the multi-channel scaffolding."""

from .base import (
    AgentMessage,
    AgentResponse,
    BaseAgent,
    BaseAgentProtocol,
    ConversationState,
    PlanResult,
    ReflectionResult,
    RouteDecision,
)
from .coordination import CoordinationAgent
from .devops_expert import DevOpsExpertAgent
from .general import GeneralAgent
from .milvus_expert import MilvusExpertAgent
from .python_expert import PythonExpertAgent
from .registry import (
    ExpertRegistry,
    ExpertRegistration,
    bootstrap_registry,
    expert_registry,
    get_expert_registry,
)
from .types import (
    AgentCapabilities,
    CapabilityDescriptor,
    ExpertKind,
    Layer,
    ToolDescriptor,
)

__all__ = [
    "AgentMessage",
    "AgentResponse",
    "AgentCapabilities",
    "CapabilityDescriptor",
    "BaseAgent",
    "BaseAgentProtocol",
    "ConversationState",
    "CoordinationAgent",
    "DevOpsExpertAgent",
    "ExpertKind",
    "ExpertRegistry",
    "ExpertRegistration",
    "GeneralAgent",
    "Layer",
    "MilvusExpertAgent",
    "PlanResult",
    "PythonExpertAgent",
    "ReflectionResult",
    "RouteDecision",
    "ToolDescriptor",
    "bootstrap_registry",
    "expert_registry",
    "get_expert_registry",
]
