#!/usr/bin/env python3
"""Simple synchronous import test."""

print("Testing basic imports...")

print("\n1. Testing agents.types.ExpertKind...")
from agents.types import ExpertKind
print(f"   ✓ ExpertKind imported")

print("\n2. Testing ExpertKind._ALIASES...")
print(f"   Type: {type(ExpertKind._ALIASES)}")
print(f"   Content: {dict(ExpertKind._ALIASES)}")

print("\n3. Testing ExpertKind.coerce()...")
test_cases = [
    ("python", "PYTHON_EXPERT"),
    ("milvus", "MILVUS_EXPERT"),
    ("router", "COORDINATION"),
    ("unknown", "UNKNOWN"),
]
for input_val, expected_name in test_cases:
    result = ExpertKind.coerce(input_val)
    print(f"   ExpertKind.coerce('{input_val}') = {result.name} (expected {expected_name})")
    if result.name != expected_name:
        print(f"   ✗ MISMATCH!")
        exit(1)

print("\n4. Testing tools.browser_tool import...")
from tools.browser_tool import BrowserTool
print(f"   ✓ BrowserTool imported")

print("\n5. Testing utils.config_manager...")
from utils.config_manager import get_browser_tool_config
print(f"   ✓ get_browser_tool_config imported")

print("\n6. Testing dependency imports...")
try:
    import httpx
    print(f"   ✓ httpx: {httpx.__version__}")
except ImportError as e:
    print(f"   ✗ httpx: {e}")

try:
    import bs4
    print(f"   ✓ beautifulsoup4: {bs4.__version__}")
except ImportError as e:
    print(f"   ✗ beautifulsoup4: {e}")

try:
    from pymilvus import __version__ as pv
    print(f"   ✓ pymilvus: {pv}")
except ImportError as e:
    print(f"   ✗ pymilvus: {e}")

print("\n✓ All imports successful!")
