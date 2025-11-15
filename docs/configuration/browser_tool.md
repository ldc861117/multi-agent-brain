# Browser Tool Configuration Reference

> **Status**: Implementation Complete  
> **Related**: [Browser Tool User Guide](../tools/browser_tool.md) · [Browser Tool Design](../design/browser_tool.md)

## Overview

This document provides a comprehensive configuration reference for the Browser Tool, including all environment variables, YAML schema, validation rules, and provider-specific setup instructions.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [YAML Configuration Schema](#yaml-configuration-schema)
3. [Search Provider Setup](#search-provider-setup)
4. [Configuration Validation](#configuration-validation)
5. [Agent-Specific Overrides](#agent-specific-overrides)
6. [Configuration Examples](#configuration-examples)

---

## Environment Variables

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_TOOL_ENABLED` | boolean | `true` | Master switch to enable/disable browser tool globally |
| `BROWSER_SEARCH_PROVIDER` | string | `tavily` | Primary search provider: `tavily`, `duckduckgo`, `bing`, `google`, `searxng` |
| `BROWSER_FALLBACK_PROVIDER` | string | `duckduckgo` | Fallback provider when primary fails (must not require API key) |

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_SEARCH_API_KEY` | string | `null` | API key for primary search provider (required for Tavily, Bing, Google) |
| `TAVILY_API_KEY` | string | `null` | Alternative env var for Tavily API key (backward compatibility) |
| `BING_SEARCH_API_KEY` | string | `null` | Bing Search API key (Azure subscription required) |
| `GOOGLE_API_KEY` | string | `null` | Google Custom Search API key |
| `GOOGLE_CSE_ID` | string | `null` | Google Custom Search Engine ID |

### Network Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_SEARCH_BASE_URL` | string | `null` | Custom base URL for self-hosted providers (SearXNG) |
| `BROWSER_USER_AGENT` | string | `Mozilla/5.0 (multi-agent-brain/1.0)` | HTTP User-Agent header |
| `BROWSER_SEARCH_TIMEOUT` | integer | `10` | Search operation timeout in seconds |
| `BROWSER_NAVIGATION_TIMEOUT` | integer | `30` | Page navigation timeout in seconds |
| `BROWSER_EXTRACTION_TIMEOUT` | integer | `15` | Content extraction timeout in seconds |

### Browser Automation

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_ENGINE` | string | `playwright` | Browser engine: `playwright`, `selenium`, or `none` (HTTP-only) |
| `BROWSER_HEADLESS` | boolean | `true` | Run browser in headless mode (no GUI) |
| `BROWSER_VIEWPORT_WIDTH` | integer | `1280` | Browser viewport width in pixels |
| `BROWSER_VIEWPORT_HEIGHT` | integer | `720` | Browser viewport height in pixels |

### Retry and Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_MAX_RETRIES` | integer | `3` | Maximum retry attempts for failed operations |
| `BROWSER_RETRY_DELAY` | float | `2.0` | Base delay between retries in seconds (exponential backoff) |
| `BROWSER_RATE_LIMIT_DELAY` | float | `1.0` | Minimum delay between consecutive requests |

### Content Extraction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_MAX_CONTENT_LENGTH` | integer | `100000` | Maximum extracted text length in characters |
| `BROWSER_EXTRACT_IMAGES` | boolean | `false` | Extract image URLs from pages |
| `BROWSER_EXTRACT_LINKS` | boolean | `true` | Extract links from pages |

### Caching (Optional)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_CACHE_ENABLED` | boolean | `false` | Enable in-memory result caching |
| `BROWSER_CACHE_TTL` | integer | `3600` | Cache time-to-live in seconds |

### Memory Persistence

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BROWSER_PERSIST_RESULTS` | boolean | `false` | Auto-persist visited pages to SharedMemory (agent override) |

---

## YAML Configuration Schema

### Full Schema

Location: `config.yaml` under `api_config.browser_tool`

```yaml
api_config:
  # Existing sections: chat_api, embedding_api, etc.
  
  browser_tool:
    # Core settings
    enabled: true
    search_provider: "tavily"        # Primary provider
    fallback_provider: "duckduckgo"  # Zero-config fallback
    
    # Authentication (null = read from environment)
    search_api_key: null
    search_api_base_url: null  # For self-hosted SearXNG
    
    # Browser automation
    browser_engine: "playwright"  # or "selenium", "none"
    headless: true
    user_agent: "Mozilla/5.0 (multi-agent-brain/1.0)"
    viewport_width: 1280
    viewport_height: 720
    
    # Timeouts (seconds)
    search_timeout: 10
    navigation_timeout: 30
    extraction_timeout: 15
    
    # Retry configuration
    max_retries: 3
    retry_delay: 2.0
    rate_limit_delay: 1.0
    
    # Content extraction
    max_content_length: 100000
    extract_images: false
    extract_links: true
    
    # Caching
    cache_enabled: false
    cache_ttl: 3600
    
    # Memory persistence
    persist_results: false
```

### Minimal Configuration

```yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "duckduckgo"  # No API key required
```

### Production Configuration

```yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "tavily"
    fallback_provider: "duckduckgo"
    search_timeout: 15
    navigation_timeout: 45
    max_retries: 5
    cache_enabled: true
    cache_ttl: 7200
```

---

## Search Provider Setup

### Tavily (Recommended)

**Acquisition**:
1. Visit https://tavily.com
2. Sign up for free account
3. Copy API key from dashboard

**Free Tier**: 1000 requests/month

**Environment Setup**:
```bash
export BROWSER_SEARCH_API_KEY="tvly-xxxxxxxxxxxxxx"
export BROWSER_SEARCH_PROVIDER="tavily"
```

**YAML Setup**:
```yaml
api_config:
  browser_tool:
    search_provider: "tavily"
    # API key via BROWSER_SEARCH_API_KEY env var
```

**Validation**:
```bash
python -c "from tools.browser_tool import BrowserTool; import asyncio; t=BrowserTool(); print(asyncio.run(t.search('test')))"
```

---

### DuckDuckGo (Zero-Config)

**Acquisition**: No API key required

**Environment Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="duckduckgo"
```

**YAML Setup**:
```yaml
api_config:
  browser_tool:
    search_provider: "duckduckgo"
    # No API key needed
```

**Validation**:
```bash
python -c "from tools.browser_tool import BrowserTool; import asyncio; t=BrowserTool(); print(asyncio.run(t.search('test')))"
```

**Rate Limiting**:
- Use `rate_limit_delay` to avoid soft blocks
- Recommended: `BROWSER_RATE_LIMIT_DELAY=2.0`

---

### Bing Search API

**Prerequisites**:
- Azure subscription
- Bing Search v7 API resource

**Acquisition**:
1. Login to Azure Portal
2. Create Bing Search v7 resource
3. Copy API key from Keys and Endpoint section

**Pricing**: Pay-as-you-go (starts at $3/1000 transactions)

**Environment Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="bing"
export BROWSER_SEARCH_API_KEY="your-azure-bing-key"
export BROWSER_SEARCH_BASE_URL="https://api.bing.microsoft.com/v7.0/search"
```

**YAML Setup**:
```yaml
api_config:
  browser_tool:
    search_provider: "bing"
    search_api_base_url: "https://api.bing.microsoft.com/v7.0/search"
```

---

### Google Custom Search

**Prerequisites**:
- Google Cloud project
- Custom Search JSON API enabled
- Programmable Search Engine created

**Acquisition**:
1. Visit https://console.cloud.google.com
2. Enable Custom Search JSON API
3. Create API key
4. Visit https://programmablesearchengine.google.com
5. Create search engine and copy ID

**Free Tier**: 100 queries/day

**Environment Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="google"
export BROWSER_SEARCH_API_KEY="your-google-api-key"
export GOOGLE_CSE_ID="your-custom-search-engine-id"
```

**YAML Setup**:
```yaml
api_config:
  browser_tool:
    search_provider: "google"
    # Requires GOOGLE_CSE_ID environment variable
```

---

### SearXNG (Self-Hosted)

**Prerequisites**:
- Docker or self-hosted server

**Setup**:
```bash
# Start SearXNG container
docker run -d \
  --name searxng \
  -p 8888:8080 \
  -v "${PWD}/searxng:/etc/searxng" \
  -e "INSTANCE_NAME=multi-agent-brain" \
  searxng/searxng:latest

# Wait for startup
sleep 5

# Test
curl http://localhost:8888/search?q=test&format=json
```

**Environment Setup**:
```bash
export BROWSER_SEARCH_PROVIDER="searxng"
export BROWSER_SEARCH_BASE_URL="http://localhost:8888"
```

**YAML Setup**:
```yaml
api_config:
  browser_tool:
    search_provider: "searxng"
    search_api_base_url: "http://localhost:8888"
```

**Production Notes**:
- Configure upstream search engines in `searxng/settings.yml`
- Use reverse proxy (nginx) with rate limiting
- Enable result caching for better performance

---

## Configuration Validation

### Validation Rules

The browser tool configuration is validated at initialization:

1. **Provider Validation**:
   - Provider must be one of: `tavily`, `duckduckgo`, `bing`, `google`, `searxng`
   - If provider requires API key, `search_api_key` must be set

2. **Timeout Validation**:
   - All timeout values must be positive integers
   - `search_timeout` ≤ `navigation_timeout` (recommended)

3. **Retry Validation**:
   - `max_retries` must be ≥ 0
   - `retry_delay` must be > 0

4. **Content Validation**:
   - `max_content_length` must be > 0
   - Boolean flags (`extract_images`, `extract_links`) must be valid

### Manual Validation

```python
from utils import get_browser_tool_config

# Validate configuration
try:
    config = get_browser_tool_config("coordination")
    print("✓ Configuration valid")
    print(f"  Provider: {config.search_provider}")
    print(f"  Enabled: {config.enabled}")
    print(f"  Has API key: {bool(config.search_api_key)}")
except Exception as e:
    print(f"✗ Configuration invalid: {e}")
```

### Health Check

```python
from tools.browser_tool import BrowserTool

browser = BrowserTool(agent_name="coordination")

# Test search (validates configuration)
result = await browser.search("test query", max_results=1)

if result.error:
    print(f"Configuration issue: {result.error}")
else:
    print(f"✓ Browser tool operational")
```

---

## Agent-Specific Overrides

### Override Syntax

Agent-specific overrides follow the same pattern as other API configs:

```yaml
api_config:
  # Global browser tool config
  browser_tool:
    enabled: true
    search_provider: "tavily"
    search_timeout: 10
  
  # Agent-specific overrides
  agent_overrides:
    coordination:
      browser_tool:
        search_provider: "tavily"
        search_timeout: 15  # More time for complex queries
        persist_results: true
    
    python_expert:
      browser_tool:
        enabled: false  # Disable for this agent
    
    milvus_expert:
      browser_tool:
        search_provider: "google"  # Use different provider
        search_timeout: 20
```

### Override Precedence

Configuration loading follows this priority (highest to lowest):

1. **Agent-specific YAML**: `api_config.agent_overrides.<agent>.browser_tool`
2. **Environment variables**: `BROWSER_*`
3. **Global YAML**: `api_config.browser_tool`
4. **Hard-coded defaults**: `BrowserToolConfig` class defaults

### Example Override Scenarios

**Scenario 1: Different providers per agent**
```yaml
agent_overrides:
  coordination:
    browser_tool:
      search_provider: "tavily"  # Best results for coordination
  
  python_expert:
    browser_tool:
      search_provider: "google"  # Code-focused searches
```

**Scenario 2: Disable for specific agents**
```yaml
agent_overrides:
  devops_expert:
    browser_tool:
      enabled: false  # DevOps agent doesn't need web search
```

**Scenario 3: Extended timeouts for slow queries**
```yaml
agent_overrides:
  coordination:
    browser_tool:
      search_timeout: 30
      navigation_timeout: 60
      max_retries: 5
```

---

## Configuration Examples

### Development (Zero-Config)

```yaml
# config.yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "duckduckgo"
    browser_engine: "none"  # Skip Playwright for faster dev
```

```bash
# .env
BROWSER_TOOL_ENABLED=true
BROWSER_SEARCH_PROVIDER=duckduckgo
BROWSER_ENGINE=none
```

### Production (High Reliability)

```yaml
# config.yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "tavily"
    fallback_provider: "duckduckgo"
    search_timeout: 15
    navigation_timeout: 45
    max_retries: 5
    cache_enabled: true
    cache_ttl: 3600
```

```bash
# .env
BROWSER_SEARCH_API_KEY=tvly-production-key
BROWSER_FALLBACK_PROVIDER=duckduckgo
BROWSER_MAX_RETRIES=5
BROWSER_CACHE_ENABLED=true
```

### Testing (Isolated)

```yaml
# config.yaml (test environment)
api_config:
  browser_tool:
    enabled: false  # Disable by default in tests
```

```python
# tests/conftest.py
@pytest.fixture
def mock_browser_config(monkeypatch):
    from utils.openai_client import BrowserToolConfig
    monkeypatch.setattr(
        "utils.config_manager.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=False)
    )
```

### Multi-Provider Fallback

```yaml
# config.yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "tavily"
    fallback_provider: "duckduckgo"
```

```bash
# .env
BROWSER_SEARCH_API_KEY=tvly-key  # Tavily first
BROWSER_FALLBACK_PROVIDER=duckduckgo  # DuckDuckGo if Tavily fails
```

### Self-Hosted SearXNG

```yaml
# config.yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "searxng"
    search_api_base_url: "http://searxng:8080"
    fallback_provider: "duckduckgo"
```

```bash
# docker-compose.yml
services:
  searxng:
    image: searxng/searxng:latest
    ports:
      - "8888:8080"
    volumes:
      - ./searxng:/etc/searxng
```

---

## Troubleshooting Configuration

### Issue: Browser tool not available

**Check**:
```python
from utils import get_browser_tool_config
config = get_browser_tool_config("coordination")
print(f"Enabled: {config.enabled}")
```

**Fix**:
```bash
export BROWSER_TOOL_ENABLED=true
```

### Issue: API key not recognized

**Check**:
```bash
echo $BROWSER_SEARCH_API_KEY
# Should show your API key
```

**Fix**:
```bash
# Set in environment
export BROWSER_SEARCH_API_KEY="tvly-xxxxx"

# Or in .env file
echo "BROWSER_SEARCH_API_KEY=tvly-xxxxx" >> .env

# Restart network
make run-network
```

### Issue: Agent override not working

**Check configuration loading**:
```python
from utils import get_agent_config
config = get_agent_config("coordination")
print(config.browser_tool.search_provider)
```

**Common cause**: Environment variables override YAML

**Fix**:
```bash
# Unset conflicting environment variables
unset BROWSER_SEARCH_PROVIDER
# Now YAML overrides take effect
```

### Issue: Timeout errors

**Increase timeouts**:
```bash
export BROWSER_SEARCH_TIMEOUT=30
export BROWSER_NAVIGATION_TIMEOUT=60
```

Or in YAML:
```yaml
api_config:
  browser_tool:
    search_timeout: 30
    navigation_timeout: 60
```

---

## Related Documentation

- **User Guide**: [Browser Tool User Guide](../tools/browser_tool.md)
- **Design**: [Browser Tool Design Document](../design/browser_tool.md)
- **Testing**: [Testing Guide](../testing/README.md)
- **Troubleshooting**: [Troubleshooting Guide](../guides/troubleshooting.md)
- **Agent Guide**: [AGENTS.md](../../AGENTS.md#9-tool-integration)
