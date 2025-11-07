"""Test suite for CoordinationAgent.

Tests for question analysis, knowledge retrieval, expert dispatch,
answer synthesis, and collaboration storage.
"""

from __future__ import annotations

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.coordination import CoordinationAgent
from agents.base import AgentResponse


@pytest.fixture
def coordination_agent():
    """Create a CoordinationAgent instance for testing."""
    with patch("agents.coordination.agent.get_openai_client"), patch(
        "agents.coordination.agent.SharedMemory"
    ):
        agent = CoordinationAgent()
    return agent


class TestCoordinationAgentInitialization:
    """Test CoordinationAgent initialization."""

    def test_agent_name(self, coordination_agent):
        """Test agent name is correctly set."""
        assert coordination_agent.name == "coordination"

    def test_agent_description(self, coordination_agent):
        """Test agent description is set."""
        assert "specialist agents" in coordination_agent.description.lower()

    def test_expert_channels_configured(self, coordination_agent):
        """Test expert channel mapping is properly configured."""
        assert "python" in coordination_agent.expert_channels
        assert "milvus" in coordination_agent.expert_channels
        assert "devops" in coordination_agent.expert_channels

    def test_active_collaborations_initialized(self, coordination_agent):
        """Test active collaborations cache is initialized."""
        assert isinstance(coordination_agent.active_collaborations, dict)
        assert len(coordination_agent.active_collaborations) == 0


class TestQuestionAnalysis:
    """Test question analysis functionality."""

    def test_analyze_simple_question(self, coordination_agent):
        """Test analysis of a simple Python question."""
        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = """{
                "required_experts": ["python"],
                "complexity": "simple",
                "keywords": ["function", "python"],
                "reasoning": "Simple Python question"
            }"""
            mock_completion.return_value = mock_response

            result = coordination_agent.analyze_question(
                "How do I define a function in Python?"
            )

            assert result["question"] == "How do I define a function in Python?"
            assert "python" in result["required_experts"]
            assert result["complexity"] in ["simple", "medium", "complex"]

    def test_analyze_complex_question(self, coordination_agent):
        """Test analysis of a complex multi-domain question."""
        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = """{
                "required_experts": ["python", "milvus", "devops"],
                "complexity": "complex",
                "keywords": ["milvus", "python", "deployment"],
                "reasoning": "Requires multiple experts"
            }"""
            mock_completion.return_value = mock_response

            result = coordination_agent.analyze_question(
                "How do I deploy a Python application using Milvus?"
            )

            assert len(result["required_experts"]) >= 2
            assert result["complexity"] == "complex"

    def test_analyze_question_with_invalid_response(self, coordination_agent):
        """Test analysis handles invalid LLM response gracefully."""
        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Invalid response"
            mock_completion.return_value = mock_response

            result = coordination_agent.analyze_question("Test question?")

            assert result["question"] == "Test question?"
            assert "python" in result["required_experts"]
            assert result["complexity"] == "medium"

    def test_analyze_question_with_api_error(self, coordination_agent):
        """Test analysis handles API errors gracefully."""
        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            result = coordination_agent.analyze_question("Test question?")

            assert result["question"] == "Test question?"
            assert "python" in result["required_experts"]
            assert "default analysis" in result["reasoning"]


class TestKnowledgeRetrieval:
    """Test knowledge retrieval functionality."""

    @pytest.mark.asyncio
    async def test_retrieve_similar_knowledge_success(self, coordination_agent):
        """Test successful knowledge retrieval."""
        mock_result = [
            {
                "id": 1,
                "problem": "How to use Milvus?",
                "solution": "First, install it...",
                "similarity_score": 0.85,
            }
        ]

        with patch.object(
            coordination_agent.memory, "search_knowledge", return_value=mock_result
        ):
            results = await coordination_agent.retrieve_similar_knowledge(
                "How to use Milvus?"
            )

            assert len(results) > 0
            assert results[0]["similarity_score"] > 0.5

    @pytest.mark.asyncio
    async def test_retrieve_similar_knowledge_empty(self, coordination_agent):
        """Test knowledge retrieval when no similar documents exist."""
        with patch.object(
            coordination_agent.memory, "search_knowledge", return_value=[]
        ):
            results = await coordination_agent.retrieve_similar_knowledge(
                "Obscure question about unknown topic"
            )

            assert isinstance(results, list)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_similar_knowledge_handles_errors(self, coordination_agent):
        """Test knowledge retrieval handles search errors gracefully."""
        with patch.object(
            coordination_agent.memory, "search_knowledge", side_effect=Exception(
                "Search error"
            )
        ):
            results = await coordination_agent.retrieve_similar_knowledge("Test query")

            assert isinstance(results, list)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_similar_knowledge_with_tenant_id(self, coordination_agent):
        """Test knowledge retrieval respects tenant isolation."""
        with patch.object(
            coordination_agent.memory, "search_knowledge", return_value=[]
        ) as mock_search:
            await coordination_agent.retrieve_similar_knowledge(
                "Test query", tenant_id="tenant_123"
            )

            # Verify both collection searches used the correct tenant_id
            assert mock_search.call_count >= 1
            for call in mock_search.call_args_list:
                assert call[1]["tenant_id"] == "tenant_123"


class TestExpertDispatch:
    """Test expert dispatch functionality."""

    @pytest.mark.asyncio
    async def test_dispatch_to_single_expert(self, coordination_agent):
        """Test dispatching to a single expert."""
        analysis = {
            "required_experts": ["python"],
            "complexity": "simple",
        }

        with patch.object(
            coordination_agent, "_get_expert_response", new_callable=AsyncMock
        ) as mock_get_response:
            mock_get_response.return_value = "Python expert response"

            result = await coordination_agent.dispatch_to_experts(
                "Python question", analysis, []
            )

            assert result["status"] == "completed"
            assert "python" in result["expert_responses"]
            assert len(result["expert_responses"]) == 1

    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_experts(self, coordination_agent):
        """Test dispatching to multiple experts."""
        analysis = {
            "required_experts": ["python", "milvus", "devops"],
            "complexity": "complex",
        }

        with patch.object(
            coordination_agent, "_get_expert_response", new_callable=AsyncMock
        ) as mock_get_response:
            mock_get_response.return_value = "Expert response"

            result = await coordination_agent.dispatch_to_experts(
                "Complex question", analysis, []
            )

            assert result["status"] == "completed"
            assert len(result["expert_responses"]) == 3

    @pytest.mark.asyncio
    async def test_dispatch_creates_interaction_id(self, coordination_agent):
        """Test dispatch creates unique interaction ID."""
        analysis = {"required_experts": ["python"], "complexity": "simple"}

        with patch.object(
            coordination_agent, "_get_expert_response", new_callable=AsyncMock
        ):
            result1 = await coordination_agent.dispatch_to_experts(
                "Question 1", analysis, []
            )
            result2 = await coordination_agent.dispatch_to_experts(
                "Question 2", analysis, []
            )

            assert result1["interaction_id"] != result2["interaction_id"]

    @pytest.mark.asyncio
    async def test_dispatch_with_timeout(self, coordination_agent):
        """Test dispatch handles expert timeout."""
        analysis = {"required_experts": ["python"], "complexity": "simple"}

        with patch.object(
            coordination_agent, "_get_expert_response", new_callable=AsyncMock
        ) as mock_get_response:
            mock_get_response.side_effect = asyncio.TimeoutError()

            result = await coordination_agent.dispatch_to_experts(
                "Question", analysis, []
            )

            assert result["status"] == "completed"
            assert "timeout" in result["expert_responses"].get("python", "").lower()


class TestAnswerSynthesis:
    """Test answer synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_answer_single_expert(self, coordination_agent):
        """Test synthesizing answer from single expert response."""
        analysis = {"required_experts": ["python"], "complexity": "simple"}
        expert_responses = {"python": "Use list comprehension for efficiency"}

        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = (
                "The recommended approach is to use list comprehension..."
            )
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                "How to write efficient Python?", analysis, expert_responses
            )

            assert len(result) > 0
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_synthesize_answer_multiple_experts(self, coordination_agent):
        """Test synthesizing answer from multiple expert responses."""
        analysis = {
            "required_experts": ["python", "milvus"],
            "complexity": "complex",
        }
        expert_responses = {
            "python": "Use async/await for concurrency",
            "milvus": "Index vectors for better performance",
        }

        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = (
                "Synthesized answer combining both perspectives..."
            )
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                "How to optimize?", analysis, expert_responses
            )

            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_answer_fallback_on_error(self, coordination_agent):
        """Test synthesis fallback when LLM fails."""
        analysis = {"required_experts": ["python"], "complexity": "simple"}
        expert_responses = {"python": "Expert response"}

        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            result = await coordination_agent.synthesize_answer(
                "Question", analysis, expert_responses
            )

            assert len(result) > 0
            assert "Expert Perspectives" in result


class TestCollaborationStorage:
    """Test collaboration storage functionality."""

    @pytest.mark.asyncio
    async def test_store_collaboration_success(self, coordination_agent):
        """Test successful collaboration storage."""
        with patch.object(
            coordination_agent.memory, "store_knowledge"
        ) as mock_store:
            await coordination_agent.store_collaboration(
                question="Test question",
                analysis={
                    "required_experts": ["python"],
                    "complexity": "simple",
                },
                expert_responses={"python": "Response"},
                final_answer="Final answer text that is long enough to be stored",
                interaction_id="test-123",
            )

            assert mock_store.call_count >= 2  # Should store in both collections

    @pytest.mark.asyncio
    async def test_store_collaboration_multiple_experts(self, coordination_agent):
        """Test storing collaboration with multiple experts."""
        with patch.object(
            coordination_agent.memory, "store_knowledge"
        ) as mock_store:
            await coordination_agent.store_collaboration(
                question="Complex question",
                analysis={
                    "required_experts": ["python", "milvus", "devops"],
                    "complexity": "complex",
                },
                expert_responses={
                    "python": "Response 1",
                    "milvus": "Response 2",
                    "devops": "Response 3",
                },
                final_answer="Final answer text that is long enough to be stored",
                interaction_id="test-456",
            )

            # Should store in collaboration_history and problem_solutions
            assert mock_store.call_count >= 2

    @pytest.mark.asyncio
    async def test_store_collaboration_handles_errors(self, coordination_agent):
        """Test storing collaboration handles errors gracefully."""
        with patch.object(
            coordination_agent.memory, "store_knowledge", side_effect=Exception(
                "Storage error"
            )
        ):
            # Should not raise exception
            await coordination_agent.store_collaboration(
                question="Question",
                analysis={"required_experts": ["python"], "complexity": "simple"},
                expert_responses={"python": "Response"},
                final_answer="Final answer text",
                interaction_id="test-789",
            )


class TestHandleMessage:
    """Test main message handling pipeline."""

    @pytest.mark.asyncio
    async def test_handle_message_full_pipeline(self, coordination_agent):
        """Test complete message handling pipeline."""
        message = {"content": {"text": "How to use Python?"}}

        with patch.object(coordination_agent, "analyze_question") as mock_analyze, patch.object(
            coordination_agent,
            "retrieve_similar_knowledge",
            new_callable=AsyncMock,
        ) as mock_retrieve, patch.object(
            coordination_agent,
            "dispatch_to_experts",
            new_callable=AsyncMock,
        ) as mock_dispatch, patch.object(
            coordination_agent,
            "synthesize_answer",
            new_callable=AsyncMock,
        ) as mock_synthesize, patch.object(
            coordination_agent,
            "store_collaboration",
            new_callable=AsyncMock,
        ) as mock_store:

            mock_analyze.return_value = {
                "required_experts": ["python"],
                "complexity": "simple",
            }
            mock_retrieve.return_value = []
            mock_dispatch.return_value = {
                "interaction_id": "test-id",
                "expert_responses": {"python": "Response"},
                "status": "completed",
            }
            mock_synthesize.return_value = "Synthesized answer"

            response = await coordination_agent.handle_message(message)

            assert isinstance(response, AgentResponse)
            assert len(response.content) > 0
            assert response.metadata["channel"] == "coordination"

    @pytest.mark.asyncio
    async def test_handle_message_empty_input(self, coordination_agent):
        """Test handling message with empty input."""
        message = {"content": {"text": ""}}

        response = await coordination_agent.handle_message(message)

        assert response.metadata["status"] == "no_input"

    @pytest.mark.asyncio
    async def test_handle_message_with_tenant_id(self, coordination_agent):
        """Test handling message with custom tenant ID."""
        message = {
            "content": {"text": "Question?"},
            "tenant_id": "custom-tenant",
        }

        with patch.object(coordination_agent, "analyze_question"), patch.object(
            coordination_agent,
            "retrieve_similar_knowledge",
            new_callable=AsyncMock,
        ) as mock_retrieve, patch.object(
            coordination_agent,
            "dispatch_to_experts",
            new_callable=AsyncMock,
        ) as mock_dispatch, patch.object(
            coordination_agent,
            "synthesize_answer",
            new_callable=AsyncMock,
        ), patch.object(
            coordination_agent,
            "store_collaboration",
            new_callable=AsyncMock,
        ):

            mock_retrieve.return_value = []
            mock_dispatch.return_value = {
                "interaction_id": "test-id",
                "expert_responses": {"python": "Response"},
                "status": "completed",
            }

            await coordination_agent.handle_message(message)

            # Verify tenant_id was passed to retrieval
            assert mock_retrieve.call_args[1]["tenant_id"] == "custom-tenant"

    @pytest.mark.asyncio
    async def test_handle_message_error_handling(self, coordination_agent):
        """Test error handling in message processing."""
        message = {"content": {"text": "Question?"}}

        with patch.object(coordination_agent, "analyze_question", side_effect=Exception(
            "Analysis error"
        )):
            response = await coordination_agent.handle_message(message)

            assert response.metadata["status"] == "error"


class TestMessageExtraction:
    """Test message content extraction."""

    def test_extract_content_from_dict(self, coordination_agent):
        """Test extracting content from dictionary message."""
        message = {"content": "Question text"}
        result = CoordinationAgent._extract_message_content(message)

        assert result["text"] == "Question text"
        assert result["tenant_id"] == "default"

    def test_extract_content_from_text_field(self, coordination_agent):
        """Test extracting from text field."""
        message = {"text": "Question text"}
        result = CoordinationAgent._extract_message_content(message)

        assert result["text"] == "Question text"

    def test_extract_content_with_tenant_id(self, coordination_agent):
        """Test extracting content with custom tenant ID."""
        message = {"content": "Question", "tenant_id": "tenant-123"}
        result = CoordinationAgent._extract_message_content(message)

        assert result["tenant_id"] == "tenant-123"

    def test_extract_content_from_string(self, coordination_agent):
        """Test extracting content from plain string."""
        result = CoordinationAgent._extract_message_content("Question text")

        assert result["text"] == "Question text"
        assert result["tenant_id"] == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
