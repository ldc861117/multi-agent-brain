"""Demo utilities packaged for the multi-agent-brain project."""

from .runner import MultiAgentDemo
from .modes import DemoMode, DemoRunner
from .output import DemoOutput
from .setup import check_environment, DemoEnvironmentError

__all__ = [
    "MultiAgentDemo",
    "DemoMode",
    "DemoRunner",
    "DemoOutput",
    "check_environment",
    "DemoEnvironmentError",
]
