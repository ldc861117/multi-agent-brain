"""Tests for browser tool integration in agents.

This module tests:
1. BaseAgent.tools() returns browser tool descriptor when enabled
2. CoordinationAgent can invoke browser tool and integrate results
3. Optional memory persistence works as expected
4. Browser tool configuration is respected
5. Error handling and graceful degradation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

from agents.base import BaseAgent, AgentResponse
from agents.coordination.agent import CoordinationAgent
from agents.types import ToolDescriptor
from tools.browser_tool import BrowserResult, SearchResult, PageContent
from utils.openai_client import BrowserToolConfig


# ==================== FIXTURES ====================

@pytest.fixture
def browser_config_enabled():
    """Browser tool configuration with enabled=True."""
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
    )


@pytest.fixture
def browser_config_disabled():
    """Browser tool configuration with enabled=False."""
    return BrowserToolConfig(
        enabled=False,
        search_provider="tavily",
    )


@pytest.fixture
def mock_browser_result():
    """Mock browser search result."""
    return BrowserResult(
        query="Milvus vector database",
        search_results=[
            SearchResult(
                title="Milvus Documentation",
                url="https://milvus.io/docs",
                snippet="Official Milvus documentation",
                score=0.95
            ),
            SearchResult(
                title="Milvus GitHub",
                url="https://github.com/milvus-io/milvus",
                snippet="Milvus vector database repository",
                score=0.90
            )
        ],
        visited_pages=[],
        answer="Milvus is an open-source vector database.",
        error=None,
        metadata={"provider": "tavily"}
    )


# ==================== TEST BASE AGENT TOOLS ====================

@pytest.mark.asyncio
async def test_base_agent_tools_returns_browser_descriptor_when_enabled(monkeypatch):
    """Test that BaseAgent.tools() returns browser tool descriptor when enabled."""
    # Mock browser config to return enabled=True
    monkeypatch.setattr(
        "agents.base.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    
    class TestAgent(BaseAgent):
        name = "test_agent"
        
        async def handle_message(self, message, conversation_state=None):
            return AgentResponse("ok", {})
    
    agent = TestAgent()
    tools = agent.tools()
    
    assert len(tools) == 1
    assert isinstance(tools[0], ToolDescriptor)
    assert tools[0].name == "browser_tool"
    assert "search" in tools[0].description.lower()
    assert tools[0].returns == "BrowserResult"
    assert "action" in tools[0].parameters
    assert "query" in tools[0].parameters


@pytest.mark.asyncio
async def test_base_agent_tools_returns_empty_when_disabled(monkeypatch):
    """Test that BaseAgent.tools() returns empty sequence when browser tool disabled."""
    # Mock browser config to return enabled=False
    monkeypatch.setattr(
        "agents.base.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=False)
    )
    
    class TestAgent(BaseAgent):
        name = "test_agent"
        
        async def handle_message(self, message, conversation_state=None):
            return AgentResponse("ok", {})
    
    agent = TestAgent()
    tools = agent.tools()
    
    assert len(tools) == 0


@pytest.mark.asyncio
async def test_base_agent_get_browser_tool_lazy_init(monkeypatch):
    """Test that _get_browser_tool lazily initializes the tool."""
    mock_browser_tool_class = Mock()
    mock_browser_tool_instance = Mock()
    mock_browser_tool_class.return_value = mock_browser_tool_instance
    
    with patch("tools.browser_tool.BrowserTool", mock_browser_tool_class):
        class TestAgent(BaseAgent):
            name = "test_agent"
            
            async def handle_message(self, message, conversation_state=None):
                return AgentResponse("ok", {})
        
        agent = TestAgent()
        
        # First call should instantiate
        tool1 = agent._get_browser_tool()
        assert tool1 is mock_browser_tool_instance
        assert mock_browser_tool_class.call_count == 1
        
        # Second call should return cached instance
        tool2 = agent._get_browser_tool()
        assert tool2 is mock_browser_tool_instance
        assert mock_browser_tool_class.call_count == 1  # Still 1


# ==================== TEST COORDINATION AGENT BROWSER INTEGRATION ====================

@pytest.mark.asyncio
async def test_coordination_agent_should_use_browser_tool_heuristics(monkeypatch):
    """Test browser tool heuristics for deciding when to search."""
    # Mock dependencies
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    agent = CoordinationAgent()
    
    # Test: Questions with external indicators should trigger browser
    analysis_simple = {"complexity": "simple", "required_experts": ["python"]}
    
    assert agent._should_use_browser_tool("What is the latest Milvus release?", analysis_simple)
    assert agent._should_use_browser_tool("Show me recent Python best practices", analysis_simple)
    assert agent._should_use_browser_tool("Find official Milvus documentation", analysis_simple)
    
    # Test: Complex questions should NOT trigger browser (experts handle it)
    analysis_complex = {"complexity": "complex", "required_experts": ["python", "milvus"]}
    assert not agent._should_use_browser_tool("What is the latest Milvus release?", analysis_complex)
    
    # Test: Questions without indicators should NOT trigger browser
    assert not agent._should_use_browser_tool("How do I use async in Python?", analysis_simple)


@pytest.mark.asyncio
async def test_coordination_agent_should_use_browser_tool_disabled(monkeypatch):
    """Test that browser tool is not used when disabled."""
    # Mock with disabled config
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=False)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    agent = CoordinationAgent()
    analysis = {"complexity": "simple", "required_experts": ["python"]}
    
    # Should not use browser when disabled
    assert not agent._should_use_browser_tool("What is the latest Milvus release?", analysis)


@pytest.mark.asyncio
async def test_coordination_agent_search_web_success(monkeypatch, mock_browser_result):
    """Test successful web search via browser tool."""
    # Setup mocks
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    # Mock browser tool
    mock_browser_tool = AsyncMock()
    mock_browser_tool.search = AsyncMock(return_value=mock_browser_result)
    
    agent = CoordinationAgent()
    agent._browser_tool = mock_browser_tool
    
    # Execute search
    result = await agent._search_web("Milvus vector database", max_results=5)
    
    assert result is not None
    assert result["query"] == "Milvus vector database"
    assert len(result["search_results"]) == 2
    assert result["search_results"][0]["title"] == "Milvus Documentation"
    assert result["answer"] == "Milvus is an open-source vector database."
    
    mock_browser_tool.search.assert_called_once()


@pytest.mark.asyncio
async def test_coordination_agent_search_web_failure(monkeypatch):
    """Test graceful handling of browser tool failures."""
    # Setup mocks
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    # Mock browser tool that raises exception
    mock_browser_tool = AsyncMock()
    mock_browser_tool.search = AsyncMock(side_effect=Exception("Network error"))
    
    agent = CoordinationAgent()
    agent._browser_tool = mock_browser_tool
    
    # Execute search - should return None and not raise
    result = await agent._search_web("test query")
    
    assert result is None


@pytest.mark.asyncio
async def test_coordination_agent_should_persist_browser_results(monkeypatch):
    """Test logic for deciding whether to persist browser results."""
    # Setup mocks
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    agent = CoordinationAgent()
    agent.browser_config.persist_results = True  # Enable persistence
    
    # Test: Results with visited pages should be persisted
    result_with_pages = {
        "query": "test",
        "search_results": [],
        "visited_pages": [{"url": "http://example.com", "title": "Test", "text": "Content"}],
        "answer": None,
        "error": None
    }
    assert agent._should_persist_browser_results("test question", result_with_pages)
    
    # Test: Results with answer should be persisted
    result_with_answer = {
        "query": "test",
        "search_results": [],
        "visited_pages": [],
        "answer": "Some answer",
        "error": None
    }
    assert agent._should_persist_browser_results("test question", result_with_answer)
    
    # Test: Empty results should NOT be persisted
    empty_result = {
        "query": "test",
        "search_results": [],
        "visited_pages": [],
        "answer": None,
        "error": None
    }
    assert not agent._should_persist_browser_results("test question", empty_result)
    
    # Test: Error results should NOT be persisted
    error_result = {
        "query": "test",
        "search_results": [],
        "visited_pages": [],
        "answer": None,
        "error": "Something went wrong"
    }
    assert not agent._should_persist_browser_results("test question", error_result)


@pytest.mark.asyncio
async def test_coordination_agent_persist_browser_results(monkeypatch):
    """Test persisting browser results to SharedMemory."""
    # Setup mocks
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: Mock()
    )
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: Mock()
    )
    
    mock_memory = Mock()
    mock_memory.store_knowledge = Mock()
    
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: mock_memory
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: Mock()
    )
    
    agent = CoordinationAgent()
    
    browser_result = {
        "query": "Milvus docs",
        "search_results": [],
        "visited_pages": [
            {
                "url": "https://milvus.io/docs",
                "title": "Milvus Documentation",
                "text": "Official documentation content"
            },
            {
                "url": "https://github.com/milvus-io/milvus",
                "title": "Milvus GitHub",
                "text": "GitHub repository"
            }
        ],
        "answer": None,
        "error": None
    }
    
    await agent._persist_browser_results(browser_result, tenant_id="test-tenant")
    
    # Verify store_knowledge was called for each page
    assert mock_memory.store_knowledge.call_count == 2
    
    # Check first call
    first_call = mock_memory.store_knowledge.call_args_list[0]
    assert first_call[1]["collection"] == "web_snapshots"
    assert first_call[1]["tenant_id"] == "test-tenant"
    assert first_call[1]["content"]["url"] == "https://milvus.io/docs"
    assert first_call[1]["content"]["query"] == "Milvus docs"
    assert first_call[1]["metadata"]["source"] == "browser_tool"


@pytest.mark.asyncio
async def test_coordination_agent_handle_message_with_browser_tool(monkeypatch):
    """Test full handle_message flow with browser tool integration."""
    # Setup comprehensive mocks
    mock_config = Mock()
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: mock_config
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_answer_verbose",
        lambda _: False
    )
    
    # Mock OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"required_experts": ["milvus"], "complexity": "simple", "keywords": ["milvus"], "reasoning": "test"}'))]
    mock_response.usage = Mock(total_tokens=100)
    mock_client.get_chat_completion = Mock(return_value=mock_response)
    
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: mock_client
    )
    
    # Mock SharedMemory
    mock_memory = Mock()
    mock_memory.search_knowledge = Mock(return_value=[])
    mock_memory.store_knowledge = Mock()
    mock_memory.health_check = Mock(return_value={"status": "ok"})
    
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: mock_memory
    )
    
    # Mock expert registry
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: None  # Use legacy dispatch
    )
    
    # Create agent
    agent = CoordinationAgent()
    
    # Mock _get_expert_response to avoid LLM calls
    async def mock_get_expert_response(expert, task_message):
        return f"Expert {expert} response"
    
    agent._get_expert_response = AsyncMock(side_effect=mock_get_expert_response)
    
    # Mock browser tool
    mock_browser_result = BrowserResult(
        query="latest Milvus release",
        search_results=[
            SearchResult(
                title="Milvus Releases",
                url="https://github.com/milvus-io/milvus/releases",
                snippet="Latest release information",
                score=0.95
            )
        ],
        visited_pages=[],
        answer="Milvus 2.3 is the latest release",
        error=None
    )
    
    mock_browser_tool = AsyncMock()
    mock_browser_tool.search = AsyncMock(return_value=mock_browser_result)
    
    # Inject browser tool
    agent._browser_tool = mock_browser_tool
    
    # Test with question that should trigger browser tool
    message = {
        "text": "What is the latest Milvus release?",
        "tenant_id": "test-tenant"
    }
    
    response = await agent.handle_message(message)
    
    # Verify response
    assert isinstance(response, AgentResponse)
    assert response.content  # Should have content
    
    # Verify metadata includes browser tool info
    assert "browser_tool_used" in response.metadata
    assert response.metadata["browser_tool_used"] is True
    assert response.metadata["web_search_query"] == "latest Milvus release"
    assert response.metadata["web_results_count"] == 1
    
    # Verify browser tool was called
    mock_browser_tool.search.assert_called_once()


@pytest.mark.asyncio
async def test_coordination_agent_handle_message_without_browser_tool(monkeypatch):
    """Test handle_message when browser tool is not triggered."""
    # Setup mocks with browser tool disabled
    mock_config = Mock()
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=False)  # Disabled
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: mock_config
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_answer_verbose",
        lambda _: False
    )
    
    # Mock OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"required_experts": ["python"], "complexity": "simple", "keywords": ["python"], "reasoning": "test"}'))]
    mock_response.usage = Mock(total_tokens=100)
    mock_client.get_chat_completion = Mock(return_value=mock_response)
    
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: mock_client
    )
    
    # Mock SharedMemory
    mock_memory = Mock()
    mock_memory.search_knowledge = Mock(return_value=[])
    mock_memory.store_knowledge = Mock()
    
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: mock_memory
    )
    
    # Mock expert registry
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: None
    )
    
    agent = CoordinationAgent()
    
    # Mock _get_expert_response to avoid LLM calls
    async def mock_get_expert_response(expert, task_message):
        return f"Expert {expert} response"
    
    agent._get_expert_response = AsyncMock(side_effect=mock_get_expert_response)
    
    message = {
        "text": "How do I use async in Python?",
        "tenant_id": "test-tenant"
    }
    
    response = await agent.handle_message(message)
    
    # Verify response
    assert isinstance(response, AgentResponse)
    assert response.content
    
    # Verify browser tool was NOT used
    assert "browser_tool_used" not in response.metadata or not response.metadata.get("browser_tool_used")


# ==================== TEST ERROR HANDLING ====================

@pytest.mark.asyncio
async def test_browser_tool_error_does_not_break_flow(monkeypatch):
    """Test that browser tool errors don't break the coordination flow."""
    # Setup mocks
    mock_config = Mock()
    monkeypatch.setattr(
        "agents.coordination.agent.get_browser_tool_config",
        lambda _: BrowserToolConfig(enabled=True)
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_config",
        lambda _: mock_config
    )
    monkeypatch.setattr(
        "agents.coordination.agent.get_agent_answer_verbose",
        lambda _: False
    )
    
    # Mock OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content='{"required_experts": ["milvus"], "complexity": "simple", "keywords": ["milvus"], "reasoning": "test"}'))]
    mock_response.usage = Mock(total_tokens=100)
    mock_client.get_chat_completion = Mock(return_value=mock_response)
    
    monkeypatch.setattr(
        "agents.coordination.agent.OpenAIClientWrapper",
        lambda **_: mock_client
    )
    
    # Mock SharedMemory
    mock_memory = Mock()
    mock_memory.search_knowledge = Mock(return_value=[])
    mock_memory.store_knowledge = Mock()
    
    monkeypatch.setattr(
        "agents.coordination.agent.SharedMemory",
        lambda **_: mock_memory
    )
    
    # Mock expert registry
    monkeypatch.setattr(
        "agents.coordination.agent.get_expert_registry",
        lambda: None
    )
    
    agent = CoordinationAgent()
    
    # Mock _get_expert_response to avoid LLM calls
    async def mock_get_expert_response(expert, task_message):
        return f"Expert {expert} response"
    
    agent._get_expert_response = AsyncMock(side_effect=mock_get_expert_response)
    
    # Mock browser tool that fails
    mock_browser_tool = AsyncMock()
    mock_browser_tool.search = AsyncMock(side_effect=Exception("Browser error"))
    
    agent._browser_tool = mock_browser_tool
    
    message = {
        "text": "What is the latest Milvus documentation?",
        "tenant_id": "test-tenant"
    }
    
    # Should complete successfully despite browser error
    response = await agent.handle_message(message)
    
    assert isinstance(response, AgentResponse)
    assert response.content  # Should still have content from experts
    
    # Browser tool should not appear in metadata since it failed
    assert "browser_tool_used" not in response.metadata or not response.metadata.get("browser_tool_used")
