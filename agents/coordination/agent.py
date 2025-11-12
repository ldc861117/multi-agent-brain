"""Coordination agent - Multi-agent orchestrator.

This agent serves as the central coordinator and orchestrator for the multi-agent
system. It analyzes incoming tasks, routes them to appropriate expert agents,
manages collaboration, and synthesizes results into cohesive responses.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from loguru import logger

from agents.base import AgentResponse, BaseAgent
from agents.registry import ExpertRegistration, get_expert_registry
from agents.shared_memory import SharedMemory
from agents.types import AgentCapabilities, CapabilityDescriptor, ExpertKind, Layer
from utils import (
    OpenAIClientWrapper,
    correlation_context,
    get_agent_answer_verbose,
    get_agent_config,
    get_correlation_id,
    metrics_registry,
)


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
    role = "orchestrator"
    layer = Layer.COORDINATION
    expert_kind = ExpertKind.COORDINATION
    capabilities = AgentCapabilities(
        primary=(
            CapabilityDescriptor(
                name="task_analysis",
                description="Analyzes incoming requests to determine required expertise.",
                outputs=("analysis",),
                tags=("coordination", "analysis"),
            ),
            CapabilityDescriptor(
                name="expert_dispatch",
                description="Coordinates specialists and aggregates their responses.",
                outputs=("dispatch_plan",),
                tags=("coordination", "routing"),
            ),
        ),
        auxiliary=(
            CapabilityDescriptor(
                name="response_synthesis",
                description="Synthesizes expert contributions into cohesive replies.",
                outputs=("final_answer",),
                tags=("coordination", "synthesis"),
            ),
        ),
    )

    SUPPORTED_EXPERTS = {"python", "milvus", "devops"}
    HEURISTIC_KEYWORDS = {
        "python": [
            "python",
            "async",
            "await",
            "pytest",
            "pip",
            "poetry",
            "django",
            "fastapi",
            "list comprehension",
            "gil",
            "pydantic",
            "microservice",
            "flask",
            "typing",
        ],
        "milvus": [
            "milvus",
            "vector database",
            "embedding",
            "vector search",
            "hnsw",
            "ivf",
            "ann index",
            "collection",
            "partition",
            "zilliz",
            "faiss",
            "pymilvus",
            "vector index",
        ],
        "devops": [
            "ci cd",
            "cicd",
            "pipeline",
            "deploy",
            "deployment",
            "docker",
            "kubernetes",
            "terraform",
            "ansible",
            "infrastructure",
            "monitoring",
            "observability",
            "prometheus",
            "grafana",
            "devops",
            "iac",
            "infrastructure as code",
            "sre",
            "automation",
        ],
    }
    HEURISTIC_MULTI_DOMAIN_HINTS = [
        "compare",
        "comparison",
        "integrate",
        "integration",
        "architecture",
        "end to end",
        "best practice",
        "best practices",
        "workflow",
        "strategy",
        "optimize",
        "optimization",
        "scalability",
        "scale",
    ]

    def __init__(self):
        """Initialize the CoordinationAgent."""
        super().__init__()
        
        # Get agent-specific configuration
        agent_config = get_agent_config(self.name)
        self.client = OpenAIClientWrapper(config=agent_config)
        
        # Get verbose setting from config
        self.verbose = get_agent_answer_verbose(self.name)
        
        self.memory = SharedMemory(agent_name=self.name)
        self.logger = logger.bind(agent="coordination")

        self.registry: Optional[ExpertRegistry]
        try:
            self.registry = get_expert_registry()
        except Exception as exc:  # pragma: no cover - defensive safeguard
            self.logger.warning(
                "Expert registry unavailable; using legacy dispatch heuristics",
                extra={"error": str(exc)},
            )
            self.registry = None

        # Mapping of expert types to channel names
        self.expert_channels = {
            "python": "python_expert",
            "milvus": "milvus_expert",
            "devops": "devops_expert",
        }

        # Cache for active collaboration tasks
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}

        self.logger.info("CoordinationAgent initialized", extra={"verbose": self.verbose})

    @staticmethod
    def _normalize_expert_label(label: Any) -> Optional[str]:
        """Normalize expert label to supported identifier."""
        if not isinstance(label, str):
            return None

        normalized = label.strip().lower()
        alias_map = {
            "python_expert": "python",
            "milvus_expert": "milvus",
            "devops_expert": "devops",
        }
        normalized = alias_map.get(normalized, normalized)
        return normalized if normalized in CoordinationAgent.SUPPORTED_EXPERTS else None

    @staticmethod
    def _extract_keywords(question: str, limit: int = 5) -> List[str]:
        """Derive a lightweight keyword list from the question."""

        tokens = re.findall(r"[a-zA-Z0-9+#]+", question.lower())
        stop_words = {
            "what",
            "how",
            "best",
            "with",
            "from",
            "that",
            "this",
            "using",
            "your",
            "about",
            "into",
            "which",
            "their",
        }

        keywords: List[str] = []
        for token in tokens:
            if len(token) <= 2:
                continue
            if token in stop_words:
                continue
            if token not in keywords:
                keywords.append(token)
            if len(keywords) >= limit:
                break

        return keywords or tokens[:limit]

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect the language of the input text.
        
        Parameters
        ----------
        text : str
            Input text to analyze
            
        Returns
        -------
        str
            Detected language code ('en', 'zh', 'es', etc.)
        """
        # Simple heuristic language detection
        text = text.strip().lower()
        
        # Chinese characters detection
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'zh'
        
        # Common non-English indicators
        non_english_patterns = {
            'es': [r'\b(hola|gracias|por favor)\b'],
            'fr': [r'\b(bonjour|merci|s\'il vous plaît)\b'],
            'de': [r'\b(hallo|danke|bitte)\b'],
            'ja': [r'(こんにちは|ありがとう|お願いします)'],
            'ko': [r'(안녕하세요|감사합니다|제발)'],
        }
        
        import re
        for lang, patterns in non_english_patterns.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return lang
        
        # Default to English
        return 'en'

    def _determine_complexity(
        self,
        experts: List[str],
        question: str,
        base_complexity: Optional[str] = None,
        heuristic_complexity: Optional[str] = None,
    ) -> str:
        """Determine complexity level using available signals."""
        allowed_values = {"simple", "medium", "complex"}

        if base_complexity in allowed_values:
            complexity = base_complexity
        elif heuristic_complexity in allowed_values:
            complexity = heuristic_complexity
        else:
            normalized = question.lower()
            if len(experts) >= 3:
                complexity = "complex"
            elif len(experts) == 2:
                multi_hints = (
                    "compare",
                    "comparison",
                    "architecture",
                    "integration",
                    "workflow",
                    "design",
                    "optimize",
                    "strategy",
                )
                complexity = (
                    "complex"
                    if any(hint in normalized for hint in multi_hints)
                    else "medium"
                )
            else:
                detail_hints = (
                    "optimize",
                    "best practice",
                    "best practices",
                    "debug",
                    "scale",
                    "scalability",
                    "architecture",
                    "strategy",
                )
                complexity = (
                    "medium"
                    if any(hint in normalized for hint in detail_hints)
                    else "simple"
                )

        return complexity

    def _heuristic_analysis(
        self, question: str, failure_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback heuristic analysis when LLM output is unavailable or unreliable."""
        normalized_question = (
            question.lower()
            .replace("async/await", "async await")
            .replace("ci/cd", "ci cd")
            .replace("dev-ops", "devops")
            .replace("end-to-end", "end to end")
        )

        matched_experts: set[str] = set()
        matched_tokens: set[str] = set()

        for expert, keywords in self.HEURISTIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized_question:
                    matched_experts.add(expert)
                    matched_tokens.add(keyword)

        if "vector database" in normalized_question or "vector db" in normalized_question or "embeddings" in normalized_question:
            matched_experts.add("milvus")
        if "vector search" in normalized_question:
            matched_experts.add("milvus")
        if "multi agent" in normalized_question or "multi-agent" in normalized_question:
            matched_experts.update({"python", "devops"})
        if "workflow" in normalized_question and "pipeline" in normalized_question:
            matched_experts.add("devops")
        if "best practice" in normalized_question and "milvus" in normalized_question:
            matched_experts.add("python")

        if matched_experts and "milvus" in matched_experts:
            if any(hint in normalized_question for hint in self.HEURISTIC_MULTI_DOMAIN_HINTS):
                matched_experts.add("python")
                if any(word in normalized_question for word in ("deploy", "pipeline", "workflow", "infrastructure", "strategy")):
                    matched_experts.add("devops")

        if not matched_experts:
            matched_experts.add("python")

        sorted_experts = sorted(matched_experts)
        complexity = self._determine_complexity(sorted_experts, question)
        keywords = self._extract_keywords(question)

        reasoning_bits: List[str] = []
        if failure_reason:
            reasoning_bits.append(f"Heuristic routing used because {failure_reason}.")
        if matched_tokens:
            reasoning_bits.append(
                "Matched keywords: " + ", ".join(sorted(matched_tokens))
            )
        else:
            reasoning_bits.append("Defaulted to core expert set based on domain heuristics.")

        return {
            "question": question,
            "required_experts": sorted_experts,
            "complexity": complexity,
            "keywords": keywords,
            "reasoning": " ".join(reasoning_bits),
        }

    def _merge_analysis(self, question: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combine LLM analysis with heuristic safeguards."""
        heuristics = self._heuristic_analysis(question)

        raw_experts = analysis.get("required_experts") or []
        normalized_experts = [
            expert
            for expert in (
                self._normalize_expert_label(item) for item in raw_experts
            )
            if expert is not None
        ]

        merged_experts = sorted(set(normalized_experts) | set(heuristics["required_experts"]))
        if not merged_experts:
            return heuristics

        complexity = self._determine_complexity(
            merged_experts,
            question,
            base_complexity=analysis.get("complexity"),
            heuristic_complexity=heuristics.get("complexity"),
        )

        keywords = analysis.get("keywords") or heuristics.get("keywords")

        reasoning_segments: List[str] = []
        if analysis.get("reasoning"):
            reasoning_segments.append(str(analysis["reasoning"]))

        additional_experts = set(merged_experts) - set(normalized_experts)
        if additional_experts:
            reasoning_segments.append(
                "Heuristic routing added: " + ", ".join(sorted(additional_experts))
            )

        if not reasoning_segments:
            reasoning_segments.append("LLM analysis completed")

        return {
            "question": question,
            "required_experts": merged_experts,
            "complexity": complexity,
            "keywords": keywords,
            "reasoning": " | ".join(reasoning_segments),
        }

    def _generate_fallback_response(self, expert: str, question: str) -> str:
        """Generate a deterministic expert response when the LLM is unavailable."""
        question = question.strip()
        templates = {
            "python": (
                f"For '{question}', focus on Python best practices:\n"
                "• Use appropriate language features and libraries\n"
                "• Follow clean code principles\n"
                "• Include error handling and testing considerations"
            ),
            "milvus": (
                f"For '{question}', consider these Milvus aspects:\n"
                "• Design collections and partitions for your use case\n"
                "• Choose the right index type and parameters\n"
                "• Implement monitoring and backup strategies"
            ),
            "devops": (
                f"For '{question}', key DevOps considerations:\n"
                "• Automate deployment and infrastructure management\n"
                "• Implement monitoring and observability\n"
                "• Focus on security, scalability, and reliability"
            ),
        }

        return templates.get(
            expert,
            (
                f"Provide pragmatic guidance for '{question}' from the {expert} domain, "
                "covering immediate steps and longer-term considerations."
            ),
        )

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

            if not isinstance(analysis, dict):
                raise ValueError("LLM analysis did not return a JSON object")

            merged_analysis = self._merge_analysis(question, analysis)

            self.logger.info(
                "Question analyzed",
                extra={
                    "required_experts": merged_analysis.get("required_experts"),
                    "complexity": merged_analysis.get("complexity"),
                },
            )

            return merged_analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze question: {e}")
            return self._heuristic_analysis(question, failure_reason=str(e))

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

            metrics_registry.record_retrieval_hits(self.name, len(all_results))

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
        correlation_id = get_correlation_id()
        interaction_id = str(uuid.uuid4())
        self.logger.info(
            "Starting expert dispatch",
            extra={
                "interaction_id": interaction_id,
                "experts": analysis.get("required_experts"),
            },
        )

        requested_experts = list(dict.fromkeys(analysis.get("required_experts", [])))
        analysis["required_experts"] = requested_experts

        registry_entries: Dict[str, ExpertRegistration] = {}
        skipped_registry_experts: List[str] = []

        if self.registry is not None:
            filtered_experts: List[str] = []
            for label in requested_experts:
                entry = self.registry.get(label)
                if entry is None:
                    filtered_experts.append(label)
                    continue
                if not entry.enabled:
                    skipped_registry_experts.append(entry.name)
                    self.logger.info(
                        "Expert disabled in registry; skipping dispatch",
                        extra={"requested_label": label, "registry_name": entry.name},
                    )
                    continue
                registry_entries[label] = entry
                filtered_experts.append(label)
            if filtered_experts != requested_experts:
                analysis["required_experts"] = filtered_experts
                requested_experts = filtered_experts
        
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
            "correlation_id": correlation_id,
        }

        # Record collaboration state
        registry_snapshot: Dict[str, Dict[str, Any]] = {}
        if registry_entries:
            registry_snapshot = {
                label: entry.to_dict() for label, entry in registry_entries.items()
            }

        self.active_collaborations[interaction_id] = {
            "status": "in_progress",
            "experts": analysis.get("required_experts", []),
            "responses": {},
            "started_at": time.time(),
            "correlation_id": correlation_id,
        }
        if registry_snapshot:
            self.active_collaborations[interaction_id]["registry_entries"] = registry_snapshot
        if skipped_registry_experts:
            self.active_collaborations[interaction_id]["skipped_registry_experts"] = list(
                skipped_registry_experts
            )

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
            "correlation_id": correlation_id,
            "registry_entries": registry_snapshot,
            "skipped_registry_experts": list(skipped_registry_experts),
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
                "You are a Python programming expert. Provide direct, practical answers "
                "about Python development, best practices, and code solutions. "
                "Avoid meta-commentary about being an expert. Focus on actionable guidance."
            ),
            "milvus": (
                "You are a Milvus vector database expert. Give direct answers about "
                "vector databases, Milvus operations, and best practices. "
                "Focus on performance and practical implementation without scaffolding."
            ),
            "devops": (
                "You are a DevOps and infrastructure expert. Provide direct recommendations "
                "about deployment, scalability, monitoring, and operational excellence. "
                "Be practical and avoid process explanations."
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
            return self._generate_fallback_response(expert, question)

    async def synthesize_answer(
        self,
        question: str,
        analysis: Dict[str, Any],
        expert_responses: Dict[str, str],
        tenant_id: str = "default",
        verbose: Optional[bool] = None,
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
        verbose : bool, optional
            Whether to include detailed meta-sections. If None, uses self.verbose setting.

        Returns
        -------
        str
            Synthesized final answer.
        """
        # Use provided verbose setting or fall back to instance default
        is_verbose = verbose if verbose is not None else self.verbose
        
        # Detect user's language for response
        user_language = self._detect_language(question)
        
        # Build expert context
        expert_context = ""
        for expert, response in expert_responses.items():
            expert_context += f"\n【{expert.upper()} Expert Opinion】\n{response}\n"

        # Create language-specific prompts
        language_instructions = {
            'zh': "请用中文回答，保持简洁明了。",
            'es': "Responde en español de manera clara y concisa.",
            'fr': "Réponds en français de manière claire et concise.",
            'de': "Antworte auf Deutsch klar und prägnant.",
            'ja': "日本語で明確かつ簡潔に答えてください。",
            'ko': "한국어로 명확하고 간결하게 답변해주세요.",
            'en': "Respond in clear, concise English."
        }
        
        language_instruction = language_instructions.get(user_language, language_instructions['en'])

        if is_verbose:
            # Verbose mode with meta-sections
            synthesis_prompt = f"""
Based on the following expert opinions, synthesize a comprehensive answer:

【User Question】
{question}

【Analysis】
Complexity: {analysis.get('complexity')}
Required Experts: {', '.join(analysis.get('required_experts', []))}

【Expert Opinions】
{expert_context}

Language instruction: {language_instruction}

Please provide:
1. **Direct Answer**: A clear, concise final answer addressing the user's question
2. **Synthesis of Expert Perspectives**: Brief summary of how different expert views complement each other
3. **Key Recommendations**: Actionable next steps or best practices
4. **Important Considerations**: Trade-offs, risks, or additional factors to consider

Format with clear headings for each section.
"""
        else:
            # Concise mode - only the direct answer
            synthesis_prompt = f"""
Based on the following expert opinions, provide a direct answer to the user's question:

【User Question】
{question}

【Expert Opinions】
{expert_context}

Language instruction: {language_instruction}

Requirements:
- Provide ONLY the direct answer to the user's question
- Do not include headings, meta-commentary, or explanations of your process
- Be conversational and natural
- Keep it concise but complete
- Respond in the same language as the user's question

Direct Answer:
"""

        try:
            response = self.client.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert synthesizer. "
                            "Combine multiple expert perspectives into clear, actionable answers. "
                            "Always match the user's language and requested verbosity level."
                        ),
                    },
                    {"role": "user", "content": synthesis_prompt},
                ],
                temperature=0.7,
                max_tokens=1000 if is_verbose else 500,
            )

            usage = getattr(response, "usage", None)
            total_tokens = getattr(usage, "total_tokens", None) if usage else None
            if total_tokens is not None:
                try:
                    metrics_registry.record_synthesis_tokens(self.name, int(total_tokens))
                except (TypeError, ValueError):
                    self.logger.debug(
                        "Skipping token metric due to non-integer usage",
                        extra={"token_value": total_tokens},
                    )

            final_answer = response.choices[0].message.content

            self.logger.info(
                "Answer synthesized",
                extra={
                    "answer_length": len(final_answer),
                    "verbose": is_verbose,
                    "language": user_language,
                },
            )

            return final_answer.strip()

        except Exception as e:
            self.logger.error(f"Failed to synthesize answer: {e}")
            # Fallback: concatenate expert responses without scaffolding
            if is_verbose:
                fallback = f"Q: {question}\n\nExpert Perspectives:{expert_context}"
            else:
                # Simple fallback for concise mode
                fallback = " ".join([response.strip() for response in expert_responses.values()])
            return fallback.strip()

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
            correlation_id = get_correlation_id()

            # Store as collaboration history
            collaboration_metadata = {
                "complexity": analysis.get("complexity"),
                "final_answer": final_answer,
                "expert_responses": list(expert_responses.keys()),
                "timestamp": datetime.utcnow().isoformat(),
            }
            if correlation_id:
                collaboration_metadata["correlation_id"] = correlation_id

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
                metadata=collaboration_metadata,
            )

            # Store as problem-solution if we have a good answer
            if final_answer and len(final_answer) > 50:
                solution_metadata = {
                    "interaction_id": interaction_id,
                    "experts": analysis.get("required_experts"),
                    "complexity": analysis.get("complexity"),
                }
                if correlation_id:
                    solution_metadata["correlation_id"] = correlation_id

                self.memory.store_knowledge(
                    collection="problem_solutions",
                    tenant_id=tenant_id,
                    content={
                        "problem": question,
                        "solution": final_answer,
                    },
                    metadata=solution_metadata,
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
        request_start = time.perf_counter()

        message_content = self._extract_message_content(message)
        question = message_content.get("text", "")
        tenant_id = message_content.get("tenant_id", "default")

        incoming_metadata: Dict[str, Any] = {}
        if isinstance(message, Mapping):
            raw_metadata = message.get("metadata", {})
            if isinstance(raw_metadata, Mapping):
                incoming_metadata = dict(raw_metadata)

        candidate_ids: List[Any] = [
            message_content.get("correlation_id"),
            incoming_metadata.get("correlation_id"),
        ]
        if isinstance(message, Mapping):
            candidate_ids.extend(
                [
                    message.get("correlation_id"),
                    message.get("id"),
                ]
            )
        candidate_ids.append(message_content.get("id"))

        correlation_id: Optional[str] = None
        for candidate in candidate_ids:
            if candidate:
                correlation_id = str(candidate)
                break
        if correlation_id is None:
            correlation_id = f"coord-{uuid.uuid4().hex}"

        with correlation_context(correlation_id):
            verbose_override = message_content.get("verbose")
            if verbose_override is None:
                verbose_override = incoming_metadata.get("verbose")

            if not question or not question.strip():
                latency = time.perf_counter() - request_start
                metrics_registry.record_request(self.name, "error", latency)
                return AgentResponse(
                    content="Please provide a question for me to process.",
                    metadata={
                        "channel": self.name,
                        "status": "no_input",
                        "correlation_id": correlation_id,
                    },
                )

            self.logger.info(
                "Processing question",
                extra={
                    "question": question[:100],
                    "tenant_id": tenant_id,
                },
            )

            try:
                analysis = self.analyze_question(question)

                similar_knowledge = await self.retrieve_similar_knowledge(
                    question, tenant_id
                )

                dispatch_result = await self.dispatch_to_experts(
                    question, analysis, similar_knowledge, tenant_id
                )

                if dispatch_result["status"] == "failed":
                    latency = time.perf_counter() - request_start
                    metrics_registry.record_request(self.name, "error", latency)
                    error_msg = (
                        "Unable to get expert responses. Please try again."
                    )
                    self.logger.warning(
                        "Dispatch failed", extra={"status": "no_responses"}
                    )
                    return AgentResponse(
                        content=error_msg,
                        metadata={
                            "channel": self.name,
                            "status": "failed",
                            "interaction_id": dispatch_result.get("interaction_id"),
                            "correlation_id": dispatch_result.get(
                                "correlation_id", correlation_id
                            ),
                        },
                    )

                final_answer = await self.synthesize_answer(
                    question,
                    analysis,
                    dispatch_result["expert_responses"],
                    tenant_id,
                    verbose=verbose_override,
                )

                await self.store_collaboration(
                    question,
                    analysis,
                    dispatch_result["expert_responses"],
                    final_answer,
                    dispatch_result["interaction_id"],
                    tenant_id,
                )

                latency = time.perf_counter() - request_start
                metrics_registry.record_request(self.name, "success", latency)

                return AgentResponse(
                    content=final_answer,
                    metadata={
                        "channel": self.name,
                        "interaction_id": dispatch_result["interaction_id"],
                        "complexity": analysis.get("complexity"),
                        "experts_involved": analysis.get("required_experts"),
                        "knowledge_used": len(similar_knowledge) > 0,
                        "correlation_id": dispatch_result.get("correlation_id", correlation_id),
                    },
                )

            except Exception as e:
                self.logger.exception(f"Error processing message: {e}")
                latency = time.perf_counter() - request_start
                metrics_registry.record_request(self.name, "error", latency)
                return AgentResponse(
                    content=f"An error occurred while processing your question. {str(e)[:100]}",
                    metadata={
                        "channel": self.name,
                        "status": "error",
                        "correlation_id": correlation_id,
                    },
                )

    @staticmethod
    def _extract_message_content(message: Mapping[str, Any] | Any) -> Dict[str, Any]:
        """Extract content from various message formats."""
        if isinstance(message, Mapping):
            tenant_id = message.get("tenant_id", "default")
            message_id = message.get("id") or message.get("message_id")
            message_correlation = message.get("correlation_id")
            message_verbose = message.get("verbose")

            for key in ("content", "text", "message", "query", "question"):
                if key in message and message[key]:
                    text_value = message[key]
                    nested_correlation = None
                    nested_verbose = None

                    if isinstance(text_value, Mapping):
                        nested_correlation = text_value.get("correlation_id")
                        nested_verbose = text_value.get("verbose")
                        if "text" in text_value and text_value["text"]:
                            text_value = text_value["text"]

                    result: Dict[str, Any] = {
                        "text": str(text_value),
                        "tenant_id": tenant_id,
                    }
                    if message_id is not None:
                        result["id"] = message_id
                    if message_verbose is not None:
                        result["verbose"] = message_verbose
                    elif nested_verbose is not None:
                        result["verbose"] = nested_verbose
                    if message_correlation is not None:
                        result["correlation_id"] = message_correlation
                    elif nested_correlation is not None:
                        result["correlation_id"] = nested_correlation

                    return result

        return {
            "text": str(message),
            "tenant_id": "default",
        }
