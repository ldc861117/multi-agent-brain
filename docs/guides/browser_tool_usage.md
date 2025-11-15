# Browser Tool Usage Guide

> **Status**: Placeholder (implementation pending)  
> **Related**: [Browser Tool Design](../design/browser_tool.md) | [Configuration](../configuration/browser_tool.md)

This guide will provide practical examples and patterns for using the browser tool once implemented.

## Planned Sections

1. **Basic Usage**
   - Simple search queries
   - Navigating to URLs
   - Extracting page content
   - Combining search + navigation

2. **Integration with Agents**
   - Using browser tool from CoordinationAgent
   - Delegating web research to specialist agents
   - Synthesizing web content with LLM

3. **Memory Persistence Patterns**
   - When to persist web results
   - Structuring web snapshots in SharedMemory
   - Retrieving cached web content

4. **Advanced Use Cases**
   - Multi-page research workflows
   - Comparing information from multiple sources
   - Monitoring web resources for changes
   - Handling authentication and cookies

5. **Error Handling**
   - Graceful degradation strategies
   - Fallback to alternative providers
   - Retrying failed operations

6. **Performance Optimization**
   - Parallelizing multiple searches
   - Caching strategies
   - Rate limiting best practices

## Temporary Quick Reference

See [AGENTS.md - Section 9.1](../../AGENTS.md#91-browser-tool-web-search--navigation) for basic usage examples.

**Simple Search**:
```python
from tools.browser_tool import BrowserTool

browser = BrowserTool(agent_name="coordination")
result = await browser.search("Python async patterns", max_results=5)

for item in result.search_results:
    print(f"{item.title}: {item.url}")
```

**Search + Visit**:
```python
result = await browser.search_and_visit(
    query="Milvus quickstart",
    max_results=5,
    visit_top_n=2  # Visit top 2 results
)

# Access visited page content
for page in result.visited_pages:
    print(f"Extracted from {page.title}:")
    print(page.text[:500])
```

## Next Steps

This document will be populated during [BROWSER-8] Documentation and examples ticket.
