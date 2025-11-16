#!/usr/bin/env python3
"""Browser Tool Demo - Example usage patterns.

This script will demonstrate browser tool capabilities once implemented.

Planned demos:
1. Simple web search with Tavily
2. Fallback to DuckDuckGo when API key is missing
3. Search + navigate to top results
4. Content extraction from web pages
5. Synthesis with LLM (using OpenAIClientWrapper)
6. Optional memory persistence

Usage:
    # With Tavily API key configured
    export BROWSER_SEARCH_API_KEY="tvly-your-key-here"
    python examples/browser_tool_demo.py

    # Without API key (uses DuckDuckGo fallback)
    python examples/browser_tool_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def demo_simple_search():
    """Demo 1: Simple web search."""
    print("\n=== Demo 1: Simple Web Search ===")
    
    from tools.browser_tool import BrowserTool
    
    browser = BrowserTool(agent_name="demo")
    result = await browser.search("Milvus vector database", max_results=5)
    
    print(f"Query: {result.query}")
    print(f"Provider: {browser.config.search_provider}")
    print(f"\nTop {len(result.search_results)} results:")
    
    for i, item in enumerate(result.search_results, 1):
        print(f"{i}. {item.title}")
        print(f"   {item.url}")
        print(f"   {item.snippet[:100]}...")
        if item.score:
            print(f"   Score: {item.score:.2f}")
        print()


async def demo_search_and_visit():
    """Demo 2: Search and visit top results."""
    print("\n=== Demo 2: Search + Visit Top Results ===")
    
    from tools.browser_tool import BrowserTool
    
    browser = BrowserTool(agent_name="demo")
    result = await browser.search_and_visit(
        query="Python async best practices",
        max_results=5,
        visit_top_n=2
    )
    
    print(f"Visited {len(result.visited_pages)} pages:")
    for page in result.visited_pages:
        print(f"\n{page.title}")
        print(f"URL: {page.url}")
        print(f"Content preview: {page.text[:200]}...")
        print(f"Links found: {len(page.links)}")


async def demo_fallback_provider():
    """Demo 3: Fallback to DuckDuckGo when primary fails."""
    print("\n=== Demo 3: Provider Fallback ===")
    
    from tools.browser_tool import BrowserTool
    
    # Temporarily unset API key to trigger fallback
    original_key = os.environ.get("BROWSER_SEARCH_API_KEY")
    if original_key:
        del os.environ["BROWSER_SEARCH_API_KEY"]
    
    try:
        browser = BrowserTool(agent_name="demo")
        print(f"Primary provider: {browser.config.search_provider}")
        print(f"Fallback provider: {browser.config.fallback_provider}")
    
        result = await browser.search("OpenAgents framework", max_results=3)
        print(f"\nUsed provider: {result.metadata.get('provider', 'unknown')}")
        print(f"Results: {len(result.search_results)}")
    finally:
        if original_key:
            os.environ["BROWSER_SEARCH_API_KEY"] = original_key


async def demo_llm_synthesis():
    """Demo 4: Synthesize web content with LLM."""
    print("\n=== Demo 4: LLM Synthesis ===")
    
    from tools.browser_tool import BrowserTool
    from utils import get_agent_config
    from utils.openai_client import OpenAIClientWrapper
    browser = BrowserTool(agent_name="demo")
    result = await browser.search_and_visit(
        query="Milvus vs Weaviate comparison",
        max_results=5,
        visit_top_n=2
    )
    
    # Build context from search results
    context_parts = []
    for page in result.visited_pages:
        context_parts.append(f"Source: {page.title}\n{page.text[:1000]}")
    context = "\n\n".join(context_parts)
    
    # Synthesize with LLM
    config = get_agent_config("demo")
    client = OpenAIClientWrapper(config=config)
    messages = [
        {"role": "system", "content": "You are a helpful assistant that synthesizes web research."},
        {"role": "user", "content": f"Based on this research:\n\n{context}\n\nProvide a concise comparison of Milvus and Weaviate."}
    ]
    
    response = client.get_chat_completion(messages=messages, max_tokens=300)
    print("\nSynthesized answer:")
    print(response.choices[0].message.content)


async def demo_memory_persistence():
    """Demo 5: Persist web results to SharedMemory."""
    print("\n=== Demo 5: Memory Persistence ===")
    
    from tools.browser_tool import BrowserTool
    from agents.shared_memory import SharedMemory
    
    browser = BrowserTool(agent_name="demo")
    result = await browser.search_and_visit(
        query="Milvus installation guide",
        visit_top_n=1
    )
    
    # Persist to memory
    memory = SharedMemory(agent_name="demo")
    for page in result.visited_pages:
        memory.store_knowledge(
            collection="web_snapshots",
            tenant_id="demo_tenant",
            content={
                "url": page.url,
                "title": page.title,
                "text": page.text[:5000],  # Truncate
                "timestamp": page.timestamp
            },
            metadata={
                "source": "browser_tool",
                "query": result.query
            }
        )
        print(f"Persisted: {page.title}")
    
    # Retrieve from memory
    print("\nRetrieving from memory...")
    retrieved = memory.search_knowledge(
        collection="web_snapshots",
        tenant_id="demo_tenant",
        query="Milvus installation",
        top_k=1
    )
    print(f"Found {len(retrieved)} cached results")


async def main():
    """Run all demos."""
    print("Browser Tool Demo Suite")
    print("=" * 50)
    
    # Check for API key
    api_key = os.environ.get("BROWSER_SEARCH_API_KEY")
    if api_key:
        print(f"✓ Tavily API key configured (starts with {api_key[:8]}...)")
    else:
        print("⚠ No API key found - will use DuckDuckGo fallback")
    
    demos = [
        demo_simple_search,
        demo_search_and_visit,
        demo_fallback_provider,
        demo_llm_synthesis,
        demo_memory_persistence,
    ]
    
    for demo in demos:
        try:
            await demo()
        except Exception as e:
            print(f"Demo failed: {e}")
    
    print("\n" + "=" * 50)
    print("Demo suite complete")


if __name__ == "__main__":
    asyncio.run(main())
