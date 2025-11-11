"""Observability utilities for logging, correlation IDs, and in-process metrics."""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from loguru import logger


RUN_ID: str = os.getenv("RUN_ID", uuid.uuid4().hex)

_CORRELATION_ID: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_LOG_FORMAT_CHOICES = {"text", "json", "both"}
_TEXT_FORMAT = (
    "<green>{time:YYYY-MM-DDTHH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "{extra[agent]: <15} | "
    "run={extra[run_id]} | "
    "corr={extra[correlation_id]} | "
    "{extra[module]} | "
    "<level>{message}</level>"
)

_config_lock = threading.RLock()
_metrics_server_lock = threading.RLock()
_metrics_server: Optional[ThreadingHTTPServer] = None
_metrics_thread: Optional[threading.Thread] = None


def _json_default(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_default(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_default(val) for key, val in value.items()}
    return repr(value)


def _infer_agent(record: Dict[str, Any]) -> str:
    module_name = record.get("name") or record.get("module") or "system"
    if module_name.startswith("agents"):
        parts = module_name.split(".")
        if len(parts) >= 2:
            return parts[1]
    return "system"


def _get_correlation_from_context() -> Optional[str]:
    try:
        return _CORRELATION_ID.get()
    except LookupError:  # pragma: no cover - defensive, ContextVar always set
        return None


def _patch_record(record: Dict[str, Any]) -> None:
    extra = record["extra"]
    extra.setdefault("run_id", RUN_ID)

    correlation = extra.get("correlation_id") or _get_correlation_from_context()
    extra["correlation_id"] = correlation or "-"

    agent = extra.get("agent") or extra.get("agent_id")
    if not agent:
        agent = _infer_agent(record)
    extra["agent"] = agent

    module_name = extra.get("module") or record.get("name") or record.get("module") or "unknown"
    extra["module"] = module_name


def _json_sink(message) -> None:  # pragma: no cover - exercised in integration tests
    record = message.record
    extra = record["extra"]

    payload: Dict[str, Any] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": extra.get("module"),
        "agent": extra.get("agent"),
        "run_id": extra.get("run_id"),
        "correlation_id": extra.get("correlation_id"),
    }

    remaining_extra = {
        key: value
        for key, value in extra.items()
        if key not in {"module", "agent", "run_id", "correlation_id"}
    }
    if remaining_extra:
        payload["extra"] = _json_default(remaining_extra)

    if record["exception"]:
        payload["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
        }

    sys.stderr.write(json.dumps(payload, default=_json_default, ensure_ascii=False) + "\n")


def configure_logging(*, log_format: Optional[str] = None, log_level: Optional[str] = None) -> None:
    """Configure loguru logging with structured and human-readable sinks."""
    with _config_lock:
        logger.remove()

        format_choice = (log_format or os.getenv("LOG_FORMAT", "text")).strip().lower()
        if format_choice not in _LOG_FORMAT_CHOICES:
            format_choice = "text"

        level = (log_level or os.getenv("LOG_LEVEL", "INFO")).strip().upper()
        if not level:
            level = "INFO"

        logger.configure(extra={"run_id": RUN_ID}, patcher=_patch_record)

        diagnose = os.getenv("LOG_DIAGNOSE", "false").strip().lower() in {"1", "true", "yes", "on"}

        if format_choice in {"text", "both"}:
            logger.add(
                sys.stderr,
                format=_TEXT_FORMAT,
                level=level,
                diagnose=diagnose,
                backtrace=False,
            )

        if format_choice in {"json", "both"}:
            logger.add(
                _json_sink,
                level=level,
                diagnose=diagnose,
                backtrace=False,
            )


def get_correlation_id() -> Optional[str]:
    """Return the current correlation ID, if any."""
    return _get_correlation_from_context()


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Set the active correlation ID for the current context."""
    _CORRELATION_ID.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _CORRELATION_ID.set(None)


def new_correlation_id(prefix: Optional[str] = None) -> str:
    """Generate and set a new correlation ID."""
    suffix = uuid.uuid4().hex
    correlation_id = f"{prefix}-{suffix}" if prefix else suffix
    set_correlation_id(correlation_id)
    return correlation_id


@contextmanager
def correlation_context(correlation_id: Optional[str]) -> Any:
    """Context manager that sets a correlation ID for the block duration."""
    token = _CORRELATION_ID.set(correlation_id)
    try:
        yield
    finally:
        _CORRELATION_ID.reset(token)


class MetricsRegistry:
    """Lightweight metrics aggregator for in-process observability."""

    def __init__(self, *, max_samples: int = 500):
        self._lock = threading.RLock()
        self._max_samples = max_samples
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._retrieval_hits: Dict[str, int] = {}
        self._synthesis_tokens: Dict[str, int] = {}

    def clear(self) -> None:
        with self._lock:
            self._agents.clear()
            self._retrieval_hits.clear()
            self._synthesis_tokens.clear()

    def record_request(self, agent: str, status: str, latency_seconds: float) -> None:
        agent_key = agent or "unknown"
        normalized_status = status.lower()
        success = normalized_status == "success"
        error = normalized_status in {"error", "failed", "failure"}

        with self._lock:
            stats = self._agents.setdefault(
                agent_key,
                {
                    "request_count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "latencies": [],
                },
            )
            stats["request_count"] += 1
            if success:
                stats["success_count"] += 1
            if error:
                stats["error_count"] += 1

            if latency_seconds is not None:
                stats["latencies"].append(max(latency_seconds, 0.0))
                if len(stats["latencies"]) > self._max_samples:
                    stats["latencies"] = stats["latencies"][-self._max_samples :]

    def record_retrieval_hits(self, agent: str, hits: int) -> None:
        with self._lock:
            self._retrieval_hits[agent or "unknown"] = self._retrieval_hits.get(agent or "unknown", 0) + max(hits, 0)

    def record_synthesis_tokens(self, agent: str, tokens: int) -> None:
        with self._lock:
            self._synthesis_tokens[agent or "unknown"] = self._synthesis_tokens.get(agent or "unknown", 0) + max(tokens, 0)

    def _compute_percentile(self, values: List[float], percentile: float) -> Optional[float]:
        if not values:
            return None
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_values[int(k)]
        return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            agents_snapshot: Dict[str, Any] = {}
            totals = {"requests": 0, "success": 0, "errors": 0}

            for agent, stats in self._agents.items():
                latencies = stats.get("latencies", [])
                p50 = self._compute_percentile(latencies, 50)
                p95 = self._compute_percentile(latencies, 95)
                agents_snapshot[agent] = {
                    "requests": stats.get("request_count", 0),
                    "success": stats.get("success_count", 0),
                    "errors": stats.get("error_count", 0),
                    "latency_p50_ms": round(p50 * 1000, 3) if p50 is not None else None,
                    "latency_p95_ms": round(p95 * 1000, 3) if p95 is not None else None,
                }
                totals["requests"] += stats.get("request_count", 0)
                totals["success"] += stats.get("success_count", 0)
                totals["errors"] += stats.get("error_count", 0)

            retrieval_total = sum(self._retrieval_hits.values())
            synthesis_total = sum(self._synthesis_tokens.values())

            return {
                "run_id": RUN_ID,
                "timestamp": time.time(),
                "totals": totals,
                "agents": agents_snapshot,
                "retrieval": {
                    "total_hits": retrieval_total,
                    "per_agent": dict(self._retrieval_hits),
                },
                "synthesis": {
                    "tokens_total": synthesis_total,
                    "per_agent": dict(self._synthesis_tokens),
                },
            }


metrics_registry = MetricsRegistry()


class _MetricsRequestHandler(BaseHTTPRequestHandler):  # pragma: no cover - exercised via tests
    server_version = "ObservabilityMetrics/1.0"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path.rstrip("/") == "/metrics":
            payload = json.dumps(metrics_registry.snapshot(), default=_json_default, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: D401, N802
        """Route server access logs through loguru."""
        logger.debug(
            "Metrics endpoint access",
            extra={"client": self.client_address[0], "path": getattr(self, "path", "")},
        )


def start_metrics_server(*, port: Optional[int] = None, host: Optional[str] = None) -> int:
    """Start the lightweight metrics HTTP server."""
    global _metrics_server, _metrics_thread
    with _metrics_server_lock:
        if _metrics_server is not None:
            return int(_metrics_server.server_address[1])

        bind_host = host or os.getenv("METRICS_HOST", "127.0.0.1")
        bind_port = port if port is not None else int(os.getenv("METRICS_PORT", "9100"))

        server = ThreadingHTTPServer((bind_host, bind_port), _MetricsRequestHandler)
        _metrics_server = server
        _metrics_thread = threading.Thread(target=server.serve_forever, name="metrics-server", daemon=True)
        _metrics_thread.start()

        logger.info("Metrics server started", extra={"host": bind_host, "port": server.server_address[1]})
        return int(server.server_address[1])


def stop_metrics_server() -> None:
    """Stop the metrics HTTP server if it is running."""
    global _metrics_server, _metrics_thread
    with _metrics_server_lock:
        if _metrics_server is None:
            return
        logger.info("Stopping metrics server")
        _metrics_server.shutdown()
        _metrics_server.server_close()
        _metrics_server = None
        _metrics_thread = None


def is_metrics_server_running() -> bool:
    with _metrics_server_lock:
        return _metrics_server is not None


configure_logging()

if os.getenv("ENABLE_METRICS", "false").strip().lower() in {"1", "true", "yes", "on"}:
    try:
        start_metrics_server()
    except OSError as exc:  # pragma: no cover - dependent on runtime environment
        logger.warning("Failed to start metrics server", extra={"error": str(exc)})


__all__ = [
    "RUN_ID",
    "MetricsRegistry",
    "configure_logging",
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "new_correlation_id",
    "correlation_context",
    "metrics_registry",
    "start_metrics_server",
    "stop_metrics_server",
    "is_metrics_server_running",
]
