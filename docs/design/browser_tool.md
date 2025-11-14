# Browser Tool Design

> **Status**: Design Phase  
> **Author**: AI Coding Agent  
> **Last Updated**: 2024-11-14  
> **Related**: [ROADMAP.md](../ROADMAP.md) (H3 - Plugin/tooling gallery)

## Executive Summary

This document specifies the design for integrating browser and web search capabilities into the `multi-agent-brain` project. The browser tool will enable agents to perform web searches, navigate websites, extract content, and optionally persist findings to `SharedMemory`. The design prioritizes OSS-friendly defaults, configuration flexibility, and seamless integration with the existing agent architecture.

**Key Decisions**:
- **Default Search Provider**: Tavily API (recommended for LLM-optimized results)
- **Fallback Strategy**: DuckDuckGo HTML scraping (no API key required)
- **Browser Engine**: Playwright (async-native, multi-browser support)
- **Configuration Model**: Follows existing `api_config` patterns with agent overrides
- **Memory Handling**: Explicit opt-in by agents (no automatic persistence)

---

## Table of Contents

1. [OpenAgents Web Agent Audit](#1-openagents-web-agent-audit)
2. [Search Provider Evaluation](#2-search-provider-evaluation)
3. [Configuration Contract](#3-configuration-contract)
4. [Architecture & Control Flow](#4-architecture--control-flow)
5. [Implementation Plan](#5-implementation-plan)
6. [Testing Strategy](#6-testing-strategy)
7. [Dependency Matrix](#7-dependency-matrix)
8. [Acceptance Checklist](#8-acceptance-checklist)
9. [Open Questions & Risks](#9-open-questions--risks)

---

## 1. OpenAgents Web Agent Audit

### 1.1 Overview of OpenAgents `real_agents/web_agent`

The OpenAgents framework provides a reference implementation of a web agent with the following capabilities:

**Core Capabilities**:
1. **Web Search**: Integration with search APIs to retrieve relevant web results
2. **Page Navigation**: Navigate to URLs and follow links
3. **Content Extraction**: Parse HTML and extract text, structured data, images
4. **Form Interaction**: Submit forms with field values
5. **JavaScript Execution**: Handle dynamic content via browser automation
6. **Screenshot Capture**: Visual evidence of browsing sessions

**Runtime Expectations**:
- **Browser Engine**: Typically uses Playwright or Selenium for browser automation
- **Async Model**: Async/await pattern for I/O-bound operations (compatible with `multi-agent-brain`)
- **Session Management**: Maintains browser context across multiple operations
- **Authentication**: Supports cookies, headers, and basic auth mechanisms

**Typical Workflow**:
```python
# Simplified example based on OpenAgents patterns
async def handle_web_query(query: str):
    # 1. Search phase
    search_results = await search_api.query(query)
    
    # 2. Navigation phase
    for result in search_results[:3]:
        page = await browser.navigate(result.url)
        content = await page.extract_text()
        
    # 3. Synthesis
    return synthesize_answer(query, content)
```

**Key Dependencies**:
- `playwright` or `selenium` (browser automation)
- `beautifulsoup4` (HTML parsing)
- `requests` / `httpx` (HTTP client)
- Search API client (varies by provider)

**Authentication Patterns**:
- Search APIs: API key in headers (`X-API-Key`, `Authorization`)
- Browser sessions: Cookie jar, localStorage injection
- Rate limiting: Backoff + retry logic

**Configuration Surface**:
- Search provider selection + credentials
- Browser settings (headless, user agent, viewport)
- Timeout values (search, navigation, element wait)
- Retry counts and delays
- Content extraction rules (CSS selectors, XPath)

### 1.2 Integration Gaps with `multi-agent-brain`

| Aspect | OpenAgents Pattern | `multi-agent-brain` Pattern | Adaptation Needed |
|--------|-------------------|----------------------------|-------------------|
| Configuration | Environment variables | `config.yaml` + `.env` with agent overrides | Map web tool config to `api_config.browser_tool` section |
| Async | Async/await | Async/await (compatible) | ✅ Direct integration |
| Error Handling | Exception-based | Logged exceptions + graceful degradation | Wrap in try/except with logger.exception() |
| Memory | Direct database writes | Explicit agent-controlled persistence | Add `persist_to_memory=False` parameter |
| LLM Integration | Separate client | `OpenAIClientWrapper` | Reuse existing client for synthesis |

---

## 2. Search Provider Evaluation

### 2.1 Provider Comparison Matrix

| Provider | Cost (Free Tier) | Rate Limits | Auth | OSS-Friendly | Quality | Reliability |
|----------|-----------------|-------------|------|--------------|---------|-------------|
| **Tavily** | 1000 req/month | ~100/day | API key | ⭐⭐⭐ High | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Bing Search** | N/A (Azure) | Varies by tier | API key | ⭐⭐ Medium | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Google CSE** | 100 req/day | 100/day free | API key | ⭐⭐ Medium | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **SearXNG** | Unlimited (self-hosted) | None | None | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **DuckDuckGo** | Unlimited (scraping) | Soft limit | None | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 2.2 Detailed Provider Analysis

#### 2.2.1 Tavily (Recommended Default)

**Pros**:
- Optimized for LLM/AI agent use cases (returns structured, summarized results)
- Generous free tier (1000 requests/month)
- Simple REST API with JSON responses
- Includes source citations and relevance scores
- Fast response times (optimized for real-time agent workflows)

**Cons**:
- Relatively new service (less proven than Google/Bing)
- Free tier limits may be restrictive for heavy use
- Requires API key signup

**API Structure**:
```python
# Example Tavily API call
POST https://api.tavily.com/search
Headers: {"X-API-Key": "tvly-..."}
Body: {
    "query": "Milvus vector database quickstart",
    "search_depth": "basic",  # or "advanced"
    "include_answer": true,
    "max_results": 5
}
Response: {
    "answer": "...",  # AI-generated summary
    "results": [
        {"title": "...", "url": "...", "content": "...", "score": 0.95}
    ]
}
```

**Credential Requirements**:
- `TAVILY_API_KEY` (obtain from https://tavily.com)

**Fallback Behavior**: If API key is missing or quota exceeded, fall back to DuckDuckGo scraping.

#### 2.2.2 Bing Search API

**Pros**:
- Enterprise-grade reliability
- Comprehensive results with rich metadata
- Well-documented SDK and REST API

**Cons**:
- Requires Azure subscription (no free tier)
- More complex setup (Azure portal, resource groups)
- Higher barrier to entry for OSS contributors

**Use Case**: Recommended for production deployments with budget allocation.

#### 2.2.3 Google Custom Search JSON API

**Pros**:
- Best-in-class search quality
- Mature API with extensive documentation
- Supports custom search engines (restrict to specific domains)

**Cons**:
- Only 100 free queries per day
- Requires Google Cloud project setup
- Quota limits strict for free tier

**Use Case**: Suitable for low-volume, high-quality use cases.

#### 2.2.4 SearXNG (Self-Hosted)

**Pros**:
- Fully open-source and free
- Privacy-focused (no tracking)
- Aggregates results from multiple search engines
- No API key required

**Cons**:
- Requires self-hosting (Docker setup)
- Variable quality depending on upstream engine availability
- Potential for IP blocks if scraping aggressively

**Use Case**: Best for privacy-conscious deployments or offline environments.

#### 2.2.5 DuckDuckGo (HTML Scraping)

**Pros**:
- No API key required
- Simple HTML scraping via `requests` + `BeautifulSoup`
- No hard rate limits (use respectful delays)

**Cons**:
- Unofficial (subject to HTML structure changes)
- Lower quality than dedicated APIs
- Risk of being blocked if too aggressive

**Use Case**: Default fallback when no API key is configured.

### 2.3 Recommended Strategy

**Primary**: Tavily API (developer-friendly, AI-optimized)  
**Secondary**: DuckDuckGo HTML scraping (zero-config fallback)  
**Optional**: Bing or Google CSE (configured via environment override)

**Configuration Example**:
```yaml
# config.yaml
api_config:
  browser_tool:
    search_provider: "tavily"  # or "bing", "google", "searxng", "duckduckgo"
    search_api_key: null  # Override via BROWSER_SEARCH_API_KEY
    fallback_provider: "duckduckgo"
```

---

## 3. Configuration Contract

### 3.1 YAML Configuration Schema

**Location**: `config.yaml` under `api_config.browser_tool`

```yaml
api_config:
  # ... existing chat_api, embedding_api ...
  
  browser_tool:
    enabled: true  # Global enable/disable switch
    
    # Search configuration
    search_provider: "tavily"  # "tavily" | "bing" | "google" | "searxng" | "duckduckgo"
    search_api_key: null  # Overridden by BROWSER_SEARCH_API_KEY env var
    search_api_base_url: null  # For self-hosted SearXNG
    fallback_provider: "duckduckgo"  # Used when primary fails
    
    # Browser automation settings
    browser_engine: "playwright"  # "playwright" | "selenium" | "none" (HTTP-only)
    headless: true
    user_agent: "Mozilla/5.0 (multi-agent-brain/1.0)"
    viewport_width: 1280
    viewport_height: 720
    
    # Timeout and rate limiting
    search_timeout: 10  # seconds
    navigation_timeout: 30  # seconds
    extraction_timeout: 15  # seconds
    max_retries: 3
    retry_delay: 2.0
    rate_limit_delay: 1.0  # Delay between consecutive requests
    
    # Content extraction
    max_content_length: 100000  # characters
    extract_images: false
    extract_links: true
    
    # Cache settings (optional)
    cache_enabled: false
    cache_ttl: 3600  # seconds
    
  # Agent-specific overrides
  agent_overrides:
    python_expert:
      browser_tool:
        search_provider: "google"  # Override for specific agent
        search_timeout: 15
```

### 3.2 Environment Variable Overrides

Following the existing pattern from `ChatAPIConfig` and `EmbeddingAPIConfig`:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `BROWSER_TOOL_ENABLED` | Enable/disable browser tool globally | `true` |
| `BROWSER_SEARCH_PROVIDER` | Search provider (`tavily`, `bing`, `google`, `searxng`, `duckduckgo`) | `tavily` |
| `BROWSER_SEARCH_API_KEY` | API key for search provider | `null` |
| `BROWSER_SEARCH_BASE_URL` | Base URL for self-hosted SearXNG | `null` |
| `BROWSER_FALLBACK_PROVIDER` | Fallback when primary fails | `duckduckgo` |
| `BROWSER_ENGINE` | Browser engine (`playwright`, `selenium`, `none`) | `playwright` |
| `BROWSER_HEADLESS` | Run browser in headless mode | `true` |
| `BROWSER_SEARCH_TIMEOUT` | Search operation timeout (seconds) | `10` |
| `BROWSER_NAVIGATION_TIMEOUT` | Page navigation timeout (seconds) | `30` |
| `BROWSER_MAX_RETRIES` | Max retry attempts | `3` |

**Priority Order** (high to low):
1. Agent-specific override in `config.yaml` (`agent_overrides.<agent>.browser_tool`)
2. Environment variables (`BROWSER_*`)
3. Global `config.yaml` (`api_config.browser_tool`)
4. Hard-coded defaults in `BrowserToolConfig`

### 3.3 Integration with Existing Config System

The browser tool configuration will integrate with `utils/config_manager.py` using the same patterns as chat/embedding APIs:

```python
# utils/config_manager.py additions
@dataclass
class BrowserToolConfig:
    enabled: bool = True
    search_provider: str = "tavily"
    search_api_key: Optional[str] = None
    search_api_base_url: Optional[str] = None
    fallback_provider: str = "duckduckgo"
    browser_engine: str = "playwright"
    headless: bool = True
    search_timeout: int = 10
    navigation_timeout: int = 30
    max_retries: int = 3
    # ... additional fields
    
    @classmethod
    def from_env(cls, load_env: bool = True) -> "BrowserToolConfig":
        """Load browser tool config from environment variables."""
        # Implementation similar to ChatAPIConfig.from_env()

class AgentConfig:
    """Extended to include browser_tool."""
    chat_api: ChatAPIConfig
    embedding_api: EmbeddingAPIConfig
    browser_tool: BrowserToolConfig  # New field
```

**Key Methods**:
- `ConfigManager.get_browser_tool_config(agent_name: str) -> BrowserToolConfig`
- `get_browser_tool_config(agent_name: str)` (utility function in `utils/__init__.py`)

### 3.4 Credential Handling

**Reuse Principle**: Browser tool will NOT duplicate LLM credential handling. For synthesis tasks, it will use the agent's existing `OpenAIClientWrapper`.

**Search API Credentials**: Managed separately via `BROWSER_SEARCH_API_KEY` (search is independent of LLM provider).

**Security Considerations**:
- API keys should never be logged or included in error messages
- Use `redact()` helper from `tools/operator.py` for display
- Validate keys on startup (optional health check)

---

## 4. Architecture & Control Flow

### 4.1 Component Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Layer                          │
│  (CoordinationAgent, PythonExpert, MilvusExpert, etc.)  │
└───────────────────────┬─────────────────────────────────┘
                        │ Invokes
                        ▼
┌─────────────────────────────────────────────────────────┐
│                 BrowserTool (tools/browser_tool.py)     │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │ SearchEngine   │  │ PageNavigator│  │ ContentParser││
│  │ (Tavily, DDG)  │  │ (Playwright) │  │(BeautifulSoup)││
│  └────────────────┘  └──────────────┘  └──────────────┘│
└───────────────────────┬─────────────────────────────────┘
                        │ Returns BrowserResult
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    Agent Decision Layer                 │
│  - Synthesize results using OpenAIClientWrapper         │
│  - Optionally persist to SharedMemory                   │
│  - Return AgentResponse to user                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Core Classes

#### 4.2.1 BrowserTool

**Location**: `tools/browser_tool.py`

```python
from dataclasses import dataclass
from typing import List, Optional
from utils import get_browser_tool_config

@dataclass
class SearchResult:
    """Single search result item."""
    title: str
    url: str
    snippet: str
    score: Optional[float] = None  # Relevance score (if available)
    
@dataclass
class PageContent:
    """Extracted page content."""
    url: str
    title: str
    text: str
    links: List[str]
    timestamp: str  # ISO format
    
@dataclass
class BrowserResult:
    """Unified result object from browser tool."""
    query: str
    search_results: List[SearchResult]
    visited_pages: List[PageContent]
    answer: Optional[str] = None  # AI-generated summary (if using Tavily)
    error: Optional[str] = None
    metadata: dict = None  # Provider, latency, etc.

class BrowserTool:
    """Main browser tool interface."""
    
    def __init__(self, agent_name: str = "default"):
        self.config = get_browser_tool_config(agent_name)
        self.search_engine = self._init_search_engine()
        self.navigator = self._init_navigator() if self.config.browser_engine != "none" else None
        
    async def search(self, query: str, max_results: int = 5) -> BrowserResult:
        """Execute web search and return results."""
        try:
            # Try primary search provider
            results = await self.search_engine.query(query, max_results)
            return BrowserResult(query=query, search_results=results, visited_pages=[])
        except Exception as e:
            logger.exception(f"Primary search failed, trying fallback: {e}")
            # Try fallback provider
            return await self._fallback_search(query, max_results)
    
    async def navigate_and_extract(self, url: str) -> PageContent:
        """Navigate to URL and extract content."""
        if not self.navigator:
            raise RuntimeError("Browser engine disabled (set browser_engine != 'none')")
        page = await self.navigator.goto(url, timeout=self.config.navigation_timeout)
        return await self._extract_content(page)
    
    async def search_and_visit(
        self, 
        query: str, 
        max_results: int = 5, 
        visit_top_n: int = 3
    ) -> BrowserResult:
        """Combined: search + visit top N results."""
        result = await self.search(query, max_results)
        visited = []
        for search_result in result.search_results[:visit_top_n]:
            try:
                content = await self.navigate_and_extract(search_result.url)
                visited.append(content)
            except Exception as e:
                logger.warning(f"Failed to visit {search_result.url}: {e}")
        result.visited_pages = visited
        return result
```

#### 4.2.2 SearchEngine (Strategy Pattern)

```python
class SearchEngine(ABC):
    """Abstract base class for search providers."""
    
    @abstractmethod
    async def query(self, query: str, max_results: int) -> List[SearchResult]:
        pass

class TavilySearchEngine(SearchEngine):
    """Tavily API implementation."""
    async def query(self, query: str, max_results: int) -> List[SearchResult]:
        # Call Tavily API
        pass

class DuckDuckGoSearchEngine(SearchEngine):
    """DuckDuckGo HTML scraping implementation."""
    async def query(self, query: str, max_results: int) -> List[SearchResult]:
        # Scrape DDG HTML
        pass

# Factory
def create_search_engine(provider: str, config: BrowserToolConfig) -> SearchEngine:
    if provider == "tavily":
        return TavilySearchEngine(config)
    elif provider == "duckduckgo":
        return DuckDuckGoSearchEngine(config)
    # ... other providers
```

### 4.3 Agent Invocation Flow

**Step-by-step control flow** when an agent uses the browser tool:

```python
# Example: Inside CoordinationAgent.handle_message()
from tools.browser_tool import BrowserTool, BrowserResult

async def handle_message(self, message: dict, conversation_state=None) -> AgentResponse:
    user_query = message.get("content", "")
    
    # 1. Determine if browser tool is needed
    if self._requires_web_search(user_query):
        # 2. Initialize browser tool
        browser = BrowserTool(agent_name=self.name)
        
        # 3. Execute search
        try:
            browser_result = await browser.search_and_visit(
                query=user_query,
                max_results=5,
                visit_top_n=2
            )
        except Exception as e:
            logger.exception(f"Browser tool failed: {e}")
            # Graceful degradation: proceed without web results
            browser_result = None
        
        # 4. Synthesize answer using LLM
        if browser_result and browser_result.search_results:
            context = self._format_browser_context(browser_result)
            answer = await self._synthesize_with_context(user_query, context)
        else:
            answer = await self._synthesize_without_web(user_query)
        
        # 5. OPTIONAL: Persist to SharedMemory (explicit decision)
        if browser_result and self._should_persist_web_results(user_query):
            await self._persist_browser_result(browser_result)
        
        # 6. Return response
        return AgentResponse(
            content=answer,
            metadata={
                "used_browser_tool": True,
                "search_provider": browser.config.search_provider,
                "sources": [r.url for r in browser_result.search_results] if browser_result else []
            }
        )
    else:
        # Normal flow without browser tool
        return await self._handle_without_web(user_query)
```

### 4.4 Error Propagation & Retry Strategy

**Error Handling Principles**:
1. **Fail gracefully**: Browser tool failures should not crash the agent
2. **Log verbosely**: Use `logger.exception()` for debugging
3. **Return partial results**: If search succeeds but navigation fails, return search results
4. **Use fallback providers**: Automatic fallback when primary search fails

**Retry Logic**:
```python
async def _search_with_retry(self, query: str, max_results: int) -> List[SearchResult]:
    """Execute search with exponential backoff retry."""
    for attempt in range(self.config.max_retries):
        try:
            return await self._execute_search(query, max_results)
        except RateLimitError as e:
            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limited, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
            else:
                raise
        except Exception as e:
            logger.exception(f"Search attempt {attempt + 1} failed: {e}")
            if attempt == self.config.max_retries - 1:
                raise
    raise RuntimeError("All retry attempts exhausted")
```

**Error Types**:
- `SearchProviderError`: API key invalid, quota exceeded
- `NavigationError`: Timeout, 404, network failure
- `ExtractionError`: Invalid HTML, missing elements
- `RateLimitError`: Too many requests (triggers backoff)

### 4.5 Memory Handling Strategy

**Key Principle**: Agents explicitly decide whether to persist browser results to `SharedMemory`. No automatic writes.

**Decision Criteria** (agent-specific):
```python
def _should_persist_web_results(self, query: str, result: BrowserResult) -> bool:
    """Decide whether to persist browser results to memory."""
    # Example heuristics:
    # 1. User explicitly asked to "remember" or "save"
    # 2. Results are high-quality (score > threshold)
    # 3. Query is about factual information (not one-off)
    # 4. Results are fresh (not from cache)
    
    if "remember" in query.lower() or "save" in query.lower():
        return True
    
    if result.search_results and all(r.score > 0.8 for r in result.search_results):
        return True
    
    return False  # Default: do not persist
```

**Persistence Implementation**:
```python
async def _persist_browser_result(self, result: BrowserResult) -> None:
    """Store browser result in SharedMemory."""
    from agents.shared_memory import SharedMemory
    
    memory = SharedMemory(agent_name=self.name)
    
    for page in result.visited_pages:
        await memory.store_knowledge(
            collection="web_snapshots",
            tenant_id=self._get_tenant_id(),
            content={
                "url": page.url,
                "title": page.title,
                "text": page.text[:10000],  # Truncate to avoid huge vectors
                "timestamp": page.timestamp
            },
            metadata={
                "source": "browser_tool",
                "query": result.query,
                "agent": self.name
            }
        )
    
    logger.info(f"Persisted {len(result.visited_pages)} pages to SharedMemory")
```

### 4.6 Results Surfacing to Agents

**Output Format**: `BrowserResult` dataclass (see 4.2.1)

**Agent Integration Examples**:

**Example 1: Simple search results in response**
```python
browser_result = await browser.search("Milvus vs Weaviate", max_results=5)

response_text = f"Here are the top resources I found:\n\n"
for i, result in enumerate(browser_result.search_results, 1):
    response_text += f"{i}. **{result.title}**\n   {result.snippet}\n   {result.url}\n\n"

return AgentResponse(content=response_text, metadata={...})
```

**Example 2: Deep analysis with page content**
```python
browser_result = await browser.search_and_visit("Python async best practices", visit_top_n=3)

# Combine snippets into context
context = "\n\n".join([
    f"Source: {page.title}\n{page.text[:500]}..."
    for page in browser_result.visited_pages
])

# Synthesize with LLM
synthesis_prompt = f"User asked: {user_query}\n\nContext from web:\n{context}\n\nProvide a comprehensive answer:"
answer = await self.client.get_chat_completion(messages=[...], ...)

return AgentResponse(content=answer, metadata={"sources": [...]})
```

**Example 3: Forwarding to specialist**
```python
# CoordinationAgent delegates web-enhanced task to PythonExpert
browser_result = await browser.search("Python Milvus integration", max_results=3)

expert_message = {
    "content": user_query,
    "context": {
        "web_results": [r.snippet for r in browser_result.search_results],
        "source_urls": [r.url for r in browser_result.search_results]
    }
}

expert_response = await self._get_expert_response("python_expert", expert_message)
```

---

## 5. Implementation Plan

### 5.1 Phase 1: Core Infrastructure (Week 1)

**Tasks**:
1. Create `tools/browser_tool.py` with `BrowserTool`, `BrowserResult`, `SearchResult`, `PageContent`
2. Implement `TavilySearchEngine` and `DuckDuckGoSearchEngine`
3. Add `BrowserToolConfig` to `utils/config_manager.py`
4. Add configuration schema to `config.yaml` and `config.default.yaml`
5. Create basic unit tests for search engines (mocked responses)

**Deliverables**:
- `tools/browser_tool.py` (300-400 LOC)
- Updated `utils/config_manager.py`
- Updated `config.yaml` with `browser_tool` section
- `tests/unit/test_browser_tool.py` (search engine tests)

**Dependencies**:
- `httpx` (async HTTP client)
- `beautifulsoup4` (HTML parsing)

### 5.2 Phase 2: Browser Automation (Week 2)

**Tasks**:
1. Implement `PageNavigator` class using Playwright
2. Add `navigate_and_extract()` method to `BrowserTool`
3. Implement content extraction with BeautifulSoup
4. Add timeout and retry logic
5. Create integration tests (requires Playwright installation)

**Deliverables**:
- Browser automation support in `BrowserTool`
- `tests/integration/test_browser_navigation.py`
- Documentation: `docs/guides/browser_tool_usage.md`

**Dependencies**:
- `playwright` (install with `playwright install chromium`)

### 5.3 Phase 3: Agent Integration (Week 3)

**Tasks**:
1. Add browser tool invocation to `CoordinationAgent`
2. Implement heuristics for when to use browser tool
3. Add memory persistence logic (with opt-in decision)
4. Create example queries in `examples/browser_tool_demo.py`
5. Update `AGENTS.md` with browser tool documentation

**Deliverables**:
- Browser tool integrated into `CoordinationAgent`
- Example scripts demonstrating usage
- Updated documentation in `AGENTS.md`

### 5.4 Phase 4: Additional Providers (Week 4)

**Tasks**:
1. Implement `BingSearchEngine` (optional)
2. Implement `GoogleSearchEngine` (optional)
3. Implement `SearXNGSearchEngine` (self-hosted support)
4. Add provider selection tests
5. Document provider setup in `docs/configuration/browser_tool.md`

**Deliverables**:
- Support for 4-5 search providers
- Comprehensive provider documentation
- Migration guide for switching providers

### 5.5 Phase 5: Polish & Production Readiness (Week 5)

**Tasks**:
1. Add health check endpoint for browser tool
2. Implement caching layer (optional)
3. Add metrics/observability (integrate with `utils/observability.py`)
4. Performance tuning (parallelization, connection pooling)
5. Security audit (API key handling, XSS prevention)
6. Create troubleshooting guide

**Deliverables**:
- Production-ready browser tool
- Observability integration
- Security documentation
- Troubleshooting guide in `docs/guides/troubleshooting.md`

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Location**: `tests/unit/test_browser_tool.py`

**Coverage**:
- Configuration loading (`BrowserToolConfig.from_env()`)
- Search engine creation (factory pattern)
- Result parsing (mock API responses)
- Error handling (invalid API keys, timeouts)
- Fallback logic (primary → fallback provider)

**Example**:
```python
@pytest.mark.asyncio
async def test_tavily_search_success(mock_httpx_client):
    """Test successful Tavily search."""
    mock_response = {
        "results": [
            {"title": "Test", "url": "https://example.com", "content": "snippet", "score": 0.9}
        ]
    }
    mock_httpx_client.post.return_value = AsyncMock(json=lambda: mock_response)
    
    engine = TavilySearchEngine(config=BrowserToolConfig(search_api_key="test"))
    results = await engine.query("test query", max_results=5)
    
    assert len(results) == 1
    assert results[0].title == "Test"
    assert results[0].score == 0.9
```

### 6.2 Integration Tests

**Location**: `tests/integration/test_browser_integration.py`

**Coverage**:
- End-to-end search workflow (requires API key or mock server)
- Browser navigation (requires Playwright)
- Content extraction from real HTML
- Retry logic with simulated failures
- Memory persistence integration

**Approach**:
- Use `pytest.mark.integration` for tests requiring external services
- Use `TEST_DISABLE_BROWSER=1` environment variable to skip in CI
- Mock external APIs in CI, run real tests locally

**Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_and_visit_flow():
    """Test complete search + navigation flow."""
    browser = BrowserTool(agent_name="test")
    result = await browser.search_and_visit("Python asyncio", max_results=3, visit_top_n=1)
    
    assert len(result.search_results) > 0
    assert len(result.visited_pages) == 1
    assert result.visited_pages[0].text  # Content extracted
```

### 6.3 Agent Integration Tests

**Location**: `tests/integration/test_agent_browser.py`

**Coverage**:
- CoordinationAgent using browser tool
- Memory persistence decision logic
- Error handling in agent context
- Multi-agent collaboration with web results

### 6.4 Manual Testing Checklist

- [ ] Search with Tavily API key configured
- [ ] Search with no API key (fallback to DuckDuckGo)
- [ ] Search with invalid API key (error handling)
- [ ] Navigate to URL and extract content
- [ ] Handle timeout gracefully
- [ ] Handle 404/500 errors
- [ ] Verify memory persistence (opt-in)
- [ ] Test agent override configuration
- [ ] Test rate limiting behavior
- [ ] Verify no API keys in logs

---

## 7. Dependency Matrix

### 7.1 Python Dependencies

| Package | Version | Purpose | License | Required |
|---------|---------|---------|---------|----------|
| `httpx` | ≥0.25.0 | Async HTTP client for API calls | BSD | ✅ Yes |
| `beautifulsoup4` | ≥4.12.0 | HTML parsing | MIT | ✅ Yes |
| `lxml` | ≥4.9.0 | Fast XML/HTML parser (bs4 backend) | BSD | ✅ Yes |
| `playwright` | ≥1.40.0 | Browser automation | Apache 2.0 | ⚠️ Optional* |
| `selenium` | ≥4.15.0 | Alternative browser automation | Apache 2.0 | ❌ Optional |

*Required only if `browser_engine != "none"`

### 7.2 External Services

| Service | Required For | Free Tier | Setup Complexity |
|---------|-------------|-----------|------------------|
| Tavily API | Primary search | 1000 req/month | Low (signup + API key) |
| Bing Search API | Alternative search | No | Medium (Azure account) |
| Google CSE | Alternative search | 100 req/day | Medium (GCP project) |
| SearXNG | Self-hosted search | Unlimited | High (Docker deployment) |

### 7.3 System Dependencies

**For Playwright**:
```bash
# Install Playwright browsers
playwright install chromium

# Or install all browsers
playwright install
```

**For Selenium** (if chosen):
```bash
# Requires browser drivers (chromedriver, geckodriver, etc.)
# Or use webdriver-manager
pip install webdriver-manager
```

### 7.4 Dependency Installation

**Update `requirements.txt`**:
```txt
# Existing dependencies
openai>=1.0.0
loguru>=0.7.0
# ...

# Browser tool dependencies
httpx>=0.25.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
playwright>=1.40.0; extra == "browser"
```

**Installation**:
```bash
# Base installation (search only)
pip install -r requirements.txt

# With browser automation
pip install -r requirements.txt
pip install ".[browser]"
playwright install chromium
```

---

## 8. Acceptance Checklist

### 8.1 Functional Requirements

- [ ] Browser tool can perform web searches using Tavily API
- [ ] Browser tool falls back to DuckDuckGo when Tavily is unavailable
- [ ] Browser tool can navigate to URLs and extract content (with Playwright)
- [ ] Configuration loads correctly from `config.yaml` and environment variables
- [ ] Agent-specific overrides work correctly
- [ ] Agents can invoke browser tool without breaking existing functionality
- [ ] Browser results are returned in structured `BrowserResult` format
- [ ] Memory persistence is opt-in and works correctly
- [ ] Error handling is graceful (no crashes on search/navigation failures)
- [ ] Retry logic works with exponential backoff

### 8.2 Non-Functional Requirements

- [ ] Search latency <5 seconds (p95) with Tavily
- [ ] Navigation + extraction latency <10 seconds (p95)
- [ ] No API keys logged or exposed in error messages
- [ ] Respects rate limits (uses delays between requests)
- [ ] Works in offline mode (with SearXNG or cached data)
- [ ] Minimal memory footprint (<100MB per browser instance)

### 8.3 Documentation Requirements

- [ ] Design document completed (`docs/design/browser_tool.md`) ✅
- [ ] Configuration reference updated (`docs/configuration/browser_tool.md`)
- [ ] Usage guide created (`docs/guides/browser_tool_usage.md`)
- [ ] AGENTS.md updated with browser tool section
- [ ] ROADMAP.md updated with browser tool integration milestone
- [ ] Example scripts in `examples/browser_tool_demo.py`
- [ ] Troubleshooting guide in `docs/guides/troubleshooting.md`

### 8.4 Testing Requirements

- [ ] Unit test coverage ≥80% for `tools/browser_tool.py`
- [ ] Integration tests pass with mocked APIs
- [ ] Integration tests pass with real Tavily API (manual)
- [ ] Agent integration tests pass (CoordinationAgent + browser tool)
- [ ] Manual testing checklist completed (see 6.4)

### 8.5 Code Quality Requirements

- [ ] Code follows existing style conventions (Black, isort)
- [ ] No linting errors (flake8, mypy)
- [ ] Type hints added for all public methods
- [ ] Docstrings follow NumPy style
- [ ] Logging uses loguru with correlation IDs
- [ ] Error messages are actionable and user-friendly

---

## 9. Open Questions & Risks

### 9.1 Open Questions

1. **Q: Should browser tool support authenticated searches (e.g., behind login)?**
   - **A**: Defer to Phase 6 (future). Initial implementation focuses on public content.

2. **Q: How should we handle JavaScript-heavy sites that require rendering?**
   - **A**: Use Playwright for full rendering. Provide `browser_engine: "none"` option for HTTP-only mode.

3. **Q: Should search results be cached to reduce API costs?**
   - **A**: Optional feature. Start with `cache_enabled: false`, add caching in Phase 5 if needed.

4. **Q: Which agents should have browser tool enabled by default?**
   - **A**: Initially, only `CoordinationAgent`. Other agents opt-in via explicit invocation.

5. **Q: How do we handle CAPTCHA or bot detection?**
   - **A**: Accept risk for Phase 1. Mitigation: use rotating user agents, add delays. Consider CAPTCHA-solving services in future.

6. **Q: Should browser tool integrate with LangChain/LangGraph for visual workflow?**
   - **A**: Defer to H2 (UI/UX Enablement) milestone in ROADMAP. Keep implementation framework-agnostic for now.

### 9.2 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Tavily API quota exhaustion** | Medium | High | Implement fallback to DuckDuckGo; add quota monitoring |
| **Playwright stability issues** | Low | Medium | Test extensively; provide fallback to HTTP-only mode |
| **Search provider changes** | Medium | Medium | Abstract providers behind interface; monitor for breaking changes |
| **Rate limiting / IP blocks** | Medium | Medium | Add delays between requests; support proxies in future |
| **Dependency bloat (Playwright)** | Low | Low | Make browser automation optional; document lightweight alternatives |
| **Security (XSS in extracted content)** | Medium | High | Sanitize extracted HTML; never execute scripts |

### 9.3 Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **API key leakage** | Low | High | Use `.env` + `.gitignore`; audit logs for key exposure |
| **Cost overruns (paid APIs)** | Low | Medium | Default to free tier providers; add quota alerts |
| **Slow response times** | Medium | Medium | Set aggressive timeouts; provide async interface |
| **Memory leaks (browser instances)** | Low | Medium | Ensure proper cleanup in finally blocks; add monitoring |

### 9.4 User Experience Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Confusing setup (API keys)** | High | Medium | Provide clear documentation; default to zero-config DuckDuckGo |
| **Unexpected memory writes** | Low | High | Require explicit opt-in; log all memory operations |
| **Slow interactions (users wait)** | Medium | High | Show progress indicators; set reasonable timeouts |

---

## 10. Follow-Up Tasks (Post-Design)

### 10.1 Implementation Tickets

1. **[BROWSER-1] Core browser tool infrastructure**
   - Estimate: 3 days
   - Assignee: TBD
   - Dependencies: None

2. **[BROWSER-2] Tavily and DuckDuckGo search engines**
   - Estimate: 2 days
   - Assignee: TBD
   - Dependencies: BROWSER-1

3. **[BROWSER-3] Playwright navigation and extraction**
   - Estimate: 3 days
   - Assignee: TBD
   - Dependencies: BROWSER-1

4. **[BROWSER-4] Configuration integration**
   - Estimate: 2 days
   - Assignee: TBD
   - Dependencies: BROWSER-1

5. **[BROWSER-5] CoordinationAgent integration**
   - Estimate: 3 days
   - Assignee: TBD
   - Dependencies: BROWSER-2, BROWSER-3

6. **[BROWSER-6] Memory persistence logic**
   - Estimate: 2 days
   - Assignee: TBD
   - Dependencies: BROWSER-5

7. **[BROWSER-7] Additional search providers (Bing, Google, SearXNG)**
   - Estimate: 3 days
   - Assignee: TBD
   - Dependencies: BROWSER-2

8. **[BROWSER-8] Documentation and examples**
   - Estimate: 2 days
   - Assignee: TBD
   - Dependencies: All

9. **[BROWSER-9] Testing and QA**
   - Estimate: 3 days
   - Assignee: TBD
   - Dependencies: All

10. **[BROWSER-10] Observability and metrics**
    - Estimate: 2 days
    - Assignee: TBD
    - Dependencies: BROWSER-5

**Total Estimate**: ~25 days (5 weeks at 1 FTE)

### 10.2 Documentation Tasks

- [ ] Create `docs/configuration/browser_tool.md` (configuration reference)
- [ ] Create `docs/guides/browser_tool_usage.md` (usage guide)
- [ ] Update `AGENTS.md` with browser tool section
- [ ] Update `docs/ROADMAP.md` with browser tool milestone
- [ ] Create `examples/browser_tool_demo.py` (example script)
- [ ] Add browser tool troubleshooting to `docs/guides/troubleshooting.md`

### 10.3 Review & Approval

- [ ] Design review with core team
- [ ] Security review (API key handling, XSS)
- [ ] Performance benchmarking (latency, resource usage)
- [ ] User acceptance testing (example queries)
- [ ] Final sign-off before merging to main

---

## Appendices

### Appendix A: Configuration Example (Full)

```yaml
# config.yaml
api_config:
  # ... existing chat_api, embedding_api ...
  
  browser_tool:
    enabled: true
    
    # Search configuration
    search_provider: "tavily"  # Primary provider
    search_api_key: null  # Set via BROWSER_SEARCH_API_KEY
    search_api_base_url: null  # For self-hosted SearXNG
    fallback_provider: "duckduckgo"
    
    # Browser settings
    browser_engine: "playwright"  # "playwright" | "selenium" | "none"
    headless: true
    user_agent: "Mozilla/5.0 (multi-agent-brain/1.0)"
    viewport_width: 1280
    viewport_height: 720
    
    # Timeouts
    search_timeout: 10
    navigation_timeout: 30
    extraction_timeout: 15
    
    # Retry & rate limiting
    max_retries: 3
    retry_delay: 2.0
    rate_limit_delay: 1.0
    
    # Content extraction
    max_content_length: 100000
    extract_images: false
    extract_links: true
    
    # Cache (optional)
    cache_enabled: false
    cache_ttl: 3600
    
  # Agent overrides
  agent_overrides:
    coordination:
      browser_tool:
        search_provider: "tavily"
        search_timeout: 15
    python_expert:
      browser_tool:
        search_provider: "google"
        max_retries: 5
```

### Appendix B: Search Provider Setup Guides

#### B.1 Tavily Setup

1. Sign up at https://tavily.com
2. Navigate to dashboard and create API key
3. Set environment variable:
   ```bash
   export BROWSER_SEARCH_API_KEY="tvly-your-key-here"
   ```

#### B.2 Google Custom Search Setup

1. Go to https://console.cloud.google.com
2. Enable Custom Search JSON API
3. Create API key
4. Create custom search engine at https://cse.google.com
5. Set environment variables:
   ```bash
   export BROWSER_SEARCH_API_KEY="your-google-api-key"
   export GOOGLE_CSE_ID="your-cse-id"
   ```

#### B.3 SearXNG Self-Hosted Setup

```bash
# Using Docker Compose
git clone https://github.com/searxng/searxng-docker.git
cd searxng-docker
docker-compose up -d

# Configure browser tool
export BROWSER_SEARCH_PROVIDER="searxng"
export BROWSER_SEARCH_BASE_URL="http://localhost:8080"
```

### Appendix C: API Response Examples

#### C.1 Tavily API Response

```json
{
  "query": "Milvus vector database",
  "answer": "Milvus is an open-source vector database built for AI applications...",
  "results": [
    {
      "title": "Milvus Documentation",
      "url": "https://milvus.io/docs",
      "content": "Milvus is a highly flexible, reliable, and blazing-fast...",
      "score": 0.95,
      "published_date": "2024-01-15"
    }
  ],
  "response_time": 0.8
}
```

#### C.2 DuckDuckGo HTML Parsing

```html
<!-- Extracted from DDG search results -->
<div class="result">
  <h2 class="result__title">
    <a href="https://milvus.io/docs">Milvus Documentation</a>
  </h2>
  <div class="result__snippet">
    Milvus is a highly flexible, reliable, and blazing-fast...
  </div>
</div>
```

### Appendix D: Glossary

| Term | Definition |
|------|------------|
| **Browser Tool** | Unified interface for web search and browsing capabilities |
| **Search Engine** | Component responsible for querying search APIs or scraping results |
| **Page Navigator** | Component using Playwright/Selenium to automate browser interactions |
| **Content Extractor** | Component parsing HTML and extracting structured data |
| **Fallback Provider** | Secondary search provider used when primary fails |
| **Agent Override** | Configuration that overrides global settings for specific agents |

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-11-14 | AI Coding Agent | Initial design document created |

---

## References

- [AGENTS.md](../../AGENTS.md) - AI Coding Agent Developer Guide
- [ROADMAP.md](../ROADMAP.md) - Project roadmap and milestones
- [ConfigManager](../../utils/config_manager.py) - Configuration management implementation
- [BaseAgent](../../agents/base.py) - Agent base class and protocol
- [SharedMemory](../../agents/shared_memory.py) - Memory persistence layer
- [Tavily API Documentation](https://docs.tavily.com)
- [Playwright Documentation](https://playwright.dev/python)
