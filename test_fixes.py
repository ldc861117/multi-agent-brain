#!/usr/bin/env python3
"""Test that all the fixes work correctly."""

import asyncio
import os
import sys

# Ensure project root is in path
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_expert_kind_coercion():
    """Test ExpertKind.coerce() fix."""
    print("\n=== Testing ExpertKind.coerce() ===")
    from agents.types import ExpertKind
    
    test_cases = [
        ("python", ExpertKind.PYTHON_EXPERT),
        ("milvus", ExpertKind.MILVUS_EXPERT),
        ("devops", ExpertKind.DEVOPS_EXPERT),
        ("router", ExpertKind.COORDINATION),
        ("entry", ExpertKind.GENERAL),
        ("gateway", ExpertKind.GENERAL),
        ("python_expert", ExpertKind.PYTHON_EXPERT),
        ("coordination", ExpertKind.COORDINATION),
        ("unknown_value", ExpertKind.UNKNOWN),
        (None, ExpertKind.UNKNOWN),
    ]
    
    all_passed = True
    for input_value, expected in test_cases:
        result = ExpertKind.coerce(input_value)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} ExpertKind.coerce({input_value!r}) = {result} (expected {expected})")
    
    if all_passed:
        print("✓ All ExpertKind coercion tests passed!")
        return True
    else:
        print("✗ Some ExpertKind coercion tests failed!")
        return False


def test_dependencies():
    """Test that all required dependencies are available."""
    print("\n=== Testing Dependencies ===")
    
    dependencies = [
        ("httpx", "httpx"),
        ("beautifulsoup4", "bs4"),
        ("pymilvus", "pymilvus"),
        ("playwright", "playwright"),
    ]
    
    all_present = True
    for name, module in dependencies:
        try:
            __import__(module)
            print(f"  ✓ {name} installed")
        except ImportError:
            print(f"  ✗ {name} NOT installed")
            all_present = False
    
    if all_present:
        print("✓ All dependencies available!")
        return True
    else:
        print("✗ Some dependencies missing!")
        return False


async def test_browser_tool_initialization():
    """Test BrowserTool initialization with and without API key."""
    print("\n=== Testing BrowserTool Initialization ===")
    
    # Save original env vars
    original_tavily = os.environ.get("TAVILY_API_KEY")
    original_browser = os.environ.get("BROWSER_SEARCH_API_KEY")
    
    try:
        # Test 1: Without API key (should fallback to DuckDuckGo)
        print("\n  Test 1: Initialization without API key (should use fallback)")
        if "TAVILY_API_KEY" in os.environ:
            del os.environ["TAVILY_API_KEY"]
        if "BROWSER_SEARCH_API_KEY" in os.environ:
            del os.environ["BROWSER_SEARCH_API_KEY"]
        
        from tools.browser_tool import BrowserTool
        from utils.config_manager import reload_config
        reload_config()
        
        try:
            browser = BrowserTool(agent_name="test_demo")
            print(f"    ✓ BrowserTool initialized successfully")
            print(f"    ✓ Search engine type: {type(browser.search_engine).__name__}")
            
            # Test a simple search
            print("\n  Test 2: Simple DuckDuckGo search")
            result = await browser.search("Python async", max_results=3)
            print(f"    ✓ Search completed: {len(result.search_results)} results")
            if result.search_results:
                print(f"    ✓ First result: {result.search_results[0].title}")
            
            return True
        except Exception as e:
            print(f"    ✗ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    finally:
        # Restore original env vars
        if original_tavily:
            os.environ["TAVILY_API_KEY"] = original_tavily
        if original_browser:
            os.environ["BROWSER_SEARCH_API_KEY"] = original_browser


def test_registry_bootstrap():
    """Test registry bootstrap with ExpertKind coercion."""
    print("\n=== Testing Registry Bootstrap ===")
    
    try:
        from utils.config_manager import get_registry_bootstrap
        
        bootstrap = get_registry_bootstrap()
        print(f"  ✓ Registry bootstrap loaded: {len(bootstrap)} entries")
        
        for name, config in bootstrap.items():
            print(f"    - {name}: {config.get('entrypoint', 'N/A')}")
        
        # Test that expert_kind can be coerced
        from agents.types import ExpertKind
        for name, config in bootstrap.items():
            expert_kind = config.get('expert_kind')
            if expert_kind:
                result = ExpertKind.coerce(expert_kind)
                print(f"  ✓ {name} expert_kind '{expert_kind}' → {result}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("TESTING BROWSER TOOL DEMO FIXES")
    print("=" * 60)
    
    results = {
        "ExpertKind Coercion": test_expert_kind_coercion(),
        "Dependencies": test_dependencies(),
        "BrowserTool Init": await test_browser_tool_initialization(),
        "Registry Bootstrap": test_registry_bootstrap(),
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All tests passed! Browser tool demo should work now.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
