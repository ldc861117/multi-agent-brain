# Browser Tool Configuration

> **Status**: Placeholder (implementation pending)  
> **Related**: [Browser Tool Design](../design/browser_tool.md)

This document will provide detailed configuration reference for the browser tool once implemented.

## Planned Sections

1. **Environment Variables Reference**
   - `BROWSER_SEARCH_PROVIDER`
   - `BROWSER_SEARCH_API_KEY`
   - `BROWSER_ENGINE`
   - Complete list with defaults and validation rules

2. **YAML Configuration Schema**
   - `api_config.browser_tool` structure
   - Agent-specific overrides
   - Configuration validation

3. **Search Provider Setup Guides**
   - Tavily API key acquisition
   - Google Custom Search setup
   - Bing Search API configuration
   - SearXNG self-hosted deployment
   - DuckDuckGo (no setup required)

4. **Browser Engine Configuration**
   - Playwright installation and setup
   - Browser options (headless, user agent, viewport)
   - Timeout tuning

5. **Troubleshooting**
   - API key validation errors
   - Rate limiting
   - Browser automation failures
   - Memory persistence issues

## Temporary Quick Reference

See [Browser Tool Design - Section 3](../design/browser_tool.md#3-configuration-contract) for the complete configuration contract.

**Minimal Configuration**:
```yaml
# config.yaml
api_config:
  browser_tool:
    enabled: true
    search_provider: "tavily"
    # API key via environment: BROWSER_SEARCH_API_KEY
```

**Environment Variables**:
```bash
# .env
BROWSER_SEARCH_API_KEY="tvly-your-api-key-here"
BROWSER_SEARCH_PROVIDER="tavily"  # or "duckduckgo"
```

## Next Steps

This document will be populated during [BROWSER-4] Configuration integration ticket.
