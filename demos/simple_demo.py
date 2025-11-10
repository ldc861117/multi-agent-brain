#!/usr/bin/env python3
"""
Simple DEMO test that works without external API calls.
This demonstrates the structure and flow without requiring real API keys.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .output import DemoOutput, DemoMode


class MockAgent:
    """Mock agent for testing without API dependencies."""
    
    def __init__(self, name: str):
        self.name = name
        self.description = f"Mock {name} agent"
    
    async def handle_message(self, message):
        """Mock message handling."""
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Generate mock response based on agent type
        question = message.get("content", {}).get("text", "")
        
        if "python" in question.lower():
            response = f"[{self.name}] Python 优化建议：使用生成器、避免全局变量、考虑多进程处理。"
        elif "milvus" in question.lower():
            response = f"[{self.name}] Milvus 建议：选择合适的索引类型（HNSW/IVF）、优化向量维度、分区策略。"
        elif "docker" in question.lower() or "部署" in question.lower():
            response = f"[{self.name}] 部署建议：使用多阶段构建、优化镜像大小、健康检查、资源限制。"
        else:
            response = f"[{self.name}] 通用建议：需要更多上下文信息来提供具体建议。"
        
        return MockResponse(content=response, metadata={"agent": self.name})


class MockResponse:
    """Mock response object."""
    
    def __init__(self, content: str, metadata: dict = None):
        self.content = content
        self.metadata = metadata or {}


class MockSharedMemory:
    """Mock shared memory for testing."""
    
    def __init__(self):
        self.documents = []
    
    def store_knowledge(self, collection, tenant_id, content, metadata=None):
        """Mock knowledge storage."""
        doc = {
            "id": len(self.documents) + 1,
            "collection": collection,
            "tenant_id": tenant_id,
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
        self.documents.append(doc)
        return doc["id"]
    
    def search_knowledge(self, collection, tenant_id, query, top_k=5):
        """Mock knowledge search."""
        # Simple mock search - return recent documents
        relevant_docs = [
            doc for doc in self.documents 
            if doc["collection"] == collection and doc["tenant_id"] == tenant_id
        ][-top_k:]
        
        return [
            {
                "id": doc["id"],
                "content": doc["content"],
                "similarity_score": 0.8,
                "metadata": doc.get("metadata", {})
            }
            for doc in relevant_docs
        ]
    
    def get_collection_stats(self, collection, tenant_id):
        """Mock collection statistics."""
        doc_count = len([
            doc for doc in self.documents
            if doc["collection"] == collection and doc["tenant_id"] == tenant_id
        ])
        
        return {
            "total_count": doc_count,
            "collections": {collection: doc_count}
        }
    
    def health_check(self):
        """Mock health check."""
        return {"milvus_connected": True, "collections": {}}


class MockCoordinatorAgent:
    """Mock coordinator agent for testing."""
    
    def __init__(self):
        self.name = "coordination"
        self.agents = {
            "python_expert": MockAgent("python_expert"),
            "milvus_expert": MockAgent("milvus_expert"),
            "devops_expert": MockAgent("devops_expert")
        }
        self.memory = MockSharedMemory()
    
    async def handle_message(self, message):
        """Mock coordination logic."""
        question = message.get("content", {}).get("text", "")
        question_id = message.get("id", "unknown")
        
        # Determine which agents to involve
        participating_agents = []
        expert_responses = {}
        
        question_lower = question.lower()
        if "python" in question_lower:
            participating_agents.append("python_expert")
        if "milvus" in question_lower:
            participating_agents.append("milvus_expert")
        if "docker" in question_lower or "部署" in question_lower or "devops" in question_lower:
            participating_agents.append("devops_expert")
        
        # If no specific agents, use all
        if not participating_agents:
            participating_agents = list(self.agents.keys())
        
        # Get responses from participating agents
        for agent_name in participating_agents:
            agent = self.agents[agent_name]
            start_time = time.time()
            response = await agent.handle_message(message)
            response_time = time.time() - start_time
            
            expert_responses[agent_name] = {
                "response": response.content,
                "response_time": response_time,
                "status": "completed"
            }
        
        # Synthesize final answer
        if expert_responses:
            final_answer = f"基于专家分析的结果：\n\n"
            for agent_name, response_data in expert_responses.items():
                final_answer += f"🔹 {response_data['response']}\n\n"
        else:
            final_answer = "抱歉，我无法处理这个问题。请尝试更具体的问题。"
        
        # Store in memory
        self.memory.store_knowledge(
            collection="collaboration_history",
            tenant_id=message.get("tenant_id", "demo"),
            content={
                "question": question,
                "answer": final_answer,
                "participating_agents": participating_agents
            }
        )
        
        return MockResponse(
            content=final_answer,
            metadata={
                "participating_agents": participating_agents,
                "expert_responses": expert_responses,
                "question_id": question_id
            }
        )


class SimpleDemo:
    """Simplified demo that works without external dependencies."""
    
    def __init__(self):
        self.output = DemoOutput()
        self.question_count = 0
    
    async def run_simple_demo(self):
        """Run a simple demo with mock data."""
        self.output.print_section("🤖 Multi-Agent Brain 简化 DEMO")
        self.output.print_info("这是一个无需 API 密钥的演示版本")
        self.output.print_info("展示多智能体协作的基本流程")
        
        # Initialize mock coordinator
        coordinator = MockCoordinatorAgent()
        memory = coordinator.memory
        
        # Test questions
        test_questions = [
            "如何优化 Python 列表推导式的性能？",
            "Milvus 向量数据库如何处理高维向量搜索？",
            "如何在 Docker 中部署 Python 应用？",
            "Python 和 Milvus 集成的最佳实践？"
        ]
        
        self.output.print_info(f"📋 开始处理 {len(test_questions)} 个测试问题...")
        
        for i, question in enumerate(test_questions, 1):
            self.question_count += 1
            question_id = f"demo_{self.question_count:03d}"
            
            self.output.print_question(question_id, question)
            
            # Process through coordinator
            start_time = time.time()
            
            message = {
                "content": {"text": question},
                "id": question_id,
                "tenant_id": "simple_demo",
                "timestamp": datetime.now().isoformat()
            }
            
            response = await coordinator.handle_message(message)
            processing_time = time.time() - start_time
            
            # Display result
            result = {
                "question_id": question_id,
                "question": question,
                "answer": response.content,
                "processing_time": processing_time,
                "metadata": response.metadata,
                "tenant_id": "simple_demo"
            }
            
            self.output.print_result(result)
            
            # Show knowledge stats
            stats = memory.get_collection_stats("collaboration_history", "simple_demo")
            self.output.print_knowledge_stats(stats)
            
            print("\n" + "=" * 60 + "\n")
            
            # Small delay between questions
            await asyncio.sleep(1)
        
        # Final summary
        self.output.print_section("📊 DEMO 总结")
        
        final_stats = memory.get_collection_stats("collaboration_history", "simple_demo")
        self.output.print_info(f"✅ 成功处理 {len(test_questions)} 个问题")
        self.output.print_info(f"📚 知识库累积 {final_stats['total_count']} 条记录")
        self.output.print_info("🎉 DEMO 完成！")
        
        # Show architecture
        self.output.print_agent_architecture()


async def main():
    """Main entry point."""
    try:
        demo = SimpleDemo()
        await demo.run_simple_demo()
    except KeyboardInterrupt:
        print("\n\n👋 DEMO 被用户中断")
    except Exception as e:
        print(f"\n❌ DEMO 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())