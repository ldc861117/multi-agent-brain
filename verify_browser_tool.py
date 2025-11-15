#!/usr/bin/env python3
"""Verification script for browser tool implementation."""

import sys
import os

# Set test environment
os.environ['BROWSER_SEARCH_PROVIDER'] = 'duckduckgo'
os.environ['BROWSER_ENGINE'] = 'none'

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    try:
        from utils.openai_client import BrowserToolConfig
        from utils.config_manager import get_browser_tool_config
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
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from utils.openai_client import BrowserToolConfig
        from utils.config_manager import get_browser_tool_config
        
        # Test direct config creation
        config = BrowserToolConfig(
            enabled=True,
            search_provider="duckduckgo",
            search_api_key=None
        )
        assert config.search_provider == "duckduckgo"
        print("✓ Direct config creation works")
        
        # Test config from environment
        config_from_env = BrowserToolConfig.from_env(load_env=False)
        assert config_from_env.search_provider == "duckduckgo"
        print("✓ Config from environment works")
        
        # Test config manager
        agent_config = get_browser_tool_config("test_agent")
        assert agent_config is not None
        print("✓ Config manager works")
        
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_models():
    """Test data model creation."""
    print("\nTesting data models...")
    try:
        from tools.browser_tool import SearchResult, PageContent, BrowserResult
        
        # Test SearchResult
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet"
        )
        assert result.title == "Test"
        print("✓ SearchResult creation works")
        
        # Test PageContent
        page = PageContent(
            url="https://example.com",
            title="Test Page",
            text="Test content"
        )
        assert page.title == "Test Page"
        print("✓ PageContent creation works")
        
        # Test BrowserResult
        browser_result = BrowserResult(
            query="test query",
            search_results=[result],
            visited_pages=[page]
        )
        assert browser_result.query == "test query"
        assert len(browser_result.search_results) == 1
        print("✓ BrowserResult creation works")
        
        return True
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Browser Tool Implementation Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Data Models", test_data_models()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:20s} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ All verification tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
