"""Compatibility shim to keep legacy invocations working.

Pytest-driven CI calls `pytest test_shared_memory.py`; the real tests live in
`tests/test_shared_memory.py`.
"""

from tests.test_shared_memory import *  # noqa: F401,F403
