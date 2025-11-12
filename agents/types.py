"""Typed enumerations and capability descriptors for the agent hierarchy.

This module introduces a lightweight vocabulary for describing the layered
agent network. It keeps the implementation intentionally defensive so that
partially configured agents or legacy subclasses can continue to operate
without raising runtime errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Tuple


class Layer(str, Enum):
    """Logical layer each agent belongs to within the hierarchy."""

    ENTRY = "entry"
    COORDINATION = "coordination"
    EXPERT = "expert"
    SUPPORT = "support"
    SERVICE = "service"
    UNKNOWN = "unknown"

    @classmethod
    def coerce(cls, value: "Layer | str | None") -> "Layer":
        """Best-effort conversion returning :class:`Layer.UNKNOWN` on failure."""

        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        normalised = str(value).strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        return cls.UNKNOWN

    @classmethod
    def from_value(cls, value: "Layer | str | None") -> "Layer":
        """Alias for :meth:`coerce` to keep the API ergonomic."""

        return cls.coerce(value)

    def __str__(self) -> str:  # pragma: no cover - trivial dunder
        return self.value


class ExpertKind(str, Enum):
    """Semantic grouping matching the current agent implementations."""

    GENERAL = "general"
    COORDINATION = "coordination"
    PYTHON_EXPERT = "python_expert"
    MILVUS_EXPERT = "milvus_expert"
    DEVOPS_EXPERT = "devops_expert"
    MEMORY = "memory"
    SUPPORT = "support"
    UNKNOWN = "unknown"

    _ALIASES: Mapping[str, "ExpertKind"] = MappingProxyType(
        {
            "python": PYTHON_EXPERT,
            "milvus": MILVUS_EXPERT,
            "devops": DEVOPS_EXPERT,
            "router": COORDINATION,
            "entry": GENERAL,
            "gateway": GENERAL,
        }
    )

    @classmethod
    def coerce(cls, value: "ExpertKind | str | None") -> "ExpertKind":
        """Best-effort conversion returning :class:`ExpertKind.UNKNOWN` on failure."""

        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        normalised = str(value).strip().lower()
        if normalised in cls._ALIASES:
            return cls._ALIASES[normalised]
        for member in cls:
            if member.value == normalised:
                return member
        return cls.UNKNOWN

    @classmethod
    def from_value(cls, value: "ExpertKind | str | None") -> "ExpertKind":
        """Alias for :meth:`coerce` to mirror the :class:`Layer` helper."""

        return cls.coerce(value)

    def __str__(self) -> str:  # pragma: no cover - trivial dunder
        return self.value


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Machine-readable description of a discrete agent capability."""

    name: str
    description: str
    inputs: Tuple[str, ...] = field(default_factory=tuple)
    outputs: Tuple[str, ...] = field(default_factory=tuple)
    tags: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class ToolDescriptor:
    """Represents a tool the agent can expose to the broader network."""

    name: str
    description: str
    returns: str = "text"
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True)
class AgentCapabilities:
    """Structured capability set with primary and auxiliary groupings."""

    primary: Tuple[CapabilityDescriptor, ...] = field(default_factory=tuple)
    auxiliary: Tuple[CapabilityDescriptor, ...] = field(default_factory=tuple)
    experimental: Tuple[CapabilityDescriptor, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "primary", tuple(self.primary))
        object.__setattr__(self, "auxiliary", tuple(self.auxiliary))
        object.__setattr__(self, "experimental", tuple(self.experimental))

    def all_capabilities(self) -> Tuple[CapabilityDescriptor, ...]:
        """Return every descriptor in a deterministic order."""

        return (*self.primary, *self.auxiliary, *self.experimental)

    def __iter__(self) -> Iterable[CapabilityDescriptor]:  # pragma: no cover - passthrough
        return iter(self.all_capabilities())


__all__ = [
    "AgentCapabilities",
    "CapabilityDescriptor",
    "ExpertKind",
    "Layer",
    "ToolDescriptor",
]
