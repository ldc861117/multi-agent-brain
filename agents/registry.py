"""Dynamic in-memory registry for expert agents.

This module introduces a lightweight registry abstraction used by the
``CoordinationAgent`` (and future orchestration layers) to discover experts
without hard-coding import paths. The registry supports runtime registration
and deregistration, alias lookups, capability-based filtering, and optional
health-check callbacks.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Type

from loguru import logger

from agents.base import BaseAgent
from agents.types import ExpertKind, Layer
from utils import get_config_manager

HealthcheckResult = Mapping[str, Any]
HealthcheckCallable = Callable[[], Any]


def _normalise_key(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


@dataclass(frozen=True)
class ExpertRegistration:
    """Immutable description of a registered expert."""

    name: str
    layer: Layer = Layer.UNKNOWN
    expert_kind: ExpertKind = ExpertKind.UNKNOWN
    description: str = ""
    capabilities: Tuple[str, ...] = ()
    entrypoint: Optional[str] = None
    agent_cls: Optional[Type[BaseAgent]] = None
    enabled: bool = True
    aliases: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    healthcheck: Optional[HealthcheckCallable] = None
    capability_index: frozenset[str] = field(default_factory=frozenset, repr=False)

    def create_instance(self) -> BaseAgent:
        """Instantiate the registered agent."""

        if self.agent_cls is None:
            raise RuntimeError(f"Expert '{self.name}' does not expose an agent class")
        return self.agent_cls()

    def has_capability(self, capability: str) -> bool:
        return _normalise_key(capability) in self.capability_index

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "layer": self.layer.value,
            "expert_kind": self.expert_kind.value,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "entrypoint": self.entrypoint,
            "aliases": list(self.aliases),
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }


class ExpertRegistry:
    """Thread-safe in-memory expert registry."""

    def __init__(self) -> None:
        self._experts: Dict[str, ExpertRegistration] = {}
        self._canonical_index: Dict[str, str] = {}
        self._alias_index: Dict[str, str] = {}
        self._lock = RLock()

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def clear(self) -> None:
        with self._lock:
            self._experts.clear()
            self._canonical_index.clear()
            self._alias_index.clear()

    def register(
        self,
        name: str,
        *,
        agent_cls: Optional[Type[BaseAgent]] = None,
        entrypoint: Optional[str] = None,
        layer: Layer | str | None = None,
        expert_kind: ExpertKind | str | None = None,
        description: Optional[str] = None,
        capabilities: Optional[Iterable[str]] = None,
        aliases: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        enabled: bool = True,
        healthcheck: Optional[HealthcheckCallable] = None,
    ) -> ExpertRegistration:
        canonical_name = str(name).strip()
        if not canonical_name:
            raise ValueError("Expert name must be a non-empty string")

        resolved_cls = agent_cls or self._resolve_agent_class(entrypoint)
        resolved_entrypoint = entrypoint or (
            f"{resolved_cls.__module__}:{resolved_cls.__name__}" if resolved_cls else None
        )

        resolved_layer = Layer.coerce(layer or (resolved_cls.layer if resolved_cls else None))
        resolved_kind = ExpertKind.coerce(
            expert_kind or (resolved_cls.expert_kind if resolved_cls else canonical_name)
        )
        resolved_description = description or (
            resolved_cls.description if resolved_cls and getattr(resolved_cls, "description", None) else ""
        )

        # Derive capability tokens.
        capability_tokens: List[str] = []
        if capabilities:
            capability_tokens.extend(str(item).strip() for item in capabilities if str(item).strip())
        if resolved_cls is not None:
            try:
                descriptors = resolved_cls.capabilities.all_capabilities()
            except Exception:  # pragma: no cover - defensive, capabilities is well-defined
                descriptors = ()
            for descriptor in descriptors:
                capability_tokens.append(descriptor.name)
                capability_tokens.extend(descriptor.tags)
                capability_tokens.extend(descriptor.outputs)
            # Include expert kind and layer keywords for easier matching.
            capability_tokens.extend(
                value
                for value in (
                    getattr(resolved_cls, "name", None),
                    resolved_kind.value,
                    resolved_layer.value,
                    resolved_cls.__name__,
                )
                if value
            )

        normalised_capabilities = tuple(
            dict.fromkeys(_normalise_key(item) for item in capability_tokens if _normalise_key(item))
        )

        alias_tokens: List[str] = []
        if aliases:
            alias_tokens.extend(str(item).strip() for item in aliases if str(item).strip())
        if resolved_cls is not None:
            agent_declared_name = str(getattr(resolved_cls, "name", "")).strip()
            if agent_declared_name and agent_declared_name != canonical_name:
                alias_tokens.append(agent_declared_name)
        # Provide implicit alias for *_expert style names to support legacy routing.
        if canonical_name.endswith("_expert"):
            alias_tokens.append(canonical_name[:-7])

        unique_aliases = tuple(
            alias for alias in dict.fromkeys(alias_tokens) if _normalise_key(alias) and _normalise_key(alias) != _normalise_key(canonical_name)
        )

        capability_index = frozenset(normalised_capabilities)
        metadata_payload = MappingProxyType(dict(metadata or {}))

        registration = ExpertRegistration(
            name=canonical_name,
            layer=resolved_layer,
            expert_kind=resolved_kind,
            description=resolved_description,
            capabilities=normalised_capabilities,
            entrypoint=resolved_entrypoint,
            agent_cls=resolved_cls,
            enabled=enabled,
            aliases=unique_aliases,
            metadata=metadata_payload,
            healthcheck=healthcheck,
            capability_index=capability_index,
        )

        with self._lock:
            self._remove_entry_unlocked(canonical_name)
            self._store_entry_unlocked(registration)

        logger.debug(
            "Registered expert",
            extra={
                "expert": canonical_name,
                "layer": registration.layer.value,
                "kind": registration.expert_kind.value,
                "aliases": registration.aliases,
                "capabilities": registration.capabilities,
            },
        )
        return registration

    def deregister(self, name: str) -> Optional[ExpertRegistration]:
        canonical_name = self._resolve_canonical_name(name)
        if not canonical_name:
            return None
        with self._lock:
            return self._remove_entry_unlocked(canonical_name)

    def enable(self, name: str) -> bool:
        entry = self.get(name)
        if not entry:
            return False
        if entry.enabled:
            return True
        updated = ExpertRegistration(
            name=entry.name,
            layer=entry.layer,
            expert_kind=entry.expert_kind,
            description=entry.description,
            capabilities=entry.capabilities,
            entrypoint=entry.entrypoint,
            agent_cls=entry.agent_cls,
            enabled=True,
            aliases=entry.aliases,
            metadata=entry.metadata,
            healthcheck=entry.healthcheck,
            capability_index=entry.capability_index,
        )
        with self._lock:
            self._remove_entry_unlocked(entry.name)
            self._store_entry_unlocked(updated)
        return True

    def disable(self, name: str) -> bool:
        entry = self.get(name)
        if not entry:
            return False
        if not entry.enabled:
            return True
        updated = ExpertRegistration(
            name=entry.name,
            layer=entry.layer,
            expert_kind=entry.expert_kind,
            description=entry.description,
            capabilities=entry.capabilities,
            entrypoint=entry.entrypoint,
            agent_cls=entry.agent_cls,
            enabled=False,
            aliases=entry.aliases,
            metadata=entry.metadata,
            healthcheck=entry.healthcheck,
            capability_index=entry.capability_index,
        )
        with self._lock:
            self._remove_entry_unlocked(entry.name)
            self._store_entry_unlocked(updated)
        return True

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    def get(self, name: str) -> Optional[ExpertRegistration]:
        canonical_name = self._resolve_canonical_name(name)
        if not canonical_name:
            return None
        with self._lock:
            return self._experts.get(canonical_name)

    def exists(self, name: str) -> bool:
        return self.get(name) is not None

    def list(
        self,
        *,
        layer: Layer | str | None = None,
        expert_kind: ExpertKind | str | None = None,
        capabilities: Optional[Iterable[str]] = None,
        include_disabled: bool = False,
    ) -> Tuple[ExpertRegistration, ...]:
        layer_filter = Layer.coerce(layer) if layer is not None else None
        kind_filter = ExpertKind.coerce(expert_kind) if expert_kind is not None else None
        capability_filter = None
        if capabilities is not None:
            capability_filter = {
                _normalise_key(token) for token in capabilities if _normalise_key(token)
            }

        with self._lock:
            entries = list(self._experts.values())

        results: List[ExpertRegistration] = []
        for entry in entries:
            if not include_disabled and not entry.enabled:
                continue
            if layer_filter is not None and entry.layer is not layer_filter:
                continue
            if kind_filter is not None and entry.expert_kind is not kind_filter:
                continue
            if capability_filter and not capability_filter.issubset(entry.capability_index):
                continue
            results.append(entry)
        results.sort(key=lambda item: item.name)
        return tuple(results)

    def select_by_capability(
        self,
        capability: str,
        *,
        layer: Layer | str | None = None,
        expert_kind: ExpertKind | str | None = None,
        include_disabled: bool = False,
        limit: Optional[int] = None,
    ) -> Tuple[ExpertRegistration, ...]:
        token = _normalise_key(capability)
        if not token:
            return tuple()
        matches = [
            entry
            for entry in self.list(
                layer=layer,
                expert_kind=expert_kind,
                include_disabled=include_disabled,
            )
            if token in entry.capability_index
        ]
        matches.sort(key=lambda item: item.name)
        if limit is not None:
            matches = matches[:limit]
        return tuple(matches)

    # ------------------------------------------------------------------
    # Health-check utilities
    # ------------------------------------------------------------------
    def run_healthcheck(self, name: str) -> Dict[str, Any]:
        entry = self.get(name)
        if not entry:
            return {"status": "unknown", "reason": "expert not registered"}
        if entry.healthcheck is None:
            return {"status": "unknown", "reason": "no healthcheck configured"}
        try:
            result = entry.healthcheck()
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.exception("Expert healthcheck raised exception", extra={"expert": entry.name})
            return {"status": "error", "detail": str(exc)}
        if isinstance(result, Mapping):
            return dict(result)
        if isinstance(result, bool):
            return {"status": "ok" if result else "fail"}
        if result is None:
            return {"status": "ok"}
        return {"status": "ok", "detail": str(result)}

    def run_all_healthchecks(self, include_disabled: bool = True) -> Dict[str, Dict[str, Any]]:
        snapshot: Dict[str, Dict[str, Any]] = {}
        for entry in self.list(include_disabled=include_disabled):
            snapshot[entry.name] = self.run_healthcheck(entry.name)
        return snapshot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_canonical_name(self, name: str | None) -> Optional[str]:
        if name is None:
            return None
        key = _normalise_key(name)
        if not key:
            return None
        with self._lock:
            if key in self._canonical_index:
                return self._canonical_index[key]
            if key in self._alias_index:
                return self._alias_index[key]
        return None

    def _remove_entry_unlocked(self, canonical_name: str) -> Optional[ExpertRegistration]:
        entry = self._experts.pop(canonical_name, None)
        key = _normalise_key(canonical_name)
        self._canonical_index.pop(key, None)
        if entry is not None:
            for alias in entry.aliases:
                self._alias_index.pop(_normalise_key(alias), None)
        return entry

    def _store_entry_unlocked(self, entry: ExpertRegistration) -> None:
        self._experts[entry.name] = entry
        self._canonical_index[_normalise_key(entry.name)] = entry.name
        for alias in entry.aliases:
            alias_key = _normalise_key(alias)
            if not alias_key or alias_key == _normalise_key(entry.name):
                continue
            existing = self._alias_index.get(alias_key)
            if existing and existing != entry.name:
                logger.warning(
                    "Expert alias collision",
                    extra={"alias": alias, "existing": existing, "incoming": entry.name},
                )
            self._alias_index[alias_key] = entry.name

    def _resolve_agent_class(self, entrypoint: Optional[str]) -> Optional[Type[BaseAgent]]:
        if not entrypoint:
            return None
        module_name: Optional[str]
        attribute: Optional[str]
        if ":" in entrypoint:
            module_name, attribute = entrypoint.split(":", 1)
        else:
            parts = entrypoint.rsplit(".", 1)
            if len(parts) == 2:
                module_name, attribute = parts
            else:
                logger.warning(
                    "Invalid entrypoint specification",
                    extra={"entrypoint": entrypoint},
                )
                return None
        module_name = module_name.strip()
        attribute = attribute.strip() if attribute else None
        if not module_name or not attribute:
            logger.warning(
                "Incomplete entrypoint specification",
                extra={"entrypoint": entrypoint},
            )
            return None
        try:
            module = importlib.import_module(module_name)
            candidate = getattr(module, attribute)
        except (ImportError, AttributeError) as exc:
            logger.error(
                "Failed to import expert entrypoint",
                extra={"entrypoint": entrypoint, "error": str(exc)},
            )
            return None
        if not isinstance(candidate, type) or not issubclass(candidate, BaseAgent):
            logger.warning(
                "Registry entrypoint does not resolve to a BaseAgent subclass",
                extra={"entrypoint": entrypoint, "resolved": repr(candidate)},
            )
            return None
        return candidate


# ----------------------------------------------------------------------
# Global registry bootstrap
# ----------------------------------------------------------------------

def bootstrap_registry(
    registry: Optional[ExpertRegistry] = None,
    *,
    config_manager: Optional[Any] = None,
    reset: bool = True,
) -> ExpertRegistry:
    target_registry = registry or expert_registry
    manager = config_manager or get_config_manager()

    try:
        definitions = manager.get_registry_bootstrap()
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.error("Failed to load registry bootstrap definitions", extra={"error": str(exc)})
        definitions = {}

    if reset:
        target_registry.clear()

    for name, payload in definitions.items():
        if not isinstance(payload, Mapping):
            logger.warning(
                "Ignoring registry bootstrap entry without mapping payload",
                extra={"expert": name, "payload_type": type(payload).__name__},
            )
            continue
        kwargs: Dict[str, Any] = {}
        kwargs["entrypoint"] = payload.get("entrypoint")
        kwargs["layer"] = payload.get("layer")
        kwargs["expert_kind"] = payload.get("expert_kind")
        kwargs["description"] = payload.get("description")
        kwargs["capabilities"] = payload.get("capabilities")
        kwargs["aliases"] = payload.get("aliases")
        metadata_value = payload.get("metadata")
        if isinstance(metadata_value, Mapping):
            kwargs["metadata"] = metadata_value
        override_fragment = payload.get("override")
        if isinstance(override_fragment, Mapping):
            merged_meta = dict(kwargs.get("metadata") or {})
            merged_meta.setdefault("override", dict(override_fragment))
            kwargs["metadata"] = merged_meta
        enabled_value = payload.get("enabled", True)
        if isinstance(enabled_value, str):
            enabled_value = enabled_value.strip().lower() not in {"false", "0", "no", "off"}
        kwargs["enabled"] = bool(enabled_value)
        healthcheck_callable = payload.get("healthcheck")
        if callable(healthcheck_callable):
            kwargs["healthcheck"] = healthcheck_callable

        try:
            target_registry.register(name, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.exception(
                "Failed to register expert from configuration",
                extra={"expert": name, "error": str(exc)},
            )

    return target_registry


expert_registry = ExpertRegistry()

try:  # pragma: no cover - bootstrap side-effect at import time
    bootstrap_registry(expert_registry, reset=True)
except Exception:  # pragma: no cover - ensure import never fails
    logger.exception("Expert registry bootstrap failed during import")


def get_expert_registry() -> ExpertRegistry:
    return expert_registry


__all__ = [
    "ExpertRegistry",
    "ExpertRegistration",
    "bootstrap_registry",
    "expert_registry",
    "get_expert_registry",
]
