# CoordinationAgent Implementation Guide

## Overview

The `CoordinationAgent` is the central orchestrator of the multi-agent system. It serves as the "brain" that analyzes user questions, routes them to appropriate expert agents, coordinates their responses, and synthesizes final answers.

## Architecture

```
User Question
     ↓
[Question Analysis] → Determine required experts & complexity
     ↓
[Knowledge Retrieval] → Search SharedMemory for similar solutions
     ↓
[Expert Dispatch] → Send tasks to Python, Milvus, DevOps experts
     ↓
[Answer Synthesis] → Combine expert perspectives into coherent answer
     ↓
[Collaboration Storage] → Persist results for future reference
     ↓
User Response
```

## Key Components

### 1. Question Analysis (`analyze_question`)

**Purpose**: Determine which experts are needed and assess complexity

**Process**:
- Uses LLM to analyze the question
- Extracts required expert types (python, milvus, devops)
- Classifies complexity (simple, medium, complex)
- Identifies key concepts/keywords

**Input**: Question text (string)
**Output**: Dictionary with `required_experts`, `complexity`, `keywords`, `reasoning`

**Example**:
```python
analysis = agent.analyze_question(
    "How to deploy a Python app with Milvus to production?"
)
# Returns:
# {
#     "required_experts": ["python", "milvus", "devops"],
#     "complexity": "complex",
#     "keywords": ["deployment", "python", "milvus"],
#     "reasoning": "Requires expertise from multiple domains..."
# }
```

### 2. Knowledge Retrieval (`retrieve_similar_knowledge`)

**Purpose**: Leverage historical solutions and collaboration patterns

**Process**:
- Searches `problem_solutions` collection for similar problems
- Searches `collaboration_history` collection for related interactions
- Ranks results by semantic similarity
- Respects tenant isolation

**Input**: Question text, tenant_id (default: "default")
**Output**: List of similar documents sorted by similarity score

**Features**:
- Multi-tenant support via partition keys
- Similarity threshold filtering (0.6 by default)
- Graceful degradation if Milvus unavailable

### 3. Expert Dispatch (`dispatch_to_experts`)

**Purpose**: Simulate sending tasks to expert agents

**Process**:
- Creates unique interaction ID for tracking
- Builds context from historical knowledge
- Calls `_get_expert_response()` for each required expert
- Manages active collaboration state
- Handles timeouts and failures gracefully

**Input**: Question, analysis, similar knowledge, tenant_id
**Output**: Dictionary with `interaction_id`, `expert_responses`, `status`

**Note**: In production with full OpenAgents integration, this would send actual messages through the OpenAgents channel system instead of simulating responses.

### 4. Expert Response Simulation (`_get_expert_response`)

**Purpose**: Generate expert-specific responses using role-based LLM prompts

**Process**:
- Tailors system prompt based on expert type
- Includes historical context from similar knowledge
- Generates specialized response for that expert domain
- Handles API errors with fallback messages

**Expert Types**:
- `python`: Python programming and development
- `milvus`: Vector database operations and optimization
- `devops`: Deployment, scaling, and operational excellence

### 5. Answer Synthesis (`synthesize_answer`)

**Purpose**: Combine multiple expert perspectives into cohesive answer

**Process**:
- Formats all expert responses with clear attribution
- Uses LLM to synthesize a unified answer
- Highlights key recommendations and trade-offs
- Structures output for clarity and actionability

**Input**: Question, analysis, expert responses, tenant_id
**Output**: Synthesized answer (string)

**Fallback**: If synthesis fails, concatenates expert responses

### 6. Collaboration Storage (`store_collaboration`)

**Purpose**: Persist interaction data for future learning

**Process**:
- Stores in `collaboration_history` collection with metadata
- Stores in `problem_solutions` collection if answer is comprehensive
- Includes interaction ID for tracking
- Stores participating experts and complexity level

**Collections Used**:
- `collaboration_history`: Full interaction records with all experts
- `problem_solutions`: Problem-solution pairs for faster retrieval

**Multi-tenancy**: All operations include tenant_id for isolation

## Method Signatures

### Main Entry Point

```python
async def handle_message(
    self,
    message: Mapping[str, Any] | Any,
    conversation_state: Optional[MutableMapping[str, Any]] = None,
) -> AgentResponse
```

Orchestrates the complete coordination pipeline.

### Core Methods

```python
def analyze_question(self, question: str) -> Dict[str, Any]
```
Analyzes question without async (LLM calls handle blocking).

```python
async def retrieve_similar_knowledge(
    self, question: str, tenant_id: str = "default"
) -> List[Dict[str, Any]]
```
Retrieves similar historical knowledge asynchronously.

```python
async def dispatch_to_experts(
    self,
    question: str,
    analysis: Dict[str, Any],
    similar_knowledge: List[Dict[str, Any]],
    tenant_id: str = "default",
) -> Dict[str, Any]
```
Dispatches tasks to expert agents and collects responses.

```python
async def synthesize_answer(
    self,
    question: str,
    analysis: Dict[str, Any],
    expert_responses: Dict[str, str],
    tenant_id: str = "default",
) -> str
```
Synthesizes expert responses into final answer.

```python
async def store_collaboration(
    self,
    question: str,
    analysis: Dict[str, Any],
    expert_responses: Dict[str, str],
    final_answer: str,
    interaction_id: str,
    tenant_id: str = "default",
) -> None
```
Stores collaboration record for future reference.

## Error Handling

The CoordinationAgent implements graceful degradation:

1. **Question Analysis Failure**: Falls back to default analysis (python expert, medium complexity)
2. **Knowledge Retrieval Failure**: Continues without historical context
3. **Expert Dispatch Failure**: Returns partial responses or simulates with LLM
4. **Synthesis Failure**: Concatenates expert responses as fallback
5. **Storage Failure**: Logs error but doesn't interrupt response flow

All exceptions are caught, logged with context, and handled gracefully.

## Multi-Tenancy Support

All operations support multi-tenant isolation:

```python
# Example: tenant-specific question processing
message = {
    "content": {"text": "Question?"},
    "tenant_id": "customer_acme"
}
response = await agent.handle_message(message)
```

Tenant isolation is maintained at:
- SharedMemory level (partition keys)
- Knowledge retrieval (searches only tenant's data)
- Collaboration storage (associates records with tenant)

## Configuration

The agent automatically reads from `.env`:
- `OPENAI_API_KEY`: Required for LLM calls
- `OPENAI_BASE_URL`: Optional custom endpoint
- `OPENAI_MODEL`: Model to use (default: gpt-3.5-turbo)
- `MILVUS_URI`: Milvus connection (default: ./multi_agent_memory.db)
- `EMBEDDING_MODEL`: Embedding model (default: text-embedding-3-small)
- `EMBEDDING_DIMENSION`: Embedding dimension (default: 1536)

## Usage Examples

### Example 1: Simple Question

```python
coordinator = CoordinationAgent()
message = {"content": {"text": "How to use Python?"}}
response = await coordinator.handle_message(message)
print(response.content)
```

### Example 2: Complex Question with Context

```python
message = {
    "content": {
        "text": "How to optimize Milvus for large-scale deployments?"
    },
    "tenant_id": "project_123"
}
response = await coordinator.handle_message(message)
print(f"Experts: {response.metadata['experts_involved']}")
print(f"Complexity: {response.metadata['complexity']}")
```

### Example 3: Analyzing Question Before Processing

```python
question = "How to build a distributed ML system?"
analysis = coordinator.analyze_question(question)
print(f"Required experts: {analysis['required_experts']}")
print(f"Complexity: {analysis['complexity']}")

# Then dispatch if needed
similar = await coordinator.retrieve_similar_knowledge(question)
```

## Testing

Run the test suite:

```bash
pytest test_coordination.py -v
```

Test coverage includes:
- Question analysis (simple, complex, error cases)
- Knowledge retrieval (success, empty, error cases)
- Expert dispatch (single/multiple experts, timeouts)
- Answer synthesis (single/multiple experts, fallback)
- Collaboration storage (success, error handling)
- Message handling (full pipeline, edge cases)
- Message extraction (various formats)

## Integration with OpenAgents

The agent is configured in `config.yaml`:

```yaml
channels:
  coordination:
    description: "Routes work between specialists and maintains context"
    entrypoint: agents.coordination:CoordinationAgent
    visibility: internal
    targets:
      - python_expert
      - milvus_expert
      - devops_expert
```

When messages arrive through the OpenAgents HTTP network:
1. Message is routed to `coordination` channel
2. `handle_message()` is called
3. Response is sent back through the network

## Performance Considerations

1. **Caching**: SharedMemory includes LRU embedding cache (1000 entries by default)
2. **Batch Operations**: Use batch_search/batch_store for multiple items
3. **Similarity Threshold**: Higher threshold reduces irrelevant results
4. **Top-K Limit**: Reduce top_k in retrieve_similar_knowledge for speed

## Future Enhancements

Potential improvements for production deployment:

1. **Actual Channel Messaging**: Replace LLM simulation with real OpenAgents channel messaging
2. **Response Caching**: Cache synthesized responses for identical questions
3. **Expert Timeouts**: Implement configurable per-expert timeouts
4. **Response Streaming**: Stream final answer as it's being synthesized
5. **Feedback Loop**: Collect user feedback to improve routing and synthesis
6. **Metrics Dashboard**: Expose collaboration metrics for monitoring
7. **Parallel Dispatch**: Use asyncio.gather() for true parallel expert queries

## Related Files

- **Implementation**: `agents/coordination/agent.py`
- **Tests**: `test_coordination.py`
- **Examples**: `examples/coordination_agent_example.py`
- **Base Agent**: `agents/base.py`
- **Shared Memory**: `agents/shared_memory.py`
- **OpenAI Client**: `utils/openai_client.py`
- **Configuration**: `config.yaml`

## Troubleshooting

### Issue: "No knowledge retrieved"
- Ensure data is stored in SharedMemory first
- Check tenant_id matches the stored data
- Lower the similarity threshold

### Issue: "Empty expert responses"
- Verify OpenAI API key is set
- Check OPENAI_BASE_URL if using custom endpoint
- Review logs for specific expert errors

### Issue: "Multi-tenant isolation not working"
- Verify tenant_id is being passed correctly
- Check that similar_knowledge retrieval includes tenant_id
- Confirm Milvus partition keys are configured

### Issue: "Slow response times"
- Check if knowledge retrieval is taking long
- Enable embedding caching
- Use batch operations for multiple items
- Reduce top_k in search operations
