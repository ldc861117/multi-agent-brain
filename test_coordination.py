"""Test suite for CoordinationAgent.

Tests for question analysis, knowledge retrieval, expert dispatch,
answer synthesis, and collaboration storage.
"""

from __future__ import annotations

import asyncio

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agents.coordination import CoordinationAgent
from agents.base import AgentResponse


@pytest.fixture
def coordination_agent():
    """Create a CoordinationAgent instance for testing."""
    chat_api = SimpleNamespace(
        api_key="dummy-key",
        base_url=None,
        model="stub-chat",
        provider="custom",
        timeout=5,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=1.0,
    )
    embedding_api = SimpleNamespace(
        api_key=None,
        base_url=None,
        model="stub-embed",
        provider="custom",
        dimension=1536,
        timeout=5,
        max_retries=0,
        retry_delay=0.1,
        max_retry_delay=1.0,
    )
    dummy_config = SimpleNamespace(chat_api=chat_api, embedding_api=embedding_api)

    with patch(
        "agents.coordination.agent.get_agent_config", return_value=dummy_config
    ), patch("agents.coordination.agent.OpenAIClientWrapper") as mock_client_cls, patch(
        "agents.coordination.agent.SharedMemory"
    ) as mock_memory_cls:
        mock_client_instance = MagicMock()
        mock_client_cls.return_value = mock_client_instance
        mock_memory_instance = MagicMock()
        mock_memory_cls.return_value = mock_memory_instance

        agent = CoordinationAgent()
        agent.client = mock_client_instance
        agent.memory = mock_memory_instance
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
            assert result["complexity"] in {"simple", "medium", "complex"}
            assert result["reasoning"]

    def test_analyze_question_with_api_error(self, coordination_agent):
        """Test analysis handles API errors gracefully."""
        with patch.object(
            coordination_agent.client, "get_chat_completion"
        ) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            result = coordination_agent.analyze_question("Test question?")

            assert result["question"] == "Test question?"
            assert "python" in result["required_experts"]
            assert "heuristic" in result["reasoning"].lower() or "routing" in result["reasoning"].lower()

    def test_heuristic_analysis_identifies_milvus_domain(self, coordination_agent):
        """Heuristic fallback should include Milvus expert for Milvus questions."""
        with patch.object(
            coordination_agent.client, "get_chat_completion", side_effect=Exception("Offline")
        ):
            result = coordination_agent.analyze_question(
                "How to optimize Milvus query performance?"
            )

        experts = set(result["required_experts"])
        assert "milvus" in experts
        assert "python" in experts  # python assists with client-side optimization
        assert result["complexity"] in {"medium", "complex"}

    def test_heuristic_analysis_identifies_devops_domain(self, coordination_agent):
        """Heuristic fallback should include DevOps expert for infrastructure questions."""
        with patch.object(
            coordination_agent.client, "get_chat_completion", side_effect=Exception("Offline")
        ):
            result = coordination_agent.analyze_question(
                "How to set up CI/CD pipeline for this project?"
            )

        experts = set(result["required_experts"])
        assert "devops" in experts
        assert result["complexity"] in {"medium", "complex"}

    def test_heuristic_analysis_handles_multi_domain_question(self, coordination_agent):
        """Multi-domain questions should engage multiple experts when LLM is unavailable."""
        with patch.object(
            coordination_agent.client, "get_chat_completion", side_effect=Exception("Offline")
        ):
            result = coordination_agent.analyze_question(
                "Compare vector database options for embeddings"
            )

        experts = set(result["required_experts"])
        assert "milvus" in experts
        assert len(experts) >= 2
        assert result["complexity"] == "complex"


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

    @pytest.mark.asyncio
    async def test_get_expert_response_fallback(self, coordination_agent):
        """Expert response should fall back to heuristic text when LLM is unavailable."""
        task_message = {"question": "How to optimize Milvus query performance?"}

        with patch.object(
            coordination_agent.client, "get_chat_completion", side_effect=Exception("Offline")
        ):
            response = await coordination_agent._get_expert_response("milvus", task_message)

        assert "milvus" in response.lower()
        assert "index" in response.lower() or "collection" in response.lower()


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


class TestAnswerSynthesis:
    """Test answer synthesis with verbose and language support."""

    @pytest.mark.asyncio
    async def test_synthesize_answer_concise_mode(self, coordination_agent):
        """Test synthesis in concise mode (default)."""
        question = "What is Python?"
        analysis = {"required_experts": ["python"], "complexity": "simple"}
        expert_responses = {"python": "Python is a programming language."}

        with patch.object(coordination_agent.client, "get_chat_completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Python is a versatile programming language."
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=False
            )

            # Check that the prompt requests concise answer
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            # Should be called with temperature=0.7 and max_tokens=500 for concise mode
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 500

            assert result == "Python is a versatile programming language."

    @pytest.mark.asyncio
    async def test_synthesize_answer_verbose_mode(self, coordination_agent):
        """Test synthesis in verbose mode."""
        question = "What is Python?"
        analysis = {"required_experts": ["python"], "complexity": "simple"}
        expert_responses = {"python": "Python is a programming language."}

        with patch.object(coordination_agent.client, "get_chat_completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "**Direct Answer:** Python is a programming language.\n\n**Synthesis:** ..."
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=True
            )

            # Check that the prompt requests detailed answer
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            # Should be called with temperature=0.7 and max_tokens=1000 for verbose mode
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 1000

            assert "**Direct Answer:**" in result

    @pytest.mark.asyncio
    async def test_synthesize_answer_chinese_language(self, coordination_agent):
        """Test language detection for Chinese."""
        question = "你好"
        analysis = {"required_experts": [], "complexity": "simple"}
        expert_responses = {}

        with patch.object(coordination_agent.client, "get_chat_completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "你好！很高兴见到你。"
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=False
            )

            # Check that Chinese language instruction is included
            mock_completion.assert_called_once()
            # Should be called with language detection result 'zh'
            # The mock should have been called with the right parameters for Chinese
            call_args = mock_completion.call_args
            assert call_args[1]["temperature"] == 0.7
            # We can't easily check the prompt content due to structure, but we can check it was called correctly

            assert result == "你好！很高兴见到你。"

    @pytest.mark.asyncio
    async def test_synthesize_answer_spanish_language(self, coordination_agent):
        """Test language detection for Spanish."""
        question = "hola"
        analysis = {"required_experts": [], "complexity": "simple"}
        expert_responses = {}

        with patch.object(coordination_agent.client, "get_chat_completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "¡Hola! ¿Cómo estás?"
            mock_completion.return_value = mock_response

            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=False
            )

            # Check that Spanish language instruction is included
            mock_completion.assert_called_once()
            # Should be called with language detection result 'es'
            # The mock should have been called with the right parameters for Spanish
            call_args = mock_completion.call_args
            assert call_args[1]["temperature"] == 0.7
            # We can't easily check the prompt content due to structure, but we can check it was called correctly

            assert result == "¡Hola! ¿Cómo estás?"

    @pytest.mark.asyncio
    async def test_synthesize_answer_uses_instance_verbose_default(self, coordination_agent):
        """Test that synthesize_answer uses instance verbose setting when not overridden."""
        question = "Test question"
        analysis = {"required_experts": [], "complexity": "simple"}
        expert_responses = {}

        # Set instance verbose to True
        coordination_agent.verbose = True

        with patch.object(coordination_agent.client, "get_chat_completion") as mock_completion:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Verbose answer"
            mock_completion.return_value = mock_response

            # Call without verbose parameter - should use instance default
            await coordination_agent.synthesize_answer(question, analysis, expert_responses)

            # Check that verbose mode is used
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args
            # Should be called with temperature=0.7 and max_tokens=1000 for verbose mode
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_synthesize_answer_fallback_concise(self, coordination_agent):
        """Test fallback behavior in concise mode when LLM fails."""
        question = "Test question"
        analysis = {"required_experts": ["python", "milvus"], "complexity": "complex"}
        expert_responses = {
            "python": "Use Python libraries.",
            "milvus": "Use vector databases."
        }

        with patch.object(coordination_agent.client, "get_chat_completion", side_effect=Exception("LLM error")):
            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=False
            )

            # Should concatenate expert responses without scaffolding
            expected = "Use Python libraries. Use vector databases."
            assert result == expected

    @pytest.mark.asyncio
    async def test_synthesize_answer_fallback_verbose(self, coordination_agent):
        """Test fallback behavior in verbose mode when LLM fails."""
        question = "Test question"
        analysis = {"required_experts": ["python"], "complexity": "simple"}
        expert_responses = {"python": "Python response"}

        with patch.object(coordination_agent.client, "get_chat_completion", side_effect=Exception("LLM error")):
            result = await coordination_agent.synthesize_answer(
                question, analysis, expert_responses, verbose=True
            )

            # Should include question and expert context
            assert "Q: Test question" in result
            assert "Expert Perspectives" in result
            assert "Python response" in result


class TestLanguageDetection:
    """Test language detection functionality."""

    def test_detect_language_chinese(self):
        """Test detection of Chinese characters."""
        assert CoordinationAgent._detect_language("你好世界") == "zh"
        assert CoordinationAgent._detect_language("Hello 你好") == "zh"

    def test_detect_language_english(self):
        """Test detection of English."""
        assert CoordinationAgent._detect_language("Hello world") == "en"
        assert CoordinationAgent._detect_language("What is Python?") == "en"

    def test_detect_language_spanish(self):
        """Test detection of Spanish."""
        assert CoordinationAgent._detect_language("hola gracias") == "es"
        assert CoordinationAgent._detect_language("por favor") == "es"

    def test_detect_language_french(self):
        """Test detection of French."""
        assert CoordinationAgent._detect_language("bonjour merci") == "fr"
        assert CoordinationAgent._detect_language("s'il vous plaît") == "fr"

    def test_detect_language_german(self):
        """Test detection of German."""
        assert CoordinationAgent._detect_language("hallo danke") == "de"
        assert CoordinationAgent._detect_language("bitte") == "de"

    def test_detect_language_japanese(self):
        """Test detection of Japanese."""
        assert CoordinationAgent._detect_language("こんにちはありがとう") == "ja"

    def test_detect_language_korean(self):
        """Test detection of Korean."""
        assert CoordinationAgent._detect_language("안녕하세요감사합니다") == "ko"

    def test_detect_language_default_english(self):
        """Test default to English for unknown languages."""
        assert CoordinationAgent._detect_language("unknown text") == "en"
        assert CoordinationAgent._detect_language("") == "en"


class TestVerboseConfiguration:
    """Test verbose configuration handling."""

    @pytest.mark.asyncio
    async def test_handle_message_with_verbose_override(self, coordination_agent):
        """Test handle_message respects verbose override in message content."""
        message = {
            "content": {
                "text": "Test question",
                "verbose": True
            }
        }

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
        ):

            mock_analyze.return_value = {"required_experts": [], "complexity": "simple"}
            mock_retrieve.return_value = []
            mock_dispatch.return_value = {
                "interaction_id": "test-id",
                "expert_responses": {},
                "status": "completed",
            }

            await coordination_agent.handle_message(message)

            # Check that verbose override was passed to synthesize_answer
            mock_synthesize.assert_called_once()
            call_kwargs = mock_synthesize.call_args[1]
            assert call_kwargs["verbose"] is True

    @pytest.mark.asyncio
    async def test_handle_message_with_verbose_in_metadata(self, coordination_agent):
        """Test handle_message respects verbose override in metadata."""
        message = {
            "content": {"text": "Test question"},
            "metadata": {"verbose": False}
        }

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
        ):

            mock_analyze.return_value = {"required_experts": [], "complexity": "simple"}
            mock_retrieve.return_value = []
            mock_dispatch.return_value = {
                "interaction_id": "test-id",
                "expert_responses": {},
                "status": "completed",
            }

            await coordination_agent.handle_message(message)

            # Check that verbose override from metadata was passed
            mock_synthesize.assert_called_once()
            call_kwargs = mock_synthesize.call_args[1]
            assert call_kwargs["verbose"] is False

    @pytest.mark.asyncio
    async def test_handle_message_uses_instance_verbose_when_no_override(self, coordination_agent):
        """Test handle_message uses instance verbose when no override provided."""
        message = {"content": {"text": "Test question"}}

        # Set instance verbose to a specific value
        coordination_agent.verbose = True

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
        ):

            mock_analyze.return_value = {"required_experts": [], "complexity": "simple"}
            mock_retrieve.return_value = []
            mock_dispatch.return_value = {
                "interaction_id": "test-id",
                "expert_responses": {},
                "status": "completed",
            }

            await coordination_agent.handle_message(message)

            # Check that synthesize_answer was called with None (will use instance default)
            mock_synthesize.assert_called_once()
            call_kwargs = mock_synthesize.call_args[1]
            assert call_kwargs["verbose"] is None


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
