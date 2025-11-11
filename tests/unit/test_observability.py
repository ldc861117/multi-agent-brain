from __future__ import annotations

import json
import urllib.request

from utils.observability import (
    MetricsRegistry,
    clear_correlation_id,
    correlation_context,
    get_correlation_id,
    metrics_registry,
    start_metrics_server,
    stop_metrics_server,
)


def test_metrics_registry_snapshot_includes_percentiles() -> None:
    registry = MetricsRegistry(max_samples=5)

    registry.record_request("coordination", "success", 0.1)
    registry.record_request("coordination", "error", 0.4)
    registry.record_request("python_expert", "success", 0.05)
    registry.record_retrieval_hits("coordination", 3)
    registry.record_synthesis_tokens("coordination", 120)

    snapshot = registry.snapshot()

    assert snapshot["totals"]["requests"] == 3
    assert snapshot["totals"]["success"] == 2
    assert snapshot["totals"]["errors"] == 1

    coordination_metrics = snapshot["agents"]["coordination"]
    assert coordination_metrics["requests"] == 2
    assert coordination_metrics["errors"] == 1
    assert coordination_metrics["latency_p50_ms"] is not None
    assert coordination_metrics["latency_p95_ms"] is not None
    assert coordination_metrics["latency_p95_ms"] >= coordination_metrics["latency_p50_ms"]

    assert snapshot["retrieval"]["total_hits"] == 3
    assert snapshot["synthesis"]["tokens_total"] == 120


def test_metrics_endpoint_returns_snapshot_json() -> None:
    stop_metrics_server()
    metrics_registry.clear()
    metrics_registry.record_request("coordination", "success", 0.2)

    port = start_metrics_server(port=0, host="127.0.0.1")
    payload = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=2) as response:
            assert response.status == 200
            payload = json.loads(response.read())
    finally:
        stop_metrics_server()
        metrics_registry.clear()

    assert payload is not None
    assert payload["totals"]["requests"] == 1
    assert payload["agents"]["coordination"]["requests"] == 1


def test_correlation_context_sets_and_clears() -> None:
    clear_correlation_id()
    assert get_correlation_id() is None

    with correlation_context("test-corr-id"):
        assert get_correlation_id() == "test-corr-id"

    assert get_correlation_id() is None
