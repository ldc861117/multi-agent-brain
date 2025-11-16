#!/usr/bin/env python3
"""Test imports to identify issues."""

print("Testing imports...")

try:
    print("1. Testing agents.types import...")
    from agents.types import ExpertKind
    print(f"   ✓ ExpertKind imported: {ExpertKind}")
    
    print("2. Testing ExpertKind.coerce()...")
    result = ExpertKind.coerce("python")
    print(f"   ✓ ExpertKind.coerce('python') = {result}")
    
    print("3. Testing ExpertKind._ALIASES...")
    print(f"   ✓ _ALIASES type: {type(ExpertKind._ALIASES)}")
    print(f"   ✓ _ALIASES content: {dict(ExpertKind._ALIASES)}")
    
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    print("4. Testing browser_tool import...")
    from tools.browser_tool import BrowserTool
    print(f"   ✓ BrowserTool imported")
    
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    print("5. Testing config loading...")
    from utils.config_manager import get_browser_tool_config
    config = get_browser_tool_config("demo")
    print(f"   ✓ Config loaded: search_provider={config.search_provider}")
    print(f"   ✓ API key set: {config.search_api_key is not None}")
    if config.search_api_key:
        print(f"   ✓ API key preview: {config.search_api_key[:8]}...")
    
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

try:
    print("6. Testing dependencies...")
    import httpx
    print(f"   ✓ httpx version: {httpx.__version__}")
    
    import bs4
    print(f"   ✓ beautifulsoup4 version: {bs4.__version__}")
    
    from pymilvus import __version__ as pymilvus_version
    print(f"   ✓ pymilvus version: {pymilvus_version}")
    
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\nAll tests completed!")
