"""
Demo execution modes and runners for different testing scenarios.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from demo_output import DemoOutput, DemoMode


class DemoMode:
    """Enumeration of supported demo modes."""
    INTERACTIVE = "interactive"
    AUTOMATED = "automated"
    BENCHMARK = "benchmark"
    VISUALIZATION = "visualization"


class DemoRunner:
    """Handles different demo execution modes and scenarios."""
    
    def __init__(self):
        self.output = DemoOutput()
    
    async def run_stress_test(self, agents: Dict[str, Any], memory: Any, duration_seconds: int = 60):
        """Run stress test with continuous load for specified duration."""
        self.output.print_section("🔥 压力测试模式")
        
        # Stress test questions pool
        questions_pool = [
            "如何优化 Python 列表操作？",
            "Milvus 向量搜索的最佳配置？",
            "Docker 容器优化技巧？",
            "异步编程的性能提升？",
            "数据库索引优化策略？",
            "微服务架构设计原则？",
            "机器学习模型部署？",
            "缓存策略最佳实践？"
        ]
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        question_count = 0
        success_count = 0
        error_count = 0
        
        self.output.print_info(f"🚀 开始 {duration_seconds} 秒压力测试...")
        
        async def send_question():
            nonlocal question_count, success_count, error_count
            
            while time.time() < end_time:
                try:
                    question = random.choice(questions_pool)
                    question_count += 1
                    
                    # Simulate processing through coordinator
                    coordinator = agents["coordinator"]
                    message = {
                        "content": {"text": question},
                        "id": f"stress_{question_count:06d}",
                        "tenant_id": "stress_test",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    response = await coordinator.handle_message(message)
                    
                    if response and response.content:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                
                # Small random delay to simulate real usage
                await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Start multiple concurrent workers
        workers = [asyncio.create_task(send_question()) for _ in range(3)]
        
        # Monitor progress
        while time.time() < end_time:
            await asyncio.sleep(5)
            elapsed = time.time() - start_time
            remaining = end_time - time.time()
            rate = question_count / elapsed if elapsed > 0 else 0
            
            self.output.print_info(
                f"⏱️  已运行: {elapsed:.1f}s | 剩余: {remaining:.1f}s | "
                f"问题数: {question_count} | 成功: {success_count} | 失败: {error_count} | "
                f"速率: {rate:.2f} q/s"
            )
        
        # Wait for all workers to finish
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Final statistics
        total_time = time.time() - start_time
        final_rate = question_count / total_time if total_time > 0 else 0
        success_rate = (success_count / question_count * 100) if question_count > 0 else 0
        
        stats = f"""
📊 压力测试结果:
总耗时: {total_time:.2f} 秒
总问题数: {question_count}
成功处理: {success_count}
处理失败: {error_count}
成功率: {success_rate:.1f}%
平均速率: {final_rate:.2f} 问题/秒
        """
        self.output.print_info(stats)
    
    async def run_knowledge_accumulation_test(self, agents: Dict[str, Any], memory: Any):
        """Test knowledge accumulation and retrieval over multiple sessions."""
        self.output.print_section("🧠 知识积累测试")
        
        # Related questions that should benefit from accumulated knowledge
        question_sets = [
            {
                "topic": "Python性能优化",
                "questions": [
                    "如何优化 Python 循环性能？",
                    "Python 列表推导式为什么比 for 循环快？",
                    "如何使用 NumPy 提升 Python 计算性能？",
                    "Python 多线程 vs 多进程的性能对比？"
                ]
            },
            {
                "topic": "Milvus向量数据库",
                "questions": [
                    "Milvus 如何处理大规模向量数据？",
                    "Milvus 的索引类型选择建议？",
                    "如何优化 Milvus 查询性能？",
                    "Milvus 集群部署的最佳实践？"
                ]
            }
        ]
        
        for topic_set in question_sets:
            topic = topic_set["topic"]
            questions = topic_set["questions"]
            
            self.output.print_info(f"\n📚 测试主题: {topic}")
            
            # Process questions sequentially to build knowledge
            for i, question in enumerate(questions, 1):
                self.output.print_info(f"\n[{i}/{len(questions)}] {question}")
                
                try:
                    coordinator = agents["coordinator"]
                    message = {
                        "content": {"text": question},
                        "id": f"knowledge_{topic}_{i}",
                        "tenant_id": "knowledge_test",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    start_time = time.time()
                    response = await coordinator.handle_message(message)
                    processing_time = time.time() - start_time
                    
                    if response and response.content:
                        # Show if similar knowledge was found
                        metadata = response.metadata or {}
                        similar_count = metadata.get("similar_documents_count", 0)
                        
                        self.output.print_success(
                            f"✅ 处理完成 ({processing_time:.2f}s) | "
                            f"找到相关知识: {similar_count} 条"
                        )
                        
                        # Show brief preview of answer
                        answer_preview = response.content[:100] + "..." if len(response.content) > 100 else response.content
                        self.output.print_info(f"💡 答案预览: {answer_preview}")
                    else:
                        self.output.print_error("❌ 处理失败")
                        
                except Exception as e:
                    self.output.print_error(f"❌ 错误: {e}")
                
                await asyncio.sleep(1)  # Small delay between questions
    
    async def run_error_recovery_test(self, agents: Dict[str, Any], memory: Any):
        """Test system behavior under error conditions and recovery."""
        self.output.print_section("🛡️  错误恢复测试")
        
        # Test scenarios that might cause errors
        error_scenarios = [
            {
                "name": "空问题测试",
                "question": "",
                "expected_behavior": "应该优雅处理空输入"
            },
            {
                "name": "超长问题测试", 
                "question": "如何" * 1000,  # Very long question
                "expected_behavior": "应该处理长文本或给出合理限制"
            },
            {
                "name": "特殊字符测试",
                "question": "如何处理 🚀 emoji 和 特殊字符 @#$%^&*()?",
                "expected_behavior": "应该正确处理特殊字符"
            },
            {
                "name": "混合语言测试",
                "question": "How to optimize Python 性能 for 中文 users?",
                "expected_behavior": "应该处理混合语言输入"
            }
        ]
        
        for scenario in error_scenarios:
            self.output.print_info(f"\n🧪 {scenario['name']}")
            self.output.print_info(f"预期: {scenario['expected_behavior']}")
            
            try:
                coordinator = agents["coordinator"]
                message = {
                    "content": {"text": scenario["question"]},
                    "id": f"error_test_{scenario['name']}",
                    "tenant_id": "error_test",
                    "timestamp": datetime.now().isoformat()
                }
                
                start_time = time.time()
                response = await coordinator.handle_message(message)
                processing_time = time.time() - start_time
                
                if response and response.content:
                    self.output.print_success(f"✅ 正常处理 ({processing_time:.2f}s)")
                    
                    # Check if response is reasonable
                    if len(response.content) > 10:
                        self.output.print_info("💡 返回了有意义的回答")
                    else:
                        self.output.print_warning("⚠️  回答可能过短")
                else:
                    self.output.print_warning("⚠️  没有返回回答，但系统没有崩溃")
                    
            except Exception as e:
                # Check if it's a handled error or system crash
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["timeout", "rate", "limit"]):
                    self.output.print_warning(f"⚠️  可预期的错误: {e}")
                else:
                    self.output.print_error(f"❌ 意外错误: {e}")
            
            await asyncio.sleep(0.5)
    
    async def run_collaboration_test(self, agents: Dict[str, Any], memory: Any):
        """Test multi-agent collaboration scenarios."""
        self.output.print_section("🤝 协作测试")
        
        # Questions that should require multiple experts
        collaboration_questions = [
            {
                "question": "如何构建一个高性能的 Python + Milvus 向量搜索系统并进行容器化部署？",
                "expected_experts": ["python_expert", "milvus_expert", "devops_expert"],
                "complexity": "high"
            },
            {
                "question": "使用 Python 开发 Milvus 数据迁移工具的 DevOps 最佳实践？",
                "expected_experts": ["python_expert", "milvus_expert", "devops_expert"],
                "complexity": "medium"
            },
            {
                "question": "Python 异步编程在 Milvus 客户端中的应用和性能监控？",
                "expected_experts": ["python_expert", "milvus_expert"],
                "complexity": "medium"
            }
        ]
        
        for i, test_case in enumerate(collaboration_questions, 1):
            question = test_case["question"]
            expected_experts = test_case["expected_experts"]
            complexity = test_case["complexity"]
            
            self.output.print_info(f"\n[{i}] 协作测试 - 复杂度: {complexity}")
            self.output.print_info(f"问题: {question}")
            self.output.print_info(f"预期参与专家: {', '.join(expected_experts)}")
            
            try:
                coordinator = agents["coordinator"]
                message = {
                    "content": {"text": question},
                    "id": f"collab_{i}",
                    "tenant_id": "collaboration_test",
                    "timestamp": datetime.now().isoformat()
                }
                
                start_time = time.time()
                response = await coordinator.handle_message(message)
                processing_time = time.time() - start_time
                
                if response and response.content:
                    metadata = response.metadata or {}
                    
                    # Check collaboration metadata
                    participating_agents = metadata.get("participating_agents", [])
                    expert_responses = metadata.get("expert_responses", {})
                    
                    self.output.print_success(f"✅ 协作完成 ({processing_time:.2f}s)")
                    self.output.print_info(f"🤝 参与智能体: {participating_agents}")
                    
                    # Show expert responses summary
                    for expert, expert_data in expert_responses.items():
                        if isinstance(expert_data, dict) and expert_data.get("response"):
                            response_preview = expert_data["response"][:50] + "..."
                            self.output.print_info(f"  📝 {expert}: {response_preview}")
                    
                    # Show final answer preview
                    answer_preview = response.content[:100] + "..." if len(response.content) > 100 else response.content
                    self.output.print_info(f"💡 综合答案: {answer_preview}")
                    
                else:
                    self.output.print_error("❌ 协作失败")
                    
            except Exception as e:
                self.output.print_error(f"❌ 协作测试错误: {e}")
            
            await asyncio.sleep(2)  # Longer delay for complex collaboration tests