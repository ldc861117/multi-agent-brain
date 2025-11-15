"""Unit tests for browser tool adapter.

This module tests the browser tool implementation with mocked external dependencies
to verify configuration wiring, error translation, and LLM configuration forwarding.
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import asdict

# Import browser tool components
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
    TavilySearchEngine,
    DuckDuckGoSearchEngine,
    create_search_engine,
    PageNavigator,
    ContentParser,
)
from utils.openai_client import BrowserToolConfig


# ==================== FIXTURES ====================

@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment for testing."""
    browser_env_vars = [
        'BROWSER_TOOL_ENABLED',
        'BROWSER_SEARCH_PROVIDER',
        'BROWSER_SEARCH_API_KEY',
        'TAVILY_API_KEY',
        'BROWSER_SEARCH_BASE_URL',
        'BROWSER_FALLBACK_PROVIDER',
        'BROWSER_ENGINE',
        'BROWSER_HEADLESS',
        'BROWSER_USER_AGENT',
        'BROWSER_VIEWPORT_WIDTH',
        'BROWSER_VIEWPORT_HEIGHT',
        'BROWSER_SEARCH_TIMEOUT',
        'BROWSER_NAVIGATION_TIMEOUT',
        'BROWSER_EXTRACTION_TIMEOUT',
        'BROWSER_MAX_RETRIES',
        'BROWSER_RETRY_DELAY',
        'BROWSER_RATE_LIMIT_DELAY',
        'BROWSER_MAX_CONTENT_LENGTH',
        'BROWSER_EXTRACT_IMAGES',
        'BROWSER_EXTRACT_LINKS',
        'BROWSER_CACHE_ENABLED',
        'BROWSER_CACHE_TTL',
    ]
    
    for var in browser_env_vars:
        if var in os.environ:
            monkeypatch.delenv(var, raising=False)
    
    yield monkeypatch


@pytest.fixture
def default_config():
    """Default browser tool configuration."""
    return BrowserToolConfig(
        enabled=True,
        search_provider="tavily",
        search_api_key="test-key",
        fallback_provider="duckduckgo",
        browser_engine="playwright",
        headless=True,
        search_timeout=10,
        navigation_timeout=30,
        max_retries=3,
        retry_delay=2.0,
    )


@pytest.fixture
def mock_httpx_response():
    """Mock httpx response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    return mock_response


@pytest.fixture
def tavily_search_results():
    """Sample Tavily search results."""
    return {
        "answer": "Milvus is a vector database",
        "results": [
            {
                "title": "Milvus Documentation",
                "url": "https://milvus.io/docs",
                "content": "Official Milvus documentation",
                "score": 0.95
            },
            {
                "title": "Milvus GitHub",
                "url": "https://github.com/milvus-io/milvus",
                "content": "Milvus vector database repository",
                "score": 0.90
            }
        ]
    }


@pytest.fixture
def duckduckgo_html():
    """Sample DuckDuckGo HTML response."""
    return """
    <html>
        <body>
            <div class="result">
                <a class="result__a" href="https://example.com/page1">Example Page 1</a>
                <div class="result__snippet">This is the first result snippet</div>
            </div>
            <div class="result">
                <a class="result__a" href="https://example.com/page2">Example Page 2</a>
                <div class="result__snippet">This is the second result snippet</div>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_content():
    """Sample HTML content for extraction."""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Test Heading</h1>
            <p>This is a test paragraph.</p>
            <a href="/relative-link">Relative Link</a>
            <a href="https://example.com/absolute">Absolute Link</a>
            <img src="/image.jpg" alt="Test Image">
            <script>console.log("script");</script>
            <style>.test { color: red; }</style>
        </body>
    </html>
    """


# ==================== CONFIGURATION TESTS ====================

class TestBrowserToolConfig:
    """Test BrowserToolConfig loading and validation."""
    
    def test_config_from_env_defaults(self, clean_env):
        """Test default configuration values."""
        config = BrowserToolConfig.from_env(load_env=False)
        
        assert config.enabled is True
        assert config.search_provider == "tavily"
        assert config.search_api_key is None
        assert config.fallback_provider == "duckduckgo"
        assert config.browser_engine == "playwright"
        assert config.headless is True
        assert config.search_timeout == 10
        assert config.navigation_timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
    
    def test_config_from_env_with_overrides(self, clean_env):
        """Test configuration loading from environment variables."""
        clean_env.setenv('BROWSER_TOOL_ENABLED', 'false')
        clean_env.setenv('BROWSER_SEARCH_PROVIDER', 'duckduckgo')
        clean_env.setenv('BROWSER_SEARCH_API_KEY', 'test-api-key')
        clean_env.setenv('BROWSER_FALLBACK_PROVIDER', 'tavily')
        clean_env.setenv('BROWSER_ENGINE', 'none')
        clean_env.setenv('BROWSER_HEADLESS', 'false')
        clean_env.setenv('BROWSER_SEARCH_TIMEOUT', '20')
        clean_env.setenv('BROWSER_MAX_RETRIES', '5')
        
        config = BrowserToolConfig.from_env(load_env=False)
        
        assert config.enabled is False
        assert config.search_provider == "duckduckgo"
        assert config.search_api_key == "test-api-key"
        assert config.fallback_provider == "tavily"
        assert config.browser_engine == "none"
        assert config.headless is False
        assert config.search_timeout == 20
        assert config.max_retries == 5
    
    def test_config_bool_parsing(self, clean_env):
        """Test boolean environment variable parsing."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('off', False),
        ]
        
        for value, expected in test_cases:
            clean_env.setenv('BROWSER_TOOL_ENABLED', value)
            config = BrowserToolConfig.from_env(load_env=False)
            assert config.enabled == expected, f"Failed for value '{value}'"


# ==================== SEARCH ENGINE TESTS ====================

class TestTavilySearchEngine:
    """Test Tavily search engine implementation."""
    
    @pytest.mark.asyncio
    async def test_tavily_search_success(self, default_config, tavily_search_results):
        """Test successful Tavily search."""
        engine = TavilySearchEngine(default_config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = tavily_search_results
            mock_response.raise_for_status = Mock()
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            results = await engine.query("test query", max_results=5)
            
            assert len(results) == 2
            assert results[0].title == "Milvus Documentation"
            assert results[0].url == "https://milvus.io/docs"
            assert results[0].score == 0.95
            assert results[0].metadata["provider"] == "tavily"
    
    @pytest.mark.asyncio
    async def test_tavily_search_rate_limit(self, default_config):
        """Test Tavily rate limit error handling."""
        engine = TavilySearchEngine(default_config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = __import__('httpx').HTTPStatusError(
                "Rate limit", request=Mock(), response=mock_response
            )
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            with pytest.raises(RateLimitError):
                await engine.query("test query", max_results=5)
    
    @pytest.mark.asyncio
    async def test_tavily_search_auth_error(self, default_config):
        """Test Tavily authentication error handling."""
        engine = TavilySearchEngine(default_config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = __import__('httpx').HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response
            )
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            with pytest.raises(SearchProviderError, match="authentication failed"):
                await engine.query("test query", max_results=5)
    
    def test_tavily_requires_api_key(self):
        """Test that Tavily engine requires API key."""
        config = BrowserToolConfig(search_api_key=None)
        
        with pytest.raises(SearchProviderError, match="API key is required"):
            TavilySearchEngine(config)


class TestDuckDuckGoSearchEngine:
    """Test DuckDuckGo search engine implementation."""
    
    @pytest.mark.asyncio
    async def test_duckduckgo_search_success(self, default_config, duckduckgo_html):
        """Test successful DuckDuckGo search."""
        engine = DuckDuckGoSearchEngine(default_config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.text = duckduckgo_html
            mock_response.raise_for_status = Mock()
            
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context
            
            results = await engine.query("test query", max_results=5)
            
            assert len(results) == 2
            assert results[0].title == "Example Page 1"
            assert results[0].url == "https://example.com/page1"
            assert results[0].metadata["provider"] == "duckduckgo"
    
    @pytest.mark.asyncio
    async def test_duckduckgo_search_timeout(self, default_config):
        """Test DuckDuckGo timeout handling."""
        engine = DuckDuckGoSearchEngine(default_config)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=__import__('httpx').TimeoutException("Timeout")
            )
            mock_client.return_value = mock_context
            
            with pytest.raises(SearchProviderError, match="timeout"):
                await engine.query("test query", max_results=5)


class TestSearchEngineFactory:
    """Test search engine factory function."""
    
    def test_create_tavily_engine(self, default_config):
        """Test creating Tavily engine."""
        engine = create_search_engine("tavily", default_config)
        assert isinstance(engine, TavilySearchEngine)
    
    def test_create_duckduckgo_engine(self, default_config):
        """Test creating DuckDuckGo engine."""
        engine = create_search_engine("duckduckgo", default_config)
        assert isinstance(engine, DuckDuckGoSearchEngine)
    
    def test_create_unknown_engine_fallback(self, default_config):
        """Test fallback for unknown engine."""
        engine = create_search_engine("unknown", default_config)
        assert isinstance(engine, DuckDuckGoSearchEngine)


# ==================== CONTENT PARSER TESTS ====================

class TestContentParser:
    """Test HTML content parser."""
    
    def test_extract_from_html_basic(self, default_config, sample_html_content):
        """Test basic HTML extraction."""
        parser = ContentParser(default_config)
        extracted = parser.extract_from_html(sample_html_content, "https://example.com")
        
        assert extracted["title"] == "Test Page"
        assert "Test Heading" in extracted["text"]
        assert "test paragraph" in extracted["text"]
        # Script and style should be removed
        assert "console.log" not in extracted["text"]
        assert "color: red" not in extracted["text"]
    
    def test_extract_links(self, default_config, sample_html_content):
        """Test link extraction."""
        parser = ContentParser(default_config)
        extracted = parser.extract_from_html(sample_html_content, "https://example.com")
        
        assert len(extracted["links"]) == 2
        # Relative link should be resolved
        assert "https://example.com/relative-link" in extracted["links"]
        assert "https://example.com/absolute" in extracted["links"]
    
    def test_extract_images(self, default_config, sample_html_content):
        """Test image extraction when enabled."""
        config = BrowserToolConfig(extract_images=True)
        parser = ContentParser(config)
        extracted = parser.extract_from_html(sample_html_content, "https://example.com")
        
        assert len(extracted["images"]) == 1
        assert "https://example.com/image.jpg" in extracted["images"]
    
    def test_content_length_truncation(self, default_config):
        """Test content length truncation."""
        long_html = f"<html><body><p>{'x' * 200000}</p></body></html>"
        parser = ContentParser(default_config)
        extracted = parser.extract_from_html(long_html)
        
        assert len(extracted["text"]) <= default_config.max_content_length + 3  # +3 for "..."


# ==================== BROWSER TOOL INTEGRATION TESTS ====================

class TestBrowserTool:
    """Test main BrowserTool class."""
    
    @pytest.mark.asyncio
    async def test_browser_tool_initialization(self, clean_env):
        """Test BrowserTool initialization."""
        clean_env.setenv('BROWSER_SEARCH_API_KEY', 'test-key')
        
        with patch('tools.browser_tool.get_browser_tool_config') as mock_config:
            mock_config.return_value = BrowserToolConfig(
                search_provider="tavily",
                search_api_key="test-key"
            )
            
            tool = BrowserTool(agent_name="test_agent")
            
            assert tool.agent_name == "test_agent"
            assert tool.config.search_provider == "tavily"
            mock_config.assert_called_once_with("test_agent")
    
    @pytest.mark.asyncio
    async def test_search_success(self, default_config, tavily_search_results):
        """Test successful search operation."""
        with patch('tools.browser_tool.get_browser_tool_config', return_value=default_config):
            tool = BrowserTool(agent_name="test")
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.json.return_value = tavily_search_results
                mock_response.raise_for_status = Mock()
                
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_context
                
                result = await tool.search("test query", max_results=5)
                
                assert result.query == "test query"
                assert len(result.search_results) == 2
                assert result.error is None
                assert result.metadata["provider"] == "tavily"
                assert "latency_seconds" in result.metadata
    
    @pytest.mark.asyncio
    async def test_search_with_fallback(self, default_config, duckduckgo_html):
        """Test search fallback when primary fails."""
        with patch('tools.browser_tool.get_browser_tool_config', return_value=default_config):
            tool = BrowserTool(agent_name="test")
            
            call_count = 0
            
            async def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count <= default_config.max_retries:
                    # First calls fail (Tavily)
                    mock_response = AsyncMock()
                    mock_response.status_code = 429
                    mock_response.raise_for_status.side_effect = __import__('httpx').HTTPStatusError(
                        "Rate limit", request=Mock(), response=mock_response
                    )
                    return mock_response
                else:
                    # Fallback succeeds (DuckDuckGo)
                    mock_response = AsyncMock()
                    mock_response.text = duckduckgo_html
                    mock_response.raise_for_status = Mock()
                    return mock_response
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = mock_post
                mock_client.return_value = mock_context
                
                result = await tool.search("test query", max_results=5)
                
                assert result.error is None
                assert result.metadata["fallback"] is True
                assert result.metadata["provider"] == "duckduckgo"
                assert len(result.search_results) == 2
    
    @pytest.mark.asyncio
    async def test_search_all_providers_fail(self, default_config):
        """Test when all search providers fail."""
        with patch('tools.browser_tool.get_browser_tool_config', return_value=default_config):
            tool = BrowserTool(agent_name="test")
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 500
                mock_response.raise_for_status.side_effect = __import__('httpx').HTTPStatusError(
                    "Server error", request=Mock(), response=mock_response
                )
                
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                mock_client.return_value = mock_context
                
                result = await tool.search("test query", max_results=5)
                
                assert result.error is not None
                assert "All search providers failed" in result.error
                assert len(result.search_results) == 0
    
    @pytest.mark.asyncio
    async def test_browser_tool_context_manager(self, default_config):
        """Test BrowserTool as async context manager."""
        with patch('tools.browser_tool.get_browser_tool_config', return_value=default_config):
            async with BrowserTool(agent_name="test") as tool:
                assert tool is not None
                assert tool.agent_name == "test"
            
            # Tool should be closed after context


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling and normalization."""
    
    @pytest.mark.asyncio
    async def test_navigation_error_when_engine_disabled(self, default_config):
        """Test that navigation fails when browser engine is disabled."""
        config = BrowserToolConfig(
            browser_engine="none",
            search_provider="duckduckgo",  # Use DuckDuckGo to avoid API key requirement
            search_api_key=None
        )
        
        with patch('tools.browser_tool.get_browser_tool_config', return_value=config):
            tool = BrowserTool(agent_name="test")
            
            with pytest.raises(NavigationError, match="Browser engine is disabled"):
                await tool.navigate_and_extract("https://example.com")
    
    def test_search_provider_error_types(self):
        """Test different SearchProviderError scenarios."""
        # API key error
        with pytest.raises(SearchProviderError, match="API key"):
            config = BrowserToolConfig(search_api_key=None)
            TavilySearchEngine(config)
    
    @pytest.mark.asyncio
    async def test_retry_logic_exhaustion(self, default_config):
        """Test that retry logic exhausts after max attempts."""
        with patch('tools.browser_tool.get_browser_tool_config', return_value=default_config):
            tool = BrowserTool(agent_name="test")
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_context = AsyncMock()
                mock_context.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Connection error")
                )
                mock_client.return_value = mock_context
                
                # Should retry max_retries times and then fail
                with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                    result = await tool.search("test query")
                
                # Should have tried primary and fallback
                assert result.error is not None


# ==================== DATA MODEL TESTS ====================

class TestDataModels:
    """Test data model classes."""
    
    def test_search_result_creation(self):
        """Test SearchResult dataclass."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            score=0.95,
            metadata={"provider": "tavily"}
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.score == 0.95
        assert result.metadata["provider"] == "tavily"
    
    def test_page_content_creation(self):
        """Test PageContent dataclass."""
        content = PageContent(
            url="https://example.com",
            title="Test Page",
            text="Test content",
            links=["https://example.com/link"],
            images=["https://example.com/image.jpg"]
        )
        
        assert content.url == "https://example.com"
        assert content.title == "Test Page"
        assert len(content.links) == 1
        assert len(content.images) == 1
        assert content.timestamp  # Should have auto-generated timestamp
    
    def test_browser_result_creation(self):
        """Test BrowserResult dataclass."""
        result = BrowserResult(
            query="test query",
            search_results=[
                SearchResult("Title", "https://example.com", "Snippet")
            ],
            visited_pages=[],
            metadata={"provider": "tavily"}
        )
        
        assert result.query == "test query"
        assert len(result.search_results) == 1
        assert result.error is None
        assert result.metadata["provider"] == "tavily"


# ==================== CONFIGURATION INTEGRATION TESTS ====================

class TestConfigurationIntegration:
    """Test integration with ConfigManager."""
    
    @pytest.mark.asyncio
    async def test_agent_specific_config(self, clean_env):
        """Test that agent-specific configuration is used."""
        clean_env.setenv('BROWSER_SEARCH_API_KEY', 'test-key')
        
        with patch('tools.browser_tool.get_browser_tool_config') as mock_get_config:
            # Mock different configs for different agents
            def get_config_side_effect(agent_name):
                if agent_name == "agent1":
                    return BrowserToolConfig(
                        search_provider="tavily",
                        search_api_key="key1",
                        search_timeout=10
                    )
                else:
                    return BrowserToolConfig(
                        search_provider="duckduckgo",
                        search_api_key="key2",
                        search_timeout=20
                    )
            
            mock_get_config.side_effect = get_config_side_effect
            
            tool1 = BrowserTool(agent_name="agent1")
            tool2 = BrowserTool(agent_name="agent2")
            
            assert tool1.config.search_provider == "tavily"
            assert tool1.config.search_timeout == 10
            assert tool2.config.search_provider == "duckduckgo"
            assert tool2.config.search_timeout == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
