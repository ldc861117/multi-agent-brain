"""Operator dashboard CLI/TUI for the multi-agent-brain project.

This module provides a lightweight Rich-powered dashboard that surfaces
agent metadata, recent task activity, log tails, and the resolved
configuration snapshot used by the agents. It is intentionally
read-only, requires no additional services, and works entirely offline
by inspecting local configuration files and log outputs.

Launch via ``python -m tools.operator`` or the ``make operator`` target.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import yaml
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from utils.config_manager import get_config_manager


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def truncate(value: str, *, limit: int = 80) -> str:
    """Truncate ``value`` to ``limit`` characters, appending an ellipsis."""

    if len(value) <= limit:
        return value
    return value[: limit - 1] + "\u2026"


def redact(value: Optional[str]) -> str:
    """Return a redacted representation for secrets (API keys, etc.)."""

    if not value:
        return "<not set>"
    return "[redacted]"


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Best-effort conversion of timestamps to :class:`datetime`."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value))
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


def format_duration(value: Optional[float]) -> str:
    """Human-readable formatting for execution durations."""

    if value is None:
        return "-"
    if value < 1.0:
        return f"{value * 1000:.0f} ms"
    return f"{value:.2f} s"


def display_timestamp(value: Optional[datetime]) -> str:
    """Render :class:`datetime` instances as compact strings."""

    if not value:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class AgentSummary:
    """Resolved metadata about an agent entrypoint."""

    name: str
    description: str
    entrypoint: str
    status: str
    chat_model: Optional[str]
    chat_provider: Optional[str]
    embedding_model: Optional[str]
    embedding_provider: Optional[str]
    notes: Optional[str] = None


@dataclass
class TaskRunSummary:
    """Aggregated information about a task or collaboration run."""

    run_id: str
    agent: Optional[str] = None
    status: str = "unknown"
    started_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    last_error: Optional[str] = None
    log_path: Optional[Path] = None


# ---------------------------------------------------------------------------
# Data providers
# ---------------------------------------------------------------------------


class AgentDataSource:
    """Resolve agent metadata from ``config.yaml`` and ConfigManager."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config_manager = get_config_manager()

    def _load_yaml(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        except Exception:
            return {}

    def load(self) -> List[AgentSummary]:
        data = self._load_yaml()
        channels = data.get("channels") or {}

        summaries: List[AgentSummary] = []
        for agent_name in sorted(channels.keys()):
            channel = channels[agent_name] or {}
            entrypoint = channel.get("entrypoint", "<missing>")
            description = channel.get("description", "(no description)")
            status = "ready"
            notes: List[str] = []

            chat_model: Optional[str] = None
            chat_provider: Optional[str] = None
            embedding_model: Optional[str] = None
            embedding_provider: Optional[str] = None

            try:
                agent_config = self._config_manager.get_agent_config(agent_name)
                chat_model = agent_config.chat_api.model
                chat_provider = getattr(agent_config.chat_api.provider, "value", str(agent_config.chat_api.provider))
                embedding_model = agent_config.embedding_api.model
                embedding_provider = getattr(
                    agent_config.embedding_api.provider, "value", str(agent_config.embedding_api.provider)
                )
            except Exception as exc:  # pragma: no cover - defensive for offline use
                status = "config-error"
                notes.append(f"config:{exc}")

            try:
                module_path, class_name = entrypoint.split(":")
                module = importlib.import_module(module_path)
                agent_cls = getattr(module, class_name)
                description = getattr(agent_cls, "description", description)
            except Exception as exc:
                status = "import-error" if status == "ready" else status
                notes.append(f"import:{exc}")

            summaries.append(
                AgentSummary(
                    name=agent_name,
                    description=truncate(str(description), limit=96),
                    entrypoint=entrypoint,
                    status=status if notes else "ready",
                    chat_model=chat_model,
                    chat_provider=chat_provider,
                    embedding_model=embedding_model,
                    embedding_provider=embedding_provider,
                    notes="; ".join(notes) if notes else None,
                )
            )

        return summaries


class TaskRunDataSource:
    """Derive recent task runs from structured log lines or JSONL history."""

    RUN_ID_PATTERN = re.compile(r"(?:run[_-]?id|interaction_id)=(?P<run>[A-Za-z0-9_-]+)")
    AGENT_PATTERN = re.compile(r"agent(?:_id)?=(?P<agent>[A-Za-z0-9_-]+)")
    STATUS_PATTERN = re.compile(r"(?:status|state)=(?P<status>[A-Za-z0-9_-]+)")
    DURATION_PATTERN = re.compile(r"(?:duration|latency)=(?P<duration>\d+(?:\.\d+)?)")
    TIMESTAMP_PATTERN = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2} [\d:.]+)")

    def __init__(self, sources: Sequence[Path], *, limit: int = 8):
        self.sources = [Path(source) for source in sources]
        self.limit = limit

    def load(self) -> List[TaskRunSummary]:
        runs: Dict[str, TaskRunSummary] = {}

        for path in self.sources:
            if not path.exists() or not path.is_file():
                continue
            for record in self._records_from_path(path):
                run_id = record.get("run_id")
                if not run_id:
                    continue
                summary = runs.get(run_id)
                if not summary:
                    summary = TaskRunSummary(run_id=run_id)
                    runs[run_id] = summary
                if record.get("agent") and not summary.agent:
                    summary.agent = record["agent"]
                if record.get("status"):
                    summary.status = record["status"]
                if record.get("duration") is not None:
                    summary.duration_seconds = record["duration"]
                if record.get("error"):
                    summary.last_error = truncate(record["error"], limit=80)
                if record.get("timestamp"):
                    timestamp = record["timestamp"]
                    if not summary.started_at or (timestamp and timestamp < summary.started_at):
                        summary.started_at = timestamp
                summary.log_path = summary.log_path or path

        sorted_runs = sorted(
            runs.values(), key=lambda item: item.started_at or datetime.min, reverse=True
        )
        return sorted_runs[: self.limit]

    # ------------------------------------------------------------------

    def _records_from_path(self, path: Path) -> Iterable[Dict[str, Any]]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            record = self._parse_line(line)
            if record:
                yield record

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        stripped = line.strip()
        if not stripped:
            return None

        # Attempt JSON first
        if stripped.startswith("{"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                run_id = payload.get("run_id") or payload.get("interaction_id") or payload.get("task_id")
                if not run_id:
                    return None
                timestamp = parse_timestamp(
                    payload.get("timestamp")
                    or payload.get("created_at")
                    or payload.get("time")
                    or payload.get("ts")
                )
                duration = payload.get("duration") or payload.get("latency")
                if isinstance(duration, str):
                    try:
                        duration = float(duration)
                    except ValueError:
                        duration = None
                elif isinstance(duration, int):
                    duration = float(duration)
                return {
                    "run_id": str(run_id),
                    "agent": payload.get("agent") or payload.get("agent_id"),
                    "status": str(payload.get("status") or payload.get("state") or "unknown").lower(),
                    "timestamp": timestamp,
                    "duration": duration,
                    "error": payload.get("error") or payload.get("error_message"),
                }

        # Fallback to regex heuristics
        match = self.RUN_ID_PATTERN.search(stripped)
        if not match:
            return None
        run_id = match.group("run")
        agent_match = self.AGENT_PATTERN.search(stripped)
        status_match = self.STATUS_PATTERN.search(stripped)
        duration_match = self.DURATION_PATTERN.search(stripped)
        ts_match = self.TIMESTAMP_PATTERN.search(stripped)

        duration_value: Optional[float] = None
        if duration_match:
            try:
                duration_value = float(duration_match.group("duration"))
            except ValueError:
                duration_value = None

        timestamp_value = parse_timestamp(ts_match.group("ts")) if ts_match else None

        error_fragment: Optional[str] = None
        if "error" in stripped.lower():
            error_fragment = stripped

        return {
            "run_id": run_id,
            "agent": agent_match.group("agent") if agent_match else None,
            "status": status_match.group("status").lower() if status_match else "unknown",
            "timestamp": timestamp_value,
            "duration": duration_value,
            "error": error_fragment,
        }


class ConfigSnapshot:
    """Render the resolved configuration tree for display."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config_manager = get_config_manager()

    def _load_yaml(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with self.config_path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        except Exception:
            return {}

    def render(self) -> Tree:
        root_title = (
            f"Configuration snapshot ({self.config_path})"
            if self.config_path.exists()
            else "Configuration snapshot (defaults)"
        )
        tree = Tree(f"[bold]{root_title}[/bold]")

        try:
            global_config = self._config_manager.get_global_config()
        except Exception as exc:  # pragma: no cover - defensive guard
            tree.add(f"[red]Failed to resolve configuration: {exc}[/red]")
            return tree

        chat_branch = tree.add("[cyan]Chat API[/cyan]")
        chat_branch.add(f"provider: {getattr(global_config.chat_api.provider, 'value', global_config.chat_api.provider)}")
        chat_branch.add(f"model: {global_config.chat_api.model}")
        chat_branch.add(f"base_url: {global_config.chat_api.base_url or 'default'}")
        chat_branch.add(f"timeout: {global_config.chat_api.timeout}s")
        chat_branch.add(f"api_key: {redact(global_config.chat_api.api_key)}")

        embedding_branch = tree.add("[magenta]Embedding API[/magenta]")
        embedding_branch.add(
            f"provider: {getattr(global_config.embedding_api.provider, 'value', global_config.embedding_api.provider)}"
        )
        embedding_branch.add(f"model: {global_config.embedding_api.model}")
        embedding_branch.add(f"dimension: {global_config.embedding_api.dimension}")
        embedding_branch.add(f"base_url: {global_config.embedding_api.base_url or 'default'}")
        embedding_branch.add(f"api_key: {redact(global_config.embedding_api.api_key)}")

        overrides_branch = tree.add("[green]Agent overrides[/green]")
        yaml_data = self._load_yaml()
        overrides = (yaml_data.get("api_config") or {}).get("agent_overrides") or {}

        if not overrides:
            overrides_branch.add("(none defined)")
        else:
            for agent_name in sorted(overrides.keys()):
                try:
                    agent_config = self._config_manager.get_agent_config(agent_name)
                    verbose_flag = overrides.get(agent_name, {}).get("answer_verbose", False)
                    overrides_branch.add(
                        f"{agent_name}: chat={agent_config.chat_api.model}"
                        f" ({getattr(agent_config.chat_api.provider, 'value', agent_config.chat_api.provider)})"
                        f" | embedding={agent_config.embedding_api.model}"
                        f" ({getattr(agent_config.embedding_api.provider, 'value', agent_config.embedding_api.provider)},"
                        f" {agent_config.embedding_api.dimension}d)"
                        f" | verbose={'yes' if verbose_flag else 'no'}"
                    )
                except Exception as exc:
                    overrides_branch.add(f"[red]{agent_name}: failed to resolve ({exc})[/red]")

        return tree


class LogTailer:
    """Tail log files with basic filtering and colouring."""

    def __init__(
        self,
        path: Path,
        *,
        level: str = "any",
        agent_filter: Optional[str] = None,
        run_filter: Optional[str] = None,
        correlation_filter: Optional[str] = None,
        limit: int = 30,
    ):
        self.path = Path(path)
        self.level = level.lower()
        self.agent_filter = agent_filter.lower() if agent_filter else None
        self.run_filter = run_filter.lower() if run_filter else None
        self.correlation_filter = correlation_filter.lower() if correlation_filter else None
        self.limit = limit

    def tail(self) -> List[str]:
        if not self.path.exists():
            return [f"Log file {self.path} not found"]

        try:
            with self.path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
        except Exception as exc:  # pragma: no cover - IO failure shading
            return [f"Failed to read log file: {exc}"]

        matched: List[str] = []
        for line in reversed(lines):
            if len(matched) >= self.limit:
                break
            if self._matches_filters(line):
                matched.append(line.rstrip("\n"))

        matched.reverse()
        return matched

    # ------------------------------------------------------------------

    def _matches_filters(self, line: str) -> bool:
        lowered = line.lower()
        if self.agent_filter and self.agent_filter not in lowered:
            return False
        if self.run_filter and self.run_filter not in lowered:
            return False
        if self.correlation_filter and self.correlation_filter not in lowered:
            return False
        if self.level != "any":
            if self.level == "error" and "error" not in lowered:
                return False
            if self.level == "warning" and not ("warning" in lowered or "warn" in lowered):
                return False
            if self.level == "info" and "info" not in lowered:
                return False
            if self.level == "debug" and "debug" not in lowered:
                return False
        return True

    def style_for_line(self, line: str) -> str:
        lowered = line.lower()
        if "error" in lowered:
            return "bold red"
        if "warning" in lowered or "warn" in lowered:
            return "yellow"
        if "debug" in lowered:
            return "dim"
        if "success" in lowered or "started" in lowered:
            return "green"
        return "white"


# ---------------------------------------------------------------------------
# Dashboard renderer
# ---------------------------------------------------------------------------


class OperatorDashboard:
    """Render a Rich layout with agent status, runs, logs, and config."""

    def __init__(
        self,
        *,
        config_path: Path,
        log_tailer: LogTailer,
        task_source: TaskRunDataSource,
        refresh_interval: float = 2.0,
        console: Optional[Console] = None,
    ):
        self.config_path = Path(config_path)
        self.log_tailer = log_tailer
        self.task_source = task_source
        self.refresh_interval = max(refresh_interval, 0.5)
        self.console = console or Console()
        self.agent_source = AgentDataSource(self.config_path)
        self.config_snapshot = ConfigSnapshot(self.config_path)

    # ------------------------------------------------------------------

    def run(self) -> None:
        self.console.print("[bold cyan]Launching operator dashboard[/bold cyan]")
        self.console.print("Press [bold]Ctrl+C[/bold] to exit.\n")

        try:
            with Live(
                self._render_layout(),
                console=self.console,
                refresh_per_second=4,
                screen=True,
                transient=False,
            ) as live:
                while True:
                    time.sleep(self.refresh_interval)
                    live.update(self._render_layout())
        except KeyboardInterrupt:
            self.console.print("\n[bold cyan]Dashboard closed by user.[/bold cyan]")

    # ------------------------------------------------------------------

    def _render_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="upper", ratio=2),
            Layout(name="logs", ratio=1),
        )

        layout["upper"].split_row(
            Layout(name="agents", ratio=2),
            Layout(name="right", ratio=3),
        )

        layout["right"].split_column(
            Layout(name="tasks", ratio=2),
            Layout(name="config", ratio=1),
        )

        layout["agents"].update(self._render_agents_panel())
        layout["tasks"].update(self._render_tasks_panel())
        layout["config"].update(self._render_config_panel())
        layout["logs"].update(self._render_logs_panel())

        return layout

    def _render_agents_panel(self) -> Panel:
        table = Table(
            "Agent",
            "Status",
            "Chat model",
            "Embedding model",
            "Notes",
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=True,
        )

        agents = self.agent_source.load()
        if not agents:
            table.add_row("(none)", "-", "-", "-", "Configure channels in config.yaml")
        else:
            for summary in agents:
                chat_repr = (
                    f"{summary.chat_model or '-'}\n[{summary.chat_provider or '-'}]"
                    if summary.chat_model
                    else "-"
                )
                embedding_repr = (
                    f"{summary.embedding_model or '-'}\n[{summary.embedding_provider or '-'}]"
                    if summary.embedding_model
                    else "-"
                )

                status_style = {
                    "ready": "green",
                    "config-error": "yellow",
                    "import-error": "red",
                }.get(summary.status, "white")

                table.add_row(
                    summary.name,
                    f"[{status_style}]{summary.status}[/]",
                    chat_repr,
                    embedding_repr,
                    summary.notes or summary.description,
                )

        return Panel(table, title="Agents", border_style="cyan", padding=(1, 1))

    def _render_tasks_panel(self) -> Panel:
        table = Table(
            "Run ID",
            "Agent",
            "Status",
            "Started",
            "Duration",
            "Last error",
            "Log",
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=True,
        )

        runs = self.task_source.load()
        if not runs:
            table.add_row("-", "-", "-", "-", "-", "No structured runs captured yet", "-")
        else:
            for run in runs:
                table.add_row(
                    truncate(run.run_id, limit=18),
                    run.agent or "-",
                    run.status,
                    display_timestamp(run.started_at),
                    format_duration(run.duration_seconds),
                    truncate(run.last_error or "-", limit=40),
                    run.log_path.name if run.log_path else "-",
                )

        return Panel(table, title="Recent task runs", border_style="magenta", padding=(1, 1))

    def _render_config_panel(self) -> Panel:
        tree = self.config_snapshot.render()
        return Panel(tree, title="Resolved configuration", border_style="green", padding=(1, 1))

    def _render_logs_panel(self) -> Panel:
        lines = self.log_tailer.tail()
        if not lines:
            content = Text("No log entries", style="dim")
        else:
            content = Text()
            for line in lines:
                content.append(line, style=self.log_tailer.style_for_line(line))
                content.append("\n")
        title = f"Log tail ({self.log_tailer.path})"
        return Panel(content, title=title, border_style="blue", padding=(1, 1))


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operator dashboard for multi-agent-brain")
    parser.add_argument(
        "--config",
        default="config.yaml",
        type=Path,
        help="Path to the configuration YAML file (default: config.yaml)",
    )
    parser.add_argument(
        "--log-file",
        default="openagents.log",
        type=Path,
        help="Primary log file to tail (default: openagents.log)",
    )
    parser.add_argument(
        "--refresh",
        default=2.0,
        type=float,
        help="Refresh interval in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--log-level",
        choices=["any", "info", "warning", "error", "debug"],
        default="any",
        help="Filter log tail by level heuristic",
    )
    parser.add_argument(
        "--filter-agent",
        dest="filter_agent",
        help="Filter log lines containing the given agent identifier",
    )
    parser.add_argument(
        "--filter-run",
        dest="filter_run",
        help="Filter log lines containing the given run/correlation identifier",
    )
    parser.add_argument(
        "--filter-correlation",
        dest="filter_correlation",
        help="Filter log lines by correlation identifier substring",
    )
    parser.add_argument(
        "--task-log",
        action="append",
        dest="task_logs",
        type=Path,
        help="Optional JSONL or log file containing structured task history (repeatable)",
    )
    parser.add_argument(
        "--max-log-lines",
        type=int,
        default=30,
        help="Maximum number of log lines to display (default: 30)",
    )
    return parser.parse_args(argv)


def discover_task_sources(args: argparse.Namespace) -> List[Path]:
    explicit = args.task_logs or []
    if explicit:
        return list(dict.fromkeys(explicit))

    # Fallback discovery for common locations
    candidates = [
        Path("logs/task_runs.jsonl"),
        Path("data/task_runs.jsonl"),
        Path("workspace/task_runs.jsonl"),
        args.log_file,
    ]
    unique: List[Path] = []
    for candidate in candidates:
        if candidate.exists() and candidate not in unique:
            unique.append(candidate)
    return unique


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)

    log_tailer = LogTailer(
        path=args.log_file,
        level=args.log_level,
        agent_filter=args.filter_agent,
        run_filter=args.filter_run,
        correlation_filter=args.filter_correlation,
        limit=args.max_log_lines,
    )

    task_sources = TaskRunDataSource(discover_task_sources(args), limit=8)

    dashboard = OperatorDashboard(
        config_path=args.config,
        log_tailer=log_tailer,
        task_source=task_sources,
        refresh_interval=args.refresh,
    )
    dashboard.run()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main(sys.argv[1:])
