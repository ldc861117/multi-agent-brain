"""Browser tool for web search and navigation.

This module provides a wrapper around web search providers and browser automation,
enabling agents to search the web, navigate pages, and extract content.

Features:
- Multiple search provider support (Tavily, DuckDuckGo, Bing, Google, SearXNG)
- Browser automation via Playwright (optional)
- Graceful fallback between providers
- Comprehensive error handling and retry logic
- Configuration via ConfigManager
"""

from __future__ import annotations

import asyncio
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from loguru import logger

# Import configuration
from utils.config_manager import get_browser_tool_config
from utils.openai_client import BrowserToolConfig


# ==================== DATA MODELS ====================

@dataclass
class SearchResult:
    """Single search result item."""
    title: str
    url: str
    snippet: str
    score: Optional[float] = None  # Relevance score (if available)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageContent:
    """Extracted page content."""
    url: str
    title: str
    text: str
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserResult:
    """Unified result object from browser tool."""
    query: str
    search_results: List[SearchResult] = field(default_factory=list)
    visited_pages: List[PageContent] = field(default_factory=list)
    answer: Optional[str] = None  # AI-generated summary (if using Tavily)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== EXCEPTIONS ====================

class BrowserToolError(Exception):
    """Base exception for browser tool errors."""
    pass


class SearchProviderError(BrowserToolError):
    """Search provider specific errors (API key, quota, etc)."""
    pass


class NavigationError(BrowserToolError):
    """Browser navigation errors (timeout, 404, network failure)."""
    pass


class ExtractionError(BrowserToolError):
    """Content extraction errors."""
    pass


class RateLimitError(BrowserToolError):
    """Rate limiting errors from providers."""
    pass


# ==================== SEARCH ENGINE INTERFACE ====================

class SearchEngine(ABC):
    """Abstract base class for search providers."""
    
    def __init__(self, config: BrowserToolConfig):
        self.config = config
    
    @abstractmethod
    async def query(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute search query and return results.
        
        Parameters
        ----------
        query:
            Search query string
        max_results:
            Maximum number of results to return
            
        Returns
        -------
        List[SearchResult]
            List of search results
        """
        pass


# ==================== TAVILY SEARCH ENGINE ====================

class TavilySearchEngine(SearchEngine):
    """Tavily API search engine implementation."""
    
    def __init__(self, config: BrowserToolConfig):
        super().__init__(config)
        if not self.config.search_api_key:
            raise SearchProviderError("Tavily API key is required (set BROWSER_SEARCH_API_KEY or TAVILY_API_KEY)")
    
    async def query(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute Tavily search query."""
        try:
            # Import httpx only when needed
            import httpx
        except ImportError:
            raise SearchProviderError("httpx is required for Tavily search (pip install httpx)")
        
        url = "https://api.tavily.com/search"
        headers = {"X-API-Key": self.config.search_api_key}
        payload = {
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "max_results": max_results
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.search_timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        score=item.get("score"),
                        metadata={"provider": "tavily"}
                    ))
                
                logger.info(f"Tavily search returned {len(results)} results for query: {query}")
                return results
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Tavily API rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                raise SearchProviderError(f"Tavily API authentication failed: {e}")
            else:
                raise SearchProviderError(f"Tavily API error: {e}")
        except httpx.TimeoutException as e:
            raise SearchProviderError(f"Tavily API timeout: {e}")
        except Exception as e:
            raise SearchProviderError(f"Tavily search failed: {e}")


# ==================== DUCKDUCKGO SEARCH ENGINE ====================

class DuckDuckGoSearchEngine(SearchEngine):
    """DuckDuckGo HTML scraping search engine implementation."""
    
    async def query(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute DuckDuckGo search via HTML scraping."""
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError:
            raise SearchProviderError("httpx and beautifulsoup4 are required for DuckDuckGo search")
        
        # DuckDuckGo HTML search URL
        search_url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": self.config.user_agent
        }
        params = {
            "q": query
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.search_timeout, follow_redirects=True) as client:
                response = await client.post(search_url, data=params, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                
                # Parse search results
                for result_div in soup.select(".result"):
                    if len(results) >= max_results:
                        break
                    
                    title_elem = result_div.select_one(".result__a")
                    snippet_elem = result_div.select_one(".result__snippet")
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get("href", "")
                        snippet = snippet_elem.get_text(strip=True)
                        
                        # DuckDuckGo uses redirect URLs, extract actual URL
                        if url.startswith("//duckduckgo.com/l/?"):
                            # Extract uddg parameter which contains the actual URL
                            match = re.search(r'uddg=([^&]+)', url)
                            if match:
                                from urllib.parse import unquote
                                url = unquote(match.group(1))
                        
                        if url and title:
                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                metadata={"provider": "duckduckgo"}
                            ))
                
                logger.info(f"DuckDuckGo search returned {len(results)} results for query: {query}")
                return results
                
        except httpx.HTTPStatusError as e:
            raise SearchProviderError(f"DuckDuckGo HTTP error: {e}")
        except httpx.TimeoutException as e:
            raise SearchProviderError(f"DuckDuckGo timeout: {e}")
        except Exception as e:
            raise SearchProviderError(f"DuckDuckGo search failed: {e}")


# ==================== SEARCH ENGINE FACTORY ====================

def create_search_engine(provider: str, config: BrowserToolConfig) -> SearchEngine:
    """Factory function to create search engine instances.
    
    Parameters
    ----------
    provider:
        Search provider name ("tavily", "duckduckgo", etc.)
    config:
        Browser tool configuration
        
    Returns
    -------
    SearchEngine
        Instantiated search engine
    """
    provider_lower = provider.lower().strip()
    
    if provider_lower == "tavily":
        return TavilySearchEngine(config)
    elif provider_lower == "duckduckgo":
        return DuckDuckGoSearchEngine(config)
    else:
        # For now, unsupported providers fall back to DuckDuckGo
        logger.warning(f"Unsupported search provider '{provider}', falling back to DuckDuckGo")
        return DuckDuckGoSearchEngine(config)


# ==================== PAGE NAVIGATOR (Playwright) ====================

class PageNavigator:
    """Browser automation wrapper using Playwright."""
    
    def __init__(self, config: BrowserToolConfig):
        self.config = config
        self.browser = None
        self.context = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of Playwright browser."""
        if self._initialized:
            return
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise NavigationError("playwright is required for browser navigation (pip install playwright)")
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.config.headless)
            self.context = await self.browser.new_context(
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
                user_agent=self.config.user_agent
            )
            self._initialized = True
            logger.debug("Playwright browser initialized")
        except Exception as e:
            raise NavigationError(f"Failed to initialize Playwright: {e}")
    
    async def goto(self, url: str, timeout: Optional[int] = None) -> Any:
        """Navigate to URL and return page object.
        
        Parameters
        ----------
        url:
            URL to navigate to
        timeout:
            Navigation timeout in seconds (uses config default if not specified)
            
        Returns
        -------
        playwright.async_api.Page
            Playwright page object
        """
        await self._ensure_initialized()
        
        timeout_ms = (timeout or self.config.navigation_timeout) * 1000
        
        try:
            page = await self.context.new_page()
            await page.goto(url, timeout=timeout_ms)
            logger.debug(f"Navigated to {url}")
            return page
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}")
    
    async def close(self):
        """Close browser and clean up resources."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()
        self._initialized = False
        logger.debug("Playwright browser closed")


# ==================== CONTENT PARSER ====================

class ContentParser:
    """HTML content extraction utilities."""
    
    def __init__(self, config: BrowserToolConfig):
        self.config = config
    
    def extract_from_html(self, html: str, base_url: str = "") -> Dict[str, Any]:
        """Extract content from HTML string.
        
        Parameters
        ----------
        html:
            HTML content string
        base_url:
            Base URL for resolving relative links
            
        Returns
        -------
        dict
            Extracted content (title, text, links, images)
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ExtractionError("beautifulsoup4 is required for content extraction")
        
        try:
            soup = BeautifulSoup(html, "lxml")
        except:
            # Fallback to html.parser if lxml is not available
            soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        
        # Truncate if too long
        if len(text) > self.config.max_content_length:
            text = text[:self.config.max_content_length] + "..."
        
        # Extract links if enabled
        links = []
        if self.config.extract_links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if base_url:
                    href = urljoin(base_url, href)
                links.append(href)
        
        # Extract images if enabled
        images = []
        if self.config.extract_images:
            for img in soup.find_all("img", src=True):
                src = img["src"]
                if base_url:
                    src = urljoin(base_url, src)
                images.append(src)
        
        return {
            "title": title,
            "text": text,
            "links": links[:100],  # Limit to first 100 links
            "images": images[:50]  # Limit to first 50 images
        }
    
    async def extract_from_page(self, page: Any, url: str) -> PageContent:
        """Extract content from Playwright page object.
        
        Parameters
        ----------
        page:
            Playwright page object
        url:
            Page URL
            
        Returns
        -------
        PageContent
            Extracted page content
        """
        try:
            html = await page.content()
            extracted = self.extract_from_html(html, url)
            
            return PageContent(
                url=url,
                title=extracted["title"],
                text=extracted["text"],
                links=extracted["links"],
                images=extracted["images"],
                metadata={"extracted_at": datetime.utcnow().isoformat()}
            )
        except Exception as e:
            raise ExtractionError(f"Failed to extract content from {url}: {e}")


# ==================== MAIN BROWSER TOOL ====================

class BrowserTool:
    """Main browser tool interface for web search and navigation."""
    
    def __init__(self, agent_name: str = "default"):
        """Initialize browser tool.
        
        Parameters
        ----------
        agent_name:
            Name of the agent using this tool (for config overrides)
        """
        self.agent_name = agent_name
        self.config = get_browser_tool_config(agent_name)
        self.search_engine = create_search_engine(self.config.search_provider, self.config)
        self.navigator: Optional[PageNavigator] = None
        self.parser = ContentParser(self.config)
        
        logger.info(
            f"BrowserTool initialized for agent '{agent_name}' "
            f"with provider '{self.config.search_provider}'"
        )
    
    def _get_navigator(self) -> PageNavigator:
        """Lazy initialization of page navigator."""
        if self.navigator is None:
            if self.config.browser_engine == "none":
                raise NavigationError("Browser engine is disabled (browser_engine='none')")
            self.navigator = PageNavigator(self.config)
        return self.navigator
    
    async def search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Execute web search and return results.
        
        Parameters
        ----------
        query:
            Search query string
        max_results:
            Maximum number of results to return
            
        Returns
        -------
        BrowserResult
            Search results with metadata
        """
        start_time = time.time()
        
        try:
            # Try primary search provider with retry
            results = await self._search_with_retry(query, max_results)
            
            elapsed = time.time() - start_time
            return BrowserResult(
                query=query,
                search_results=results,
                metadata={
                    "provider": self.config.search_provider,
                    "latency_seconds": round(elapsed, 2),
                    "result_count": len(results)
                }
            )
            
        except (SearchProviderError, RateLimitError) as e:
            logger.warning(f"Primary search failed, trying fallback: {e}")
            
            # Try fallback provider
            try:
                results = await self._fallback_search(query, max_results)
                elapsed = time.time() - start_time
                
                return BrowserResult(
                    query=query,
                    search_results=results,
                    metadata={
                        "provider": self.config.fallback_provider,
                        "fallback": True,
                        "latency_seconds": round(elapsed, 2),
                        "result_count": len(results),
                        "primary_error": str(e)
                    }
                )
            except Exception as fallback_error:
                logger.exception(f"Fallback search also failed: {fallback_error}")
                elapsed = time.time() - start_time
                
                return BrowserResult(
                    query=query,
                    error=f"All search providers failed: {str(e)}; Fallback: {str(fallback_error)}",
                    metadata={
                        "provider": self.config.search_provider,
                        "fallback_provider": self.config.fallback_provider,
                        "latency_seconds": round(elapsed, 2)
                    }
                )
    
    async def _search_with_retry(self, query: str, max_results: int) -> List[SearchResult]:
        """Execute search with exponential backoff retry."""
        for attempt in range(self.config.max_retries):
            try:
                return await self.search_engine.query(query, max_results)
            except RateLimitError as e:
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1}/{self.config.max_retries})")
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"Search attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise SearchProviderError("All retry attempts exhausted")
    
    async def _fallback_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Execute fallback search provider."""
        fallback_engine = create_search_engine(self.config.fallback_provider, self.config)
        return await fallback_engine.query(query, max_results)
    
    async def navigate_and_extract(self, url: str) -> PageContent:
        """Navigate to URL and extract content.
        
        Parameters
        ----------
        url:
            URL to navigate to
            
        Returns
        -------
        PageContent
            Extracted page content
        """
        navigator = self._get_navigator()
        
        try:
            page = await navigator.goto(url)
            content = await self.parser.extract_from_page(page, url)
            await page.close()
            
            logger.info(f"Successfully extracted content from {url}")
            return content
            
        except Exception as e:
            logger.exception(f"Failed to navigate and extract {url}: {e}")
            raise
    
    async def search_and_visit(
        self,
        query: str,
        max_results: int = 5,
        visit_top_n: int = 3
    ) -> BrowserResult:
        """Combined operation: search + visit top N results.
        
        Parameters
        ----------
        query:
            Search query string
        max_results:
            Maximum search results to retrieve
        visit_top_n:
            Number of top results to visit and extract
            
        Returns
        -------
        BrowserResult
            Search results with visited page content
        """
        # First, execute search
        result = await self.search(query, max_results)
        
        if result.error or not result.search_results:
            return result
        
        # Visit top N results
        visited = []
        for i, search_result in enumerate(result.search_results[:visit_top_n]):
            try:
                logger.info(f"Visiting result {i+1}/{visit_top_n}: {search_result.url}")
                content = await self.navigate_and_extract(search_result.url)
                visited.append(content)
                
                # Respectful rate limiting between requests
                if i < visit_top_n - 1:
                    await asyncio.sleep(self.config.rate_limit_delay)
                    
            except Exception as e:
                logger.warning(f"Failed to visit {search_result.url}: {e}")
                # Continue with other results
        
        result.visited_pages = visited
        result.metadata["visited_count"] = len(visited)
        
        return result
    
    async def close(self):
        """Clean up resources."""
        if self.navigator:
            await self.navigator.close()
            self.navigator = None
        logger.debug(f"BrowserTool closed for agent '{self.agent_name}'")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# ==================== CONVENIENCE FUNCTIONS ====================

async def quick_search(query: str, agent_name: str = "default", max_results: int = 5) -> BrowserResult:
    """Convenience function for quick web search.
    
    Parameters
    ----------
    query:
        Search query string
    agent_name:
        Agent name for configuration
    max_results:
        Maximum results to return
        
    Returns
    -------
    BrowserResult
        Search results
    """
    async with BrowserTool(agent_name=agent_name) as browser:
        return await browser.search(query, max_results)


async def quick_search_and_visit(
    query: str,
    agent_name: str = "default",
    max_results: int = 5,
    visit_top_n: int = 2
) -> BrowserResult:
    """Convenience function for search + visit workflow.
    
    Parameters
    ----------
    query:
        Search query string
    agent_name:
        Agent name for configuration
    max_results:
        Maximum search results
    visit_top_n:
        Number of top results to visit
        
    Returns
    -------
    BrowserResult
        Search results with visited page content
    """
    async with BrowserTool(agent_name=agent_name) as browser:
        return await browser.search_and_visit(query, max_results, visit_top_n)
