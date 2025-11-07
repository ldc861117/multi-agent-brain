#!/usr/bin/env python3
"""
End-to-end Multi-Agent Brain DEMO

This script demonstrates the complete workflow of the multi-agent system:
1. User asks a question
2. Coordinator analyzes and routes to experts
3. Expert agents process in parallel
4. Coordinator synthesizes results
5. Knowledge is stored in SharedMemory
6. Final answer is presented with metrics
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import click
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.coordination import CoordinationAgent
from agents.python_expert import PythonExpertAgent
from agents.milvus_expert import MilvusExpertAgent
from agents.devops_expert import DevOpsExpertAgent
from agents.shared_memory import SharedMemory
from utils import get_agent_config, OpenAIClientWrapper
from demo_setup import check_environment, DemoEnvironmentError
from demo_output import DemoOutput, DemoMode
from demo_modes import DemoRunner


class MultiAgentDemo:
    """Main DEMO orchestrator for the multi-agent brain system."""

    def __init__(self, mode: str = "interactive", config_file: str = "config.yaml"):
        """Initialize the DEMO with specified mode and configuration."""
        self.mode = DemoMode(mode)
        self.config_file = config_file
        self.agents = {}
        self.memory = None
        self.output = DemoOutput()
        self.runner = DemoRunner()
        self.question_count = 0

    async def setup_agents(self) -> Dict[str, Any]:
        """Initialize all agents and shared memory."""
        self.output.print_section("🚀 启动智能体网络")
        
        try:
            # Initialize SharedMemory first
            self.memory = SharedMemory()
            self.output.print_success("✅ SharedMemory 初始化完成")

            # Initialize all expert agents
            self.agents["coordinator"] = CoordinationAgent()
            self.output.print_success("✅ CoordinatorAgent 初始化完成")

            self.agents["python_expert"] = PythonExpertAgent()
            self.output.print_success("✅ PythonExpertAgent 初始化完成")

            self.agents["milvus_expert"] = MilvusExpertAgent()
            self.output.print_success("✅ MilvusExpertAgent 初始化完成")

            self.agents["devops_expert"] = DevOpsExpertAgent()
            self.output.print_success("✅ DevOpsExpertAgent 初始化完成")

            # Test OpenAI client connectivity
            try:
                test_client = get_agent_config("coordination")
                client = OpenAIClientWrapper(config=test_client)
                # Simple test call
                test_response = client.get_chat_completion(
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1
                )
                self.output.print_success("✅ OpenAI API 连接测试通过")
            except Exception as e:
                self.output.print_warning(f"⚠️  OpenAI API 连接测试失败: {e}")

            # Test SharedMemory connectivity
            try:
                health = self.memory.health_check()
                if health.get("milvus_connected", False):
                    self.output.print_success("✅ Milvus 数据库连接正常")
                else:
                    self.output.print_warning("⚠️  Milvus 数据库连接异常")
            except Exception as e:
                self.output.print_warning(f"⚠️  SharedMemory 健康检查失败: {e}")

            return self.agents

        except Exception as e:
            self.output.print_error(f"❌ 智能体初始化失败: {e}")
            raise

    async def process_question(self, question: str, tenant_id: str = "demo") -> Dict[str, Any]:
        """Process a single question through the multi-agent system."""
        self.question_count += 1
        question_id = f"q_{self.question_count:03d}"
        
        start_time = time.time()
        
        self.output.print_question(question_id, question)
        
        try:
            # Prepare message for coordinator
            message = {
                "content": {"text": question},
                "id": question_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }

            # Process through coordinator
            coordinator = self.agents["coordinator"]
            response = await coordinator.handle_message(message)
            
            processing_time = time.time() - start_time
            
            # Extract metadata and results
            metadata = response.metadata or {}
            
            result = {
                "question_id": question_id,
                "question": question,
                "answer": response.content,
                "processing_time": processing_time,
                "metadata": metadata,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }

            # Display results
            self.output.print_result(result)
            
            # Show knowledge base statistics
            if self.memory:
                try:
                    stats = self.memory.get_collection_stats("collaboration_history", tenant_id)
                    self.output.print_knowledge_stats(stats)
                except Exception as e:
                    self.output.print_warning(f"⚠️  无法获取知识库统计: {e}")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            error_result = {
                "question_id": question_id,
                "question": question,
                "answer": None,
                "error": str(e),
                "processing_time": processing_time,
                "tenant_id": tenant_id,
                "timestamp": datetime.now().isoformat()
            }
            
            self.output.print_error_result(error_result)
            logger.exception(f"Error processing question {question_id}")
            return error_result

    async def run_interactive_mode(self):
        """Run the DEMO in interactive mode."""
        self.output.print_section("🤖 Multi-Agent Brain 交互式 DEMO")
        self.output.print_info("输入问题进行测试（输入 'quit', 'exit', 或 'q' 退出）")
        self.output.print_info("输入 'help' 查看可用命令")
        
        while True:
            try:
                question = input("\n📝 您的问题: ").strip()
                
                if question.lower() in ["quit", "exit", "q"]:
                    self.output.print_info("\n👋 再见！")
                    break
                
                if question.lower() == "help":
                    self._show_help()
                    continue
                
                if not question:
                    continue
                
                await self.process_question(question)
                
            except KeyboardInterrupt:
                self.output.print_info("\n\n中断演示")
                break
            except EOFError:
                self.output.print_info("\n\n再见！")
                break

    def _show_help(self):
        """Show help information for interactive mode."""
        help_text = """
📋 可用命令:
  help     - 显示此帮助信息
  quit     - 退出 DEMO
  exit     - 退出 DEMO  
  q        - 退出 DEMO

💡 示例问题:
  - 如何用 Python 优化列表推导式的性能？
  - Milvus 向量数据库如何处理高维向量搜索？
  - 如何在 Docker 中部署 multi-agent-brain 系统？
  - 使用 Python 和 Milvus 构建实时向量搜索系统的最佳实践是什么？
  - 如何监控和优化 multi-agent 系统的性能？
        """
        self.output.print_info(help_text)

    async def run_automated_mode(self):
        """Run the DEMO in automated mode with predefined questions."""
        self.output.print_section("🤖 Multi-Agent Brain 自动化 DEMO")
        
        # Load predefined questions
        questions_file = project_root / "demo_questions.json"
        if not questions_file.exists():
            self.output.print_error(f"❌ 问题文件不存在: {questions_file}")
            return
        
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
            
            questions = questions_data.get("questions", [])
            if not questions:
                self.output.print_warning("⚠️  没有找到预定义问题")
                return
            
            self.output.print_info(f"📋 开始处理 {len(questions)} 个预定义问题...")
            
            results = []
            for i, q_data in enumerate(questions, 1):
                question = q_data.get("question", "")
                category = q_data.get("category", "unknown")
                expected_experts = q_data.get("expected_expert", [])
                
                self.output.print_info(f"\n[{i}/{len(questions)}] 类别: {category} | 预期专家: {', '.join(expected_experts)}")
                
                result = await self.process_question(question, tenant_id="automated_demo")
                result["category"] = category
                result["expected_experts"] = expected_experts
                results.append(result)
                
                # Small delay between questions
                await asyncio.sleep(1)
            
            # Show summary
            self._show_automated_summary(results)
            
        except Exception as e:
            self.output.print_error(f"❌ 自动化模式执行失败: {e}")
            logger.exception("Automated mode failed")

    def _show_automated_summary(self, results: List[Dict[str, Any]]):
        """Show summary of automated test results."""
        self.output.print_section("📊 自动化测试总结")
        
        total = len(results)
        successful = sum(1 for r in results if r.get("answer") and not r.get("error"))
        failed = total - successful
        
        avg_time = sum(r.get("processing_time", 0) for r in results) / total if total > 0 else 0
        
        summary = f"""
总问题数: {total}
成功处理: {successful}
处理失败: {failed}
平均处理时间: {avg_time:.2f} 秒
成功率: {(successful/total*100):.1f}%
        """
        self.output.print_info(summary)
        
        # Show category breakdown
        categories = {}
        for result in results:
            cat = result.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0}
            categories[cat]["total"] += 1
            if result.get("answer") and not result.get("error"):
                categories[cat]["success"] += 1
        
        if categories:
            self.output.print_info("\n📈 分类统计:")
            for cat, stats in categories.items():
                success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
                self.output.print_info(f"  {cat}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

    async def run_benchmark_mode(self):
        """Run the DEMO in benchmark mode for performance testing."""
        self.output.print_section("🚀 Multi-Agent Brain 性能基准测试")
        
        # Define benchmark questions
        benchmark_questions = [
            "如何优化 Python 代码性能？",
            "Milvus 数据库的最佳实践是什么？",
            "如何部署容器化应用？",
            "向量搜索的性能优化技巧？",
            "多线程编程的最佳实践？"
        ]
        
        concurrent_levels = [1, 3, 5]  # Different concurrency levels
        
        for concurrency in concurrent_levels:
            self.output.print_info(f"\n🔄 测试并发级别: {concurrency}")
            
            start_time = time.time()
            tasks = []
            
            for i in range(concurrency):
                question = benchmark_questions[i % len(benchmark_questions)]
                task = self.process_question(
                    question, 
                    tenant_id=f"benchmark_concurrency_{concurrency}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Calculate metrics
            successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("answer"))
            avg_response_time = sum(r.get("processing_time", 0) for r in results if not isinstance(r, Exception)) / len(results)
            
            throughput = successful / total_time if total_time > 0 else 0
            
            metrics = f"""
并发级别: {concurrency}
总耗时: {total_time:.2f} 秒
成功请求: {successful}/{len(results)}
平均响应时间: {avg_response_time:.2f} 秒
吞吐量: {throughput:.2f} 请求/秒
            """
            self.output.print_info(metrics)
            
            # Small delay between concurrency levels
            await asyncio.sleep(2)

    async def run(self):
        """Main entry point for running the DEMO."""
        try:
            # Check environment first
            if not check_environment():
                self.output.print_error("❌ 环境检查失败，请检查配置")
                return
            
            # Setup agents
            await self.setup_agents()
            
            # Run based on mode
            if self.mode == DemoMode.INTERACTIVE:
                await self.run_interactive_mode()
            elif self.mode == DemoMode.AUTOMATED:
                await self.run_automated_mode()
            elif self.mode == DemoMode.BENCHMARK:
                await self.run_benchmark_mode()
            else:
                self.output.print_error(f"❌ 不支持的模式: {self.mode}")
                
        except KeyboardInterrupt:
            self.output.print_info("\n\n演示被用户中断")
        except Exception as e:
            self.output.print_error(f"❌ DEMO 执行失败: {e}")
            logger.exception("DEMO execution failed")
        finally:
            self.output.print_section("🏁 DEMO 结束")


@click.command()
@click.option('--mode', '-m', 
              type=click.Choice(['interactive', 'automated', 'benchmark'], case_sensitive=False),
              default='interactive', 
              help='DEMO 运行模式')
@click.option('--config', '-c', 
              default='config.yaml', 
              help='配置文件路径')
def main(mode: str, config: str):
    """启动 Multi-Agent Brain DEMO
    
    MODES:
      interactive  交互式模式，用户手动输入问题
      automated    自动化模式，使用预定义问题集
      benchmark    性能测试模式，测试并发性能
    
    EXAMPLES:
      python demo_runner.py                          # 交互式模式
      python demo_runner.py --mode automated         # 自动化模式
      python demo_runner.py --mode benchmark         # 性能测试
    """
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[agent_id]}</cyan> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run demo
    demo = MultiAgentDemo(mode=mode, config_file=config)
    asyncio.run(demo.run())


if __name__ == "__main__":
    main()