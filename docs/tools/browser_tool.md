# Browser Tool - Web Search and Navigation

> **Status**: Implemented and tested  
> **Related**: [Browser Tool Design](../design/browser_tool.md) · [Browser Tool Configuration](../configuration/browser_tool.md) · [ROADMAP H3](../ROADMAP.md#h3--productization-extensibility--packaging)

## Overview

The Browser Tool enables agents in the multi-agent-brain system to:

1. **Search the web** using multiple search providers (Tavily, DuckDuckGo, Bing, Google, SearXNG)
2. **Navigate web pages** via Playwright browser automation
3. **Extract content** from HTML using BeautifulSoup
4. **Optionally persist findings** to SharedMemory for future reference

**Key Design Principles**:
- 🌐 **Provider flexibility**: Primary provider with automatic fallback
- 🔧 **Zero-config capable**: Works without API keys using DuckDuckGo
- 🎯 **Agent-controlled**: Agents decide when to search and what to persist
- ⚡ **Async-native**: Built on asyncio for non-blocking operations
- 📊 **Observable**: Comprehensive logging and error handling

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Search Providers](#search-providers)
3. [Configuration](#configuration)
4. [Usage Examples](#usage-examples)
5. [Browser Automation](#browser-automation)
6. [Memory Persistence](#memory-persistence)
7. [Error Handling](#error-handling)
8. [Observability](#observability)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## Quick Start

### 1. Install Dependencies

```bash
# Core dependencies (already in requirements.txt)
pip install httpx beautifulsoup4 lxml

# Browser automation (optional, for page navigation)
pip install playwright
playwright install chromium
```

Or use the Makefile target:
```bash
make setup-playwright
```

### 2. Configure Search Provider

**Option A: Tavily (Recommended for AI use cases)**
```bash
# Get free API key from https://tavily.com (1000 requests/month)
export BROWSER_SEARCH_API_KEY="tvly-your-api-key-here"
export BROWSER_SEARCH_PROVIDER="tavily"
```

**Option B: DuckDuckGo (Zero-config fallback)**
```bash
# No API key required - just set provider
export BROWSER_SEARCH_PROVIDER="duckduckgo"
```

### 3. Use in Agents

```python
from tools.browser_tool import BrowserTool

# Initialize with agent-specific config
browser = BrowserTool(agent_name="coordination")

# Simple search
result = await browser.search("Milvus vector database quickstart", max_results=5)

# Access results
for search_result in result.search_results:
    print(f"{search_result.title}: {search_result.url}")
```

### 4. Verify Setup

Run the browser tool example:
```bash
python examples/browser_tool_demo.py
```

Run integration tests:
```bash
make test-fast  # Includes browser tool unit tests
pytest tests/unit/test_browser_tool_integration.py -v
```

---

## Search Providers

### Provider Comparison

| Provider | API Key | Free Tier | Quality | Speed | Best For |
|----------|---------|-----------|---------|-------|----------|
| **Tavily** | Required | 1000/month | ⭐⭐⭐⭐⭐ | Fast | AI agents, structured results |
| **DuckDuckGo** | None | Unlimited* | ⭐⭐⭐ | Fast | Zero-config, privacy, fallback |
| **Bing** | Required | Paid only | ⭐⭐⭐⭐ | Fast | Enterprise, high volume |
| **Google CSE** | Required | 100/day | ⭐⭐⭐⭐⭐ | Fast | Custom search engines |
| **SearXNG** | None | Unlimited | ⭐⭐⭐ | Variable | Self-hosted, privacy |

*\*DuckDuckGo uses HTML scraping with respectful rate limiting*

### Tavily Setup (Recommended)

**Why Tavily?**
- Optimized for LLM/AI agent workflows
- Returns structured, summarized results
- Includes AI-generated answers
- Fast response times (~1-2 seconds)
- Generous free tier

**Setup Steps**:
1. Visit https://tavily.com and sign up
2. Copy your API key from the dashboard
3. Set environment variable:
   ```bash
   export BROWSER_SEARCH_API_KEY="tvly-xxxxxxxxxxxxx"
   # Or add to .env file
   echo "BROWSER_SEARCH_API_KEY=tvly-xxxxxxxxxxxxx" >> .env
   ```

**Example Response**:
```json
{
  "query": "Milvus vector database",
  "search_results": [
    {
      "title": "Milvus Documentation",
      "url": "https://milvus.io/docs",
      "snippet": "Official Milvus documentation...",
      "score": 0.95
    }
  ],
  "answer": "Milvus is an open-source vector database..."
}
```

### DuckDuckGo Setup (Zero-Config)

**Why DuckDuckGo?**
- No API key required
- Privacy-focused (no tracking)
- Reliable fallback when other providers fail
- Works immediately after installation

**Limitations**:
- HTML scraping (subject to structure changes)
- Lower result quality than paid APIs
- Soft rate limits (use respectful delays)

**Configuration**:
```bash
export BROWSER_SEARCH_PROVIDER="duckduckgo"
# No API key needed!
```

### Bing Search API Setup

**Prerequisites**:
- Azure subscription
- Bing Search v7 API resource

**Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="bing"
export BROWSER_SEARCH_API_KEY="your-azure-bing-key"
export BROWSER_SEARCH_BASE_URL="https://api.bing.microsoft.com/v7.0/search"
```

### Google Custom Search Setup

**Prerequisites**:
- Google Cloud project
- Custom Search JSON API enabled
- Custom search engine ID

**Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="google"
export BROWSER_SEARCH_API_KEY="your-google-api-key"
export GOOGLE_CSE_ID="your-custom-search-engine-id"
```

### SearXNG Setup (Self-Hosted)

**Prerequisites**:
- Docker or self-hosted SearXNG instance

**Setup**:
```bash
# Start SearXNG container
docker run -d -p 8888:8080 searxng/searxng

# Configure browser tool
export BROWSER_SEARCH_PROVIDER="searxng"
export BROWSER_SEARCH_BASE_URL="http://localhost:8888"
```

---

## Configuration

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BROWSER_TOOL_ENABLED` | Enable/disable globally | `true` | No |
| `BROWSER_SEARCH_PROVIDER` | Search provider name | `tavily` | No |
| `BROWSER_SEARCH_API_KEY` | API key for provider | `null` | Provider-dependent |
| `BROWSER_SEARCH_BASE_URL` | Custom provider URL | `null` | For SearXNG |
| `BROWSER_FALLBACK_PROVIDER` | Fallback when primary fails | `duckduckgo` | No |
| `BROWSER_ENGINE` | Browser automation engine | `playwright` | No |
| `BROWSER_HEADLESS` | Run browser headlessly | `true` | No |
| `BROWSER_USER_AGENT` | HTTP user agent string | `Mozilla/5.0 (multi-agent-brain/1.0)` | No |
| `BROWSER_SEARCH_TIMEOUT` | Search timeout (seconds) | `10` | No |
| `BROWSER_NAVIGATION_TIMEOUT` | Page load timeout (seconds) | `30` | No |
| `BROWSER_EXTRACTION_TIMEOUT` | Content extraction timeout | `15` | No |
| `BROWSER_MAX_RETRIES` | Retry attempts | `3` | No |
| `BROWSER_RETRY_DELAY` | Retry delay (seconds) | `2.0` | No |
| `BROWSER_RATE_LIMIT_DELAY` | Delay between requests | `1.0` | No |
| `BROWSER_MAX_CONTENT_LENGTH` | Max extracted text length | `100000` | No |
| `BROWSER_EXTRACT_IMAGES` | Extract image URLs | `false` | No |
| `BROWSER_EXTRACT_LINKS` | Extract page links | `true` | No |
| `BROWSER_CACHE_ENABLED` | Enable result caching | `false` | No |
| `BROWSER_CACHE_TTL` | Cache TTL (seconds) | `3600` | No |

### YAML Configuration

Browser tool configuration integrates with the existing `config.yaml` structure:

```yaml
api_config:
  # Existing chat_api, embedding_api...
  
  browser_tool:
    enabled: true
    search_provider: "tavily"
    search_api_key: null  # Override via BROWSER_SEARCH_API_KEY
    fallback_provider: "duckduckgo"
    browser_engine: "playwright"
    headless: true
    search_timeout: 10
    navigation_timeout: 30
    max_retries: 3
    
  # Agent-specific overrides
  agent_overrides:
    coordination:
      browser_tool:
        search_provider: "tavily"
        search_timeout: 15  # More time for complex queries
    
    python_expert:
      browser_tool:
        enabled: false  # Disable for specific agent
```

### Configuration Priority

The configuration loading follows the same precedence as other APIs:

1. **Highest**: Agent-specific YAML overrides (`api_config.agent_overrides.<agent>.browser_tool`)
2. **High**: Environment variables (`BROWSER_*`)
3. **Medium**: Global YAML config (`api_config.browser_tool`)
4. **Lowest**: Hard-coded defaults in `BrowserToolConfig`

### Loading Configuration in Code

```python
from utils import get_browser_tool_config

# Get configuration for specific agent
config = get_browser_tool_config("coordination")

print(f"Provider: {config.search_provider}")
print(f"Enabled: {config.enabled}")
print(f"Timeout: {config.search_timeout}s")
```

---

## Usage Examples

### Basic Web Search

```python
from tools.browser_tool import BrowserTool

async def search_example():
    browser = BrowserTool(agent_name="coordination")
    
    # Execute search
    result = await browser.search("Python async best practices", max_results=5)
    
    # Check for errors
    if result.error:
        print(f"Search failed: {result.error}")
        return
    
    # Process results
    print(f"Found {len(result.search_results)} results for: {result.query}")
    
    for item in result.search_results:
        print(f"\nTitle: {item.title}")
        print(f"URL: {item.url}")
        print(f"Snippet: {item.snippet[:100]}...")
        if item.score:
            print(f"Relevance: {item.score:.2f}")
    
    # Tavily provides AI-generated answers
    if result.answer:
        print(f"\nAI Summary: {result.answer}")
```

### Search + Visit Pages

```python
async def search_and_visit_example():
    browser = BrowserTool(agent_name="coordination")
    
    # Search and visit top 3 results
    result = await browser.search_and_visit(
        query="Milvus vector database quickstart",
        max_results=5,
        visit_top_n=3
    )
    
    # Access search results
    print(f"Search results: {len(result.search_results)}")
    
    # Access visited page content
    print(f"\nVisited {len(result.visited_pages)} pages:")
    for page in result.visited_pages:
        print(f"\n=== {page.title} ===")
        print(f"URL: {page.url}")
        print(f"Content preview: {page.text[:200]}...")
        print(f"Links found: {len(page.links)}")
        print(f"Images found: {len(page.images)}")
```

### Navigate Specific URL

```python
async def navigate_example():
    browser = BrowserTool(agent_name="coordination")
    
    # Navigate and extract content
    content = await browser.navigate_and_extract(
        "https://milvus.io/docs/quickstart.html"
    )
    
    print(f"Title: {content.title}")
    print(f"URL: {content.url}")
    print(f"Extracted text: {content.text[:500]}...")
    print(f"Links: {len(content.links)}")
    print(f"Timestamp: {content.timestamp}")
```

### Integration in Agents

```python
from agents.base import BaseAgent, AgentResponse
from tools.browser_tool import BrowserTool

class MyAgent(BaseAgent):
    name = "my_agent"
    
    async def handle_message(self, message: str, conversation_state=None) -> AgentResponse:
        # Check if message needs web search
        if self._should_search_web(message):
            browser = self._get_browser_tool()
            result = await browser.search(message, max_results=5)
            
            if result.error:
                logger.warning(f"Browser search failed: {result.error}")
                # Continue with fallback logic
            else:
                # Incorporate search results into response
                context = self._format_search_results(result)
                # ... synthesize answer with LLM
        
        return AgentResponse(content="...", metadata={})
```

### Error Handling

```python
from tools.browser_tool import (
    BrowserTool,
    SearchProviderError,
    NavigationError,
    RateLimitError
)

async def robust_search():
    browser = BrowserTool(agent_name="coordination")
    
    try:
        result = await browser.search("my query")
        
        if result.error:
            print(f"Degraded result: {result.error}")
            # Use partial results if available
            
    except RateLimitError as e:
        print(f"Rate limited: {e}")
        # Wait and retry or use fallback provider
        
    except SearchProviderError as e:
        print(f"Provider error: {e}")
        # Will automatically try fallback if configured
        
    except NavigationError as e:
        print(f"Navigation failed: {e}")
        # Handle browser automation failures
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Log and degrade gracefully
```

---

## Browser Automation

### Playwright Setup

**Installation**:
```bash
pip install playwright
playwright install chromium

# Or via Makefile
make setup-playwright
```

**System Requirements**:
- 500MB+ disk space for browser binaries
- Linux: libglib2.0-0, libnss3, libxcb1, libxcomposite1, etc.
- macOS: No additional requirements
- Windows: No additional requirements

**Troubleshooting Playwright Installation**:

1. **Missing system libraries (Linux)**:
   ```bash
   # Ubuntu/Debian
   playwright install-deps chromium
   
   # Manual dependencies
   apt-get install -y libnss3 libxcb1 libxcomposite1 libxdamage1 \
       libxext6 libxfixes3 libxrandr2 libgbm1 libpangocairo-1.0-0 \
       libasound2
   ```

2. **Permission issues**:
   ```bash
   # Run with user permissions (avoid root)
   python -m playwright install chromium --user
   ```

3. **Disk space errors**:
   ```bash
   # Check available space
   df -h
   # Clean up old browsers
   python -m playwright uninstall --all
   python -m playwright install chromium
   ```

### HTTP-Only Mode (No Browser)

If browser automation is not needed or Playwright cannot be installed:

```bash
export BROWSER_ENGINE="none"
```

This disables `navigate_and_extract()` and `search_and_visit()`, but basic search still works.

### Browser Configuration Options

```python
from utils import get_browser_tool_config

config = get_browser_tool_config("my_agent")

# Headless mode (no visible window)
config.headless = True  # Default, faster

# Viewport size
config.viewport_width = 1920
config.viewport_height = 1080

# User agent
config.user_agent = "Mozilla/5.0 (custom agent)"

# Timeouts
config.navigation_timeout = 30  # Page load timeout
config.extraction_timeout = 15  # Content extraction timeout
```

### Advanced Navigation

```python
from tools.browser_tool import BrowserTool

async def advanced_navigation():
    browser = BrowserTool(agent_name="coordination")
    
    # Get internal navigator
    navigator = browser._get_navigator()
    
    # Navigate with custom timeout
    page = await navigator.goto("https://example.com", timeout=60)
    
    # Extract content
    parser = browser.parser
    content = await parser.extract_from_page(page, "https://example.com")
    
    # Clean up
    await page.close()
    await navigator.close()
```

---

## Memory Persistence

### Design Philosophy

**Explicit Opt-In**: The browser tool does NOT automatically persist results to SharedMemory. Agents decide when to persist based on:

- Query intent (research vs. transient lookup)
- Result quality (successful extraction vs. errors)
- User context (collaborative session vs. one-off query)

### Persistence Example

```python
from tools.browser_tool import BrowserTool
from agents.shared_memory import SharedMemory

async def search_with_persistence():
    browser = BrowserTool(agent_name="coordination")
    memory = SharedMemory(agent_name="coordination")
    
    # Execute search + visit
    result = await browser.search_and_visit(
        query="Milvus deployment best practices",
        max_results=5,
        visit_top_n=2
    )
    
    # Decide whether to persist
    if result.visited_pages and not result.error:
        # Persist each visited page
        for page in result.visited_pages:
            memory.store_knowledge(
                collection="web_snapshots",
                tenant_id="my_project",
                content={
                    "url": page.url,
                    "title": page.title,
                    "text": page.text,
                    "query": result.query
                },
                metadata={
                    "source": "browser_tool",
                    "timestamp": page.timestamp,
                    "search_provider": result.metadata.get("provider")
                }
            )
        
        print(f"Persisted {len(result.visited_pages)} pages to memory")
```

### Coordination Agent Persistence

The `CoordinationAgent` includes built-in persistence logic:

```python
# Inside CoordinationAgent
async def _persist_browser_results(self, browser_result, tenant_id):
    """Persist browser results to SharedMemory if configured."""
    if not self.browser_config.persist_results:
        return
    
    for page in browser_result.get("visited_pages", []):
        await self.memory.store_knowledge(
            collection="web_snapshots",
            tenant_id=tenant_id,
            content={
                "url": page["url"],
                "title": page["title"],
                "text": page["text"],
                "query": browser_result["query"]
            },
            metadata={"source": "browser_tool"}
        )
```

**Configuration**:
```yaml
api_config:
  agent_overrides:
    coordination:
      browser_tool:
        persist_results: true  # Enable automatic persistence
```

### Retrieving Persisted Results

```python
from agents.shared_memory import SharedMemory

memory = SharedMemory(agent_name="coordination")

# Search for previously visited content
results = memory.search_knowledge(
    collection="web_snapshots",
    tenant_id="my_project",
    query="Milvus deployment best practices",
    top_k=5,
    threshold=0.7
)

for result in results:
    print(f"URL: {result['content']['url']}")
    print(f"Title: {result['content']['title']}")
    print(f"Relevance: {result['score']:.2f}")
```

---

## Error Handling

### Exception Hierarchy

```
BrowserToolError (base)
├── SearchProviderError (API failures, auth issues)
│   └── RateLimitError (specific rate limit handling)
├── NavigationError (browser automation failures)
└── ExtractionError (content parsing failures)
```

### Graceful Degradation

The browser tool implements automatic fallback mechanisms:

1. **Provider Fallback**: Primary provider fails → Falls back to `fallback_provider`
2. **Retry Logic**: Transient errors → Automatic retry with exponential backoff
3. **Partial Results**: Navigation failures → Returns search results without page content
4. **Error Metadata**: Failed operations → Populates `result.error` with diagnostic info

### Common Error Scenarios

#### 1. API Key Invalid or Missing

```python
# Exception: SearchProviderError: Tavily API authentication failed
```

**Resolution**:
- Verify API key is correct: `echo $BROWSER_SEARCH_API_KEY`
- Check key has not expired (Tavily dashboard)
- Set fallback provider: `export BROWSER_FALLBACK_PROVIDER=duckduckgo`

#### 2. Rate Limit Exceeded

```python
# Exception: RateLimitError: Tavily API rate limit exceeded
```

**Resolution**:
- Wait for quota to reset (check provider dashboard)
- Implement request throttling in agent logic
- Use fallback provider temporarily
- Upgrade provider plan if persistent

#### 3. Playwright Not Installed

```python
# Exception: NavigationError: playwright is required for browser navigation
```

**Resolution**:
```bash
pip install playwright
playwright install chromium
```

#### 4. Page Load Timeout

```python
# Exception: NavigationError: Failed to navigate to {url}: Timeout 30000ms exceeded
```

**Resolution**:
- Increase timeout: `export BROWSER_NAVIGATION_TIMEOUT=60`
- Check URL is accessible: `curl -I <url>`
- Verify network connectivity
- Consider HTTP-only mode if automation not critical

#### 5. Content Extraction Failed

```python
# Exception: ExtractionError: beautifulsoup4 is required for content extraction
```

**Resolution**:
```bash
pip install beautifulsoup4 lxml
```

---

## Observability

### Structured Logging

The browser tool integrates with the project's observability system:

```python
from loguru import logger

# All browser operations log with structured context
# Example log output:
"""
2024-11-15T10:30:45.123 | INFO     | coordination    | run=abc123 | corr=xyz789 | 
tools.browser_tool | BrowserTool initialized for agent 'coordination' with provider 'tavily'

2024-11-15T10:30:46.234 | INFO     | coordination    | run=abc123 | corr=xyz789 | 
tools.browser_tool | Tavily search returned 5 results for query: Milvus vector database

2024-11-15T10:30:47.345 | WARNING  | coordination    | run=abc123 | corr=xyz789 | 
tools.browser_tool | Failed to visit https://example.com: Timeout
"""
```

### Metrics Collection

Browser tool usage is tracked via the observability system:

```python
from utils.observability import get_metrics

metrics = get_metrics()

# Available metrics (when ENABLE_METRICS=true):
# - browser_tool.search.total
# - browser_tool.search.success
# - browser_tool.search.errors
# - browser_tool.navigation.total
# - browser_tool.navigation.success
# - browser_tool.latency_ms.p50
# - browser_tool.latency_ms.p95
```

### Accessing Metrics Endpoint

```bash
# Enable metrics in .env
export ENABLE_METRICS=true
export METRICS_PORT=9100

# Start network
make run-network

# Query metrics
curl http://localhost:9100/metrics

# Example response:
{
  "browser_tool": {
    "searches": 42,
    "navigations": 18,
    "errors": 2,
    "avg_latency_ms": 1234,
    "providers": {
      "tavily": 40,
      "duckduckgo": 2
    }
  }
}
```

### Correlation IDs

Browser tool operations inherit correlation IDs from the calling agent:

```python
from utils.observability import correlation_context

async def agent_search(query):
    with correlation_context("my-correlation-id"):
        browser = BrowserTool(agent_name="coordination")
        result = await browser.search(query)
        # All logs include correlation_id="my-correlation-id"
```

### Log Filtering

Filter browser tool logs:

```bash
# Text logs
grep "tools.browser_tool" openagents.log

# JSON logs
jq 'select(.module == "tools.browser_tool")' openagents.json

# Operator dashboard
make operator  # Use --filter-module=tools.browser_tool
```

---

## Troubleshooting

### Diagnostic Checklist

1. **Verify browser tool is enabled**:
   ```python
   from utils import get_browser_tool_config
   config = get_browser_tool_config("coordination")
   print(f"Enabled: {config.enabled}")
   ```

2. **Check API credentials**:
   ```bash
   echo $BROWSER_SEARCH_API_KEY
   # Should show your API key (not empty)
   ```

3. **Test search provider directly**:
   ```bash
   python examples/browser_tool_demo.py
   ```

4. **Verify Playwright installation**:
   ```bash
   python -c "from playwright.async_api import async_playwright; print('OK')"
   playwright --version
   ```

5. **Check logs for errors**:
   ```bash
   grep -i "error\|exception" openagents.log | grep browser_tool
   ```

### Common Issues

#### Search Returns No Results

**Symptoms**: `result.search_results` is empty

**Diagnosis**:
1. Check query is not empty or malformed
2. Verify search provider is online (Tavily status page)
3. Try fallback provider manually:
   ```bash
   export BROWSER_SEARCH_PROVIDER=duckduckgo
   ```

**Resolution**:
- Use more specific search queries
- Check rate limits haven't been exceeded
- Verify network connectivity

#### Browser Tool Not Available to Agents

**Symptoms**: `agent.tools()` returns empty list

**Diagnosis**:
```python
from utils import get_browser_tool_config
config = get_browser_tool_config("my_agent")
print(config.enabled)  # Should be True
```

**Resolution**:
1. Enable globally: `export BROWSER_TOOL_ENABLED=true`
2. Or in config.yaml:
   ```yaml
   api_config:
     browser_tool:
       enabled: true
   ```
3. Restart network: `make run-network`

#### Memory Persistence Not Working

**Symptoms**: Visited pages not stored in SharedMemory

**Diagnosis**:
1. Check persistence is enabled in agent config
2. Verify Milvus is running: `curl http://localhost:19530/health`
3. Check `web_snapshots` collection exists

**Resolution**:
```python
# Verify memory health
from agents.shared_memory import SharedMemory
memory = SharedMemory(agent_name="coordination")
print(memory.health_check())
```

#### High Latency

**Symptoms**: Searches take >10 seconds

**Diagnosis**:
1. Check network latency to provider
2. Review timeout settings
3. Monitor provider rate limits

**Resolution**:
- Increase timeouts if needed:
  ```bash
  export BROWSER_SEARCH_TIMEOUT=30
  export BROWSER_NAVIGATION_TIMEOUT=60
  ```
- Use caching:
  ```bash
  export BROWSER_CACHE_ENABLED=true
  export BROWSER_CACHE_TTL=3600
  ```
- Switch to faster provider (Tavily typically fastest)

### Getting Help

1. **Check logs**: Review structured logs for detailed error messages
2. **Run tests**: `pytest tests/unit/test_browser_tool_integration.py -v`
3. **Consult documentation**:
   - [Browser Tool Design](../design/browser_tool.md)
   - [Configuration Guide](../configuration/browser_tool.md)
   - [Troubleshooting Guide](../guides/troubleshooting.md)
4. **Review examples**: See `examples/browser_tool_demo.py`

---

## API Reference

### BrowserTool Class

```python
class BrowserTool:
    def __init__(self, agent_name: str = "default"):
        """Initialize browser tool with agent-specific configuration."""
        
    async def search(
        self, 
        query: str, 
        max_results: int = 5
    ) -> BrowserResult:
        """Execute web search and return results."""
        
    async def navigate_and_extract(self, url: str) -> PageContent:
        """Navigate to URL and extract page content."""
        
    async def search_and_visit(
        self,
        query: str,
        max_results: int = 5,
        visit_top_n: int = 3
    ) -> BrowserResult:
        """Search and visit top N results, returning combined data."""
```

### Data Models

```python
@dataclass
class SearchResult:
    """Single search result item."""
    title: str
    url: str
    snippet: str
    score: Optional[float] = None
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
    answer: Optional[str] = None  # AI-generated summary (Tavily)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Configuration Model

```python
@dataclass
class BrowserToolConfig:
    enabled: bool = True
    search_provider: str = "tavily"
    search_api_key: Optional[str] = None
    fallback_provider: str = "duckduckgo"
    browser_engine: str = "playwright"
    headless: bool = True
    user_agent: str = "Mozilla/5.0 (multi-agent-brain/1.0)"
    viewport_width: int = 1280
    viewport_height: int = 720
    search_timeout: int = 10
    navigation_timeout: int = 30
    extraction_timeout: int = 15
    max_retries: int = 3
    retry_delay: float = 2.0
    rate_limit_delay: float = 1.0
    max_content_length: int = 100000
    extract_images: bool = False
    extract_links: bool = True
    cache_enabled: bool = False
    cache_ttl: int = 3600
    persist_results: bool = False  # Auto-persist to SharedMemory
```

### Exceptions

```python
class BrowserToolError(Exception):
    """Base exception for browser tool errors."""

class SearchProviderError(BrowserToolError):
    """Search provider specific errors (API key, quota, etc)."""

class NavigationError(BrowserToolError):
    """Browser navigation errors (timeout, 404, network failure)."""

class ExtractionError(BrowserToolError):
    """Content extraction errors."""

class RateLimitError(BrowserToolError):
    """Rate limiting errors from providers."""
```

---

## Related Documentation

- **Design**: [Browser Tool Design Document](../design/browser_tool.md)
- **Configuration**: [Browser Tool Configuration Guide](../configuration/browser_tool.md)
- **Testing**: [Testing Guide - Browser Tool Tests](../testing/README.md)
- **Troubleshooting**: [Troubleshooting Guide - Browser Tool Section](../guides/troubleshooting.md)
- **Roadmap**: [H3 Milestone - Plugin/Tooling Gallery](../ROADMAP.md#h3--productization-extensibility--packaging)
- **Examples**: `examples/browser_tool_demo.py`
- **Agent Guide**: [AGENTS.md - Tool Integration](../../AGENTS.md#9-tool-integration)
