"""Coordination agent - Multi-agent orchestrator.

This agent serves as the central coordinator and orchestrator for the multi-agent
system. It analyzes incoming tasks, routes them to appropriate expert agents,
manages collaboration, and synthesizes results into cohesive responses.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from loguru import logger

from agents.base import AgentResponse, BaseAgent
from agents.shared_memory import SharedMemory
from utils import get_agent_config, get_openai_client, OpenAIClientWrapper


class CoordinationAgent(BaseAgent):
    """Multi-agent orchestrator and coordinator.

    Responsibilities:
    - Analyze user questions to determine complexity and required expertise
    - Retrieve relevant historical knowledge from SharedMemory
    - Coordinate with specialist agents (Python, Milvus, DevOps)
    - Synthesize expert responses into cohesive answers
    - Persist collaboration records for future reference
    """

    name = "coordination"
    description = (
        "Routes work between specialist agents, maintains context, and orchestrates"
        " multi-agent collaboration."
    )

    def __init__(self):
        """Initialize the CoordinationAgent."""
        super().__init__()
        
        # Get agent-specific configuration
        agent_config = get_agent_config(self.name)
        self.client = OpenAIClientWrapper(config=agent_config)
        
        self.memory = SharedMemory(agent_name=self.name)
        self.logger = logger.bind(agent_id="coordination")

        # Mapping of expert types to channel names
        self.expert_channels = {
            "python": "python_expert",
            "milvus": "milvus_expert",
            "devops": "devops_expert",
        }

        # Cache for active collaboration tasks
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}

        self.logger.info("CoordinationAgent initialized")

    def analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze user question to determine required expertise and complexity.

        Parameters
        ----------
        question : str
            The user's question text.

        Returns
        -------
        Dict[str, Any]
            Analysis result containing:
            - required_experts: List of expert types needed
            - complexity: "simple", "medium", or "complex"
            - keywords: List of extracted keywords
            - reasoning: Explanation of the analysis
        """
        analysis_prompt = """
Analyze the user question and determine which experts are needed.

User question: {question}

Please analyze and return JSON with the following structure:
{{
    "required_experts": ["python", "milvus", "devops"],
    "complexity": "simple" | "medium" | "complex",
    "keywords": ["keyword1", "keyword2"],
    "reasoning": "Explanation of why these experts are needed"
}}

Supported expert types:
- python: Python programming and development
- milvus: Milvus vector database
- devops: DevOps, deployment, and infrastructure

Guidelines:
1. Select multiple experts if the question spans multiple domains
2. If uncertain, include "python" (generalist)
3. Complexity: simple=straightforward single-domain, medium=cross-domain or requires analysis, complex=deep analysis or code generation
"""

        try:
            response = self.client.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert problem analyzer. Determine which "
                            "specialists should handle the user's question. Return only valid JSON."
                        ),
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt.format(question=question),
                    },
                ],
                temperature=0.5,
                max_tokens=500,
            )

            analysis_text = response.choices[0].message.content

            # Extract JSON from response
            json_start = analysis_text.find("{")
            json_end = analysis_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(analysis_text[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")

            analysis["question"] = question

            self.logger.info(
                "Question analyzed",
                extra={
                    "required_experts": analysis.get("required_experts"),
                    "complexity": analysis.get("complexity"),
                },
            )

            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze question: {e}")
            # Graceful degradation: default analysis
            return {
                "question": question,
                "required_experts": ["python"],
                "complexity": "medium",
                "keywords": question.split()[:5],
                "reasoning": "Analysis failed, using default analysis",
            }

    async def retrieve_similar_knowledge(
        self, question: str, tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve historically similar questions and solutions.

        Parameters
        ----------
        question : str
            The user's question.
        tenant_id : str, optional
            Tenant ID for multi-tenant isolation, by default "default".

        Returns
        -------
        List[Dict[str, Any]]
            List of similar knowledge sorted by similarity score.
        """
        try:
            # Search in problem-solutions collection
            problem_solutions = self.memory.search_knowledge(
                collection="problem_solutions",
                tenant_id=tenant_id,
                query=question,
                top_k=3,
                threshold=0.6,
            )

            # Search in collaboration history for context
            collab_history = self.memory.search_knowledge(
                collection="collaboration_history",
                tenant_id=tenant_id,
                query=question,
                top_k=2,
                threshold=0.6,
            )

            # Combine and sort by similarity
            all_results = problem_solutions + collab_history
            all_results.sort(
                key=lambda x: x.get("similarity_score", 0), reverse=True
            )

            self.logger.info(
                "Retrieved similar knowledge",
                extra={
                    "problem_solutions_count": len(problem_solutions),
                    "collaboration_history_count": len(collab_history),
                },
            )

            return all_results

        except Exception as e:
            self.logger.error(f"Failed to retrieve knowledge: {e}")
            return []

    async def dispatch_to_experts(
        self,
        question: str,
        analysis: Dict[str, Any],
        similar_knowledge: List[Dict[str, Any]],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Dispatch tasks to expert agents for parallel processing.

        Parameters
        ----------
        question : str
            The user's question.
        analysis : Dict[str, Any]
            Question analysis results.
        similar_knowledge : List[Dict[str, Any]]
            Retrieved similar historical knowledge.
        tenant_id : str, optional
            Tenant ID for multi-tenant isolation, by default "default".

        Returns
        -------
        Dict[str, Any]
            Dispatching results containing:
            - interaction_id: Unique ID for this collaboration
            - expert_responses: Dict mapping expert names to their responses
            - status: "completed", "partial", or "failed"
        """
        interaction_id = str(uuid.uuid4())
        self.logger.info(
            "Starting expert dispatch",
            extra={
                "interaction_id": interaction_id,
                "experts": analysis.get("required_experts"),
            },
        )

        # Build context from similar knowledge
        context = ""
        if similar_knowledge:
            context = "Related historical knowledge:\n"
            for doc in similar_knowledge[:2]:
                if "problem" in doc:
                    context += f"- Q: {doc.get('problem', 'N/A')}\n"
                if "solution" in doc:
                    context += f"  A: {doc.get('solution', 'N/A')[:100]}...\n"

        # Create task message
        task_message = {
            "interaction_id": interaction_id,
            "question": question,
            "analysis": analysis,
            "context": context,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Record collaboration state
        self.active_collaborations[interaction_id] = {
            "status": "in_progress",
            "experts": analysis.get("required_experts", []),
            "responses": {},
            "started_at": time.time(),
        }

        # Dispatch to experts (note: in a real implementation, this would
        # send messages to expert channels through OpenAgents' message system)
        expert_responses = {}
        for expert in analysis.get("required_experts", []):
            try:
                # Simulate expert response with LLM
                response = await self._get_expert_response(
                    expert, task_message
                )
                expert_responses[expert] = response

            except asyncio.TimeoutError:
                self.logger.warning(f"Expert {expert} response timeout")
                expert_responses[expert] = f"[{expert} timeout]"
            except Exception as e:
                self.logger.error(f"Failed to get response from {expert}: {e}")
                expert_responses[expert] = f"[{expert} error: {str(e)[:50]}]"

        self.active_collaborations[interaction_id]["responses"] = expert_responses
        self.active_collaborations[interaction_id]["status"] = (
            "completed" if expert_responses else "failed"
        )

        self.logger.info(
            "Expert dispatch completed",
            extra={
                "interaction_id": interaction_id,
                "responses_count": len(expert_responses),
            },
        )

        return {
            "interaction_id": interaction_id,
            "expert_responses": expert_responses,
            "status": "completed" if expert_responses else "failed",
        }

    async def _get_expert_response(
        self, expert: str, task_message: Dict[str, Any]
    ) -> str:
        """Get response from an expert agent using LLM simulation.

        In a production system with full OpenAgents integration, this would
        dispatch messages through the channel system. For now, we simulate
        expert responses using LLM prompts.

        Parameters
        ----------
        expert : str
            The expert type (python, milvus, devops).
        task_message : Dict[str, Any]
            The task message to send to the expert.

        Returns
        -------
        str
            The expert's response.
        """
        question = task_message.get("question", "")
        context = task_message.get("context", "")

        expert_prompts = {
            "python": (
                "You are a Python programming expert. Answer the following question "
                "about Python development, best practices, and code solutions. "
                "Be concise and practical."
            ),
            "milvus": (
                "You are a Milvus vector database expert. Answer questions about "
                "vector databases, Milvus operations, and best practices. "
                "Focus on performance and practical implementation."
            ),
            "devops": (
                "You are a DevOps and infrastructure expert. Answer questions about "
                "deployment, scalability, monitoring, and operational excellence. "
                "Provide practical recommendations."
            ),
        }

        system_prompt = expert_prompts.get(expert, "You are a helpful expert.")
        user_prompt = f"{context}\n\nQuestion: {question}"

        try:
            response = self.client.get_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Failed to get expert response for {expert}: {e}")
            return f"Unable to get response from {expert} expert"

    async def synthesize_answer(
        self,
        question: str,
        analysis: Dict[str, Any],
        expert_responses: Dict[str, str],
        tenant_id: str = "default",
    ) -> str:
        """Synthesize expert responses into a cohesive final answer.

        Parameters
        ----------
        question : str
            The original user question.
        analysis : Dict[str, Any]
            Question analysis results.
        expert_responses : Dict[str, str]
            Responses from expert agents.
        tenant_id : str, optional
            Tenant ID for multi-tenant isolation, by default "default".

        Returns
        -------
        str
            Synthesized final answer.
        """
        # Build expert context
        expert_context = ""
        for expert, response in expert_responses.items():
            expert_context += f"\n【{expert.upper()} Expert Opinion】\n{response}\n"

        synthesis_prompt = f"""
Based on the following expert opinions, synthesize a comprehensive answer:

【User Question】
{question}

【Analysis】
Complexity: {analysis.get('complexity')}
Required Experts: {', '.join(analysis.get('required_experts', []))}

【Expert Opinions】
{expert_context}

Please provide:
1. A clear, concise final answer addressing the user's question
2. Synthesis of different expert perspectives
3. Key recommendations or action items
4. Any trade-offs or considerations the user should know about

Format the answer in a clear, structured way.
"""

        try:
            response = self.client.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert synthesizer. Combine multiple expert "
                            "perspectives into a clear, actionable answer."
                        ),
                    },
                    {"role": "user", "content": synthesis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            final_answer = response.choices[0].message.content

            self.logger.info(
                "Answer synthesized",
                extra={"answer_length": len(final_answer)},
            )

            return final_answer

        except Exception as e:
            self.logger.error(f"Failed to synthesize answer: {e}")
            # Fallback: concatenate expert responses
            fallback = f"Q: {question}\n\nExpert Perspectives:{expert_context}"
            return fallback

    async def store_collaboration(
        self,
        question: str,
        analysis: Dict[str, Any],
        expert_responses: Dict[str, str],
        final_answer: str,
        interaction_id: str,
        tenant_id: str = "default",
    ) -> None:
        """Store collaboration record to SharedMemory for future reference.

        Parameters
        ----------
        question : str
            The user's question.
        analysis : Dict[str, Any]
            Question analysis results.
        expert_responses : Dict[str, str]
            Responses from expert agents.
        final_answer : str
            The synthesized final answer.
        interaction_id : str
            Unique ID for this collaboration.
        tenant_id : str, optional
            Tenant ID for multi-tenant isolation, by default "default".
        """
        try:
            # Store as collaboration history
            self.memory.store_knowledge(
                collection="collaboration_history",
                tenant_id=tenant_id,
                content={
                    "interaction_id": interaction_id,
                    "initiator_agent": "coordination",
                    "participating_agents": ",".join(
                        analysis.get("required_experts", [])
                    ),
                    "task_description": question,
                },
                metadata={
                    "complexity": analysis.get("complexity"),
                    "final_answer": final_answer,
                    "expert_responses": list(expert_responses.keys()),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Store as problem-solution if we have a good answer
            if final_answer and len(final_answer) > 50:
                self.memory.store_knowledge(
                    collection="problem_solutions",
                    tenant_id=tenant_id,
                    content={
                        "problem": question,
                        "solution": final_answer,
                    },
                    metadata={
                        "interaction_id": interaction_id,
                        "experts": analysis.get("required_experts"),
                        "complexity": analysis.get("complexity"),
                    },
                )

            self.logger.info(
                "Collaboration stored",
                extra={"interaction_id": interaction_id},
            )

        except Exception as e:
            self.logger.error(f"Failed to store collaboration: {e}")

    async def handle_message(
        self,
        message: Mapping[str, Any] | Any,
        conversation_state: Optional[MutableMapping[str, Any]] = None,
    ) -> AgentResponse:
        """Process incoming message through the coordination pipeline.

        Flow:
        1. Extract message content
        2. Analyze question
        3. Retrieve similar historical knowledge
        4. Dispatch to expert agents
        5. Synthesize expert responses
        6. Store collaboration record
        7. Return final answer

        Parameters
        ----------
        message : Mapping[str, Any] | Any
            Incoming message from the OpenAgents network.
        conversation_state : Optional[MutableMapping[str, Any]], optional
            Conversation state for multi-turn interactions, by default None.

        Returns
        -------
        AgentResponse
            Response with synthesized answer and metadata.
        """
        try:
            # Extract message content
            message_content = self._extract_message_content(message)
            question = message_content.get("text", "")
            tenant_id = message_content.get("tenant_id", "default")

            if not question or not question.strip():
                return AgentResponse(
                    content="Please provide a question for me to process.",
                    metadata={"channel": self.name, "status": "no_input"},
                )

            self.logger.info(
                "Processing question",
                extra={
                    "question": question[:100],
                    "tenant_id": tenant_id,
                },
            )

            # Analyze question
            analysis = self.analyze_question(question)

            # Retrieve similar knowledge
            similar_knowledge = await self.retrieve_similar_knowledge(
                question, tenant_id
            )

            # Dispatch to experts
            dispatch_result = await self.dispatch_to_experts(
                question, analysis, similar_knowledge, tenant_id
            )

            if dispatch_result["status"] == "failed":
                error_msg = (
                    "Unable to get expert responses. Please try again."
                )
                self.logger.warning("Dispatch failed", extra={"status": "no_responses"})
                return AgentResponse(
                    content=error_msg,
                    metadata={
                        "channel": self.name,
                        "status": "failed",
                        "interaction_id": dispatch_result.get("interaction_id"),
                    },
                )

            # Synthesize answer
            final_answer = await self.synthesize_answer(
                question,
                analysis,
                dispatch_result["expert_responses"],
                tenant_id,
            )

            # Store collaboration
            await self.store_collaboration(
                question,
                analysis,
                dispatch_result["expert_responses"],
                final_answer,
                dispatch_result["interaction_id"],
                tenant_id,
            )

            # Return response
            self.logger.info(
                "Message processing completed",
                extra={
                    "interaction_id": dispatch_result["interaction_id"],
                    "answer_length": len(final_answer),
                },
            )

            return AgentResponse(
                content=final_answer,
                metadata={
                    "channel": self.name,
                    "interaction_id": dispatch_result["interaction_id"],
                    "complexity": analysis.get("complexity"),
                    "experts_involved": analysis.get("required_experts"),
                    "knowledge_used": len(similar_knowledge) > 0,
                },
            )

        except Exception as e:
            self.logger.exception(f"Error processing message: {e}")
            return AgentResponse(
                content=f"An error occurred while processing your question. {str(e)[:100]}",
                metadata={"channel": self.name, "status": "error"},
            )

    @staticmethod
    def _extract_message_content(message: Mapping[str, Any] | Any) -> Dict[str, Any]:
        """Extract content from various message formats.

        Parameters
        ----------
        message : Mapping[str, Any] | Any
            Message in various possible formats.

        Returns
        -------
        Dict[str, Any]
            Extracted content with "text" and optional "tenant_id".
        """
        if isinstance(message, Mapping):
            # Try common content fields
            for key in ("content", "text", "message", "query", "question"):
                if key in message and message[key]:
                    text = message[key]
                    if isinstance(text, Mapping) and "text" in text:
                        text = text["text"]
                    return {
                        "text": str(text),
                        "tenant_id": message.get("tenant_id", "default"),
                    }
        return {
            "text": str(message),
            "tenant_id": "default",
        }
