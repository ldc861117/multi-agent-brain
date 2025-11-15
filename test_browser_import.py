#!/usr/bin/env python3
"""Quick test to verify browser tool imports."""

import sys

try:
    print("Testing imports...")
    
    # Test config imports
    from utils.openai_client import BrowserToolConfig
    print("✓ BrowserToolConfig imported")
    
    # Test config manager
    from utils.config_manager import get_browser_tool_config
    print("✓ get_browser_tool_config imported")
    
    # Test browser tool
    from tools.browser_tool import (
        BrowserTool,
        BrowserResult,
        SearchResult,
        PageContent,
        BrowserToolError,
        SearchProviderError,
        NavigationError,
        ExtractionError,
        RateLimitError,
    )
    print("✓ BrowserTool classes imported")
    
    # Test config creation
    config = BrowserToolConfig(
        enabled=True,
        search_provider="duckduckgo",
        search_api_key=None
    )
    print(f"✓ Config created: provider={config.search_provider}")
    
    print("\n✅ All imports successful!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
