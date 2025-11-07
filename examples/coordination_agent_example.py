"""Example usage of the CoordinationAgent.

This example demonstrates how the CoordinationAgent orchestrates
multi-agent collaboration to answer complex questions.
"""

import asyncio
from agents.coordination import CoordinationAgent


async def main():
    """Run a simple example of the CoordinationAgent."""
    # Initialize the agent
    coordinator = CoordinationAgent()

    # Example 1: Simple Python question
    simple_message = {
        "content": {"text": "How do I define a function in Python?"}
    }

    print("=" * 60)
    print("Example 1: Simple Question")
    print("=" * 60)
    response = await coordinator.handle_message(simple_message)
    print(f"Question: How do I define a function in Python?")
    print(f"Answer: {response.content[:200]}...")
    print(f"Metadata: {response.metadata}")
    print()

    # Example 2: Complex cross-domain question
    complex_message = {
        "content": {
            "text": (
                "I want to build a Python application that uses Milvus "
                "for vector storage and needs to be deployed to production. "
                "What are the best practices?"
            )
        },
        "tenant_id": "project_123",
    }

    print("=" * 60)
    print("Example 2: Complex Cross-Domain Question")
    print("=" * 60)
    response = await coordinator.handle_message(complex_message)
    print(f"Question: {complex_message['content']['text']}")
    print(f"Answer: {response.content[:300]}...")
    print(f"Complexity: {response.metadata.get('complexity')}")
    print(f"Experts involved: {response.metadata.get('experts_involved')}")
    print(f"Tenant ID: {complex_message['tenant_id']}")
    print()

    # Example 3: Question with similar historical knowledge
    # (This requires some knowledge stored in SharedMemory first)
    historical_question = {
        "content": {"text": "How to optimize Milvus indexing?"}
    }

    print("=" * 60)
    print("Example 3: Question Leveraging Historical Knowledge")
    print("=" * 60)
    response = await coordinator.handle_message(historical_question)
    print(f"Question: How to optimize Milvus indexing?")
    print(f"Answer: {response.content[:200]}...")
    print(f"Historical knowledge used: {response.metadata.get('knowledge_used')}")
    print()

    # Example 4: Analyzing a complex question
    print("=" * 60)
    print("Example 4: Question Analysis Details")
    print("=" * 60)
    question = (
        "I need to implement a distributed training system using Python "
        "with Milvus for vector embeddings. How should I architect this?"
    )
    analysis = coordinator.analyze_question(question)
    print(f"Question: {question}")
    print(f"Required Experts: {analysis.get('required_experts')}")
    print(f"Complexity: {analysis.get('complexity')}")
    print(f"Keywords: {analysis.get('keywords')}")
    print(f"Reasoning: {analysis.get('reasoning')}")
    print()

    # Example 5: Knowledge retrieval
    print("=" * 60)
    print("Example 5: Retrieving Similar Historical Knowledge")
    print("=" * 60)
    similar_docs = await coordinator.retrieve_similar_knowledge(
        "How to use Milvus?", tenant_id="project_123"
    )
    print(
        f"Found {len(similar_docs)} similar documents for 'How to use Milvus?'"
    )
    for i, doc in enumerate(similar_docs[:3], 1):
        print(f"  {i}. Similarity: {doc.get('similarity_score', 'N/A')}")
        if "problem" in doc:
            print(f"     Problem: {doc['problem'][:50]}...")
        if "task_description" in doc:
            print(f"     Task: {doc['task_description'][:50]}...")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CoordinationAgent Usage Examples")
    print("=" * 60 + "\n")

    asyncio.run(main())

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
