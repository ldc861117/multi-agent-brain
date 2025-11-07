"""
Demo output formatting and visualization utilities.
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from textwrap import fill


class DemoMode:
    """Enumeration of supported demo modes."""
    INTERACTIVE = "interactive"
    AUTOMATED = "automated"
    BENCHMARK = "benchmark"
    VISUALIZATION = "visualization"


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Special combinations
    SUCCESS = GREEN + BOLD
    WARNING = YELLOW + BOLD
    ERROR = RED + BOLD
    INFO = CYAN
    SECTION = HEADER + BOLD


class DemoOutput:
    """Handles beautiful output formatting for the demo."""
    
    def __init__(self, width: int = 80):
        self.width = width
    
    def _print_box(self, title: str, content: str, color: str = Colors.BLUE):
        """Print content in a nice box."""
        lines = content.split('\n')
        max_line_length = max(len(title), max(len(line) for line in lines), self.width - 4)
        
        # Top border
        border = '┌' + '─' * (max_line_length + 2) + '┐'
        print(f"{color}{border}{Colors.END}")
        
        # Title line
        title_padding = max_line_length - len(title)
        print(f"{color}│ {Colors.BOLD}{title}{Colors.END}{color} {' ' * title_padding} │{Colors.END}")
        
        # Separator
        print(f"{color}├{ '─' * (max_line_length + 2) }┤{Colors.END}")
        
        # Content lines
        for line in lines:
            line_padding = max_line_length - len(line)
            print(f"{color}│ {line}{' ' * line_padding} │{Colors.END}")
        
        # Bottom border
        print(f"{color}└{ '─' * (max_line_length + 2) }┘{Colors.END}")
    
    def print_section(self, title: str):
        """Print a section header."""
        separator = "=" * self.width
        print(f"\n{Colors.SECTION}{separator}{Colors.END}")
        print(f"{Colors.SECTION}{title.center(self.width)}{Colors.END}")
        print(f"{Colors.SECTION}{separator}{Colors.END}\n")
    
    def print_success(self, message: str):
        """Print a success message."""
        print(f"{Colors.SUCCESS}✅ {message}{Colors.END}")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"{Colors.WARNING}⚠️  {message}{Colors.END}")
    
    def print_error(self, message: str):
        """Print an error message."""
        print(f"{Colors.ERROR}❌ {message}{Colors.END}")
    
    def print_info(self, message: str):
        """Print an info message."""
        print(f"{Colors.INFO}ℹ️  {message}{Colors.END}")
    
    def print_question(self, question_id: str, question: str):
        """Print a formatted question."""
        question_box = f"""
📝 问题 #{question_id}
{fill(question, width=self.width-4)}
        """.strip()
        
        self._print_box(f"问题 #{question_id}", question_box, Colors.CYAN)
    
    def print_agent_process(self, agent_name: str, status: str, details: str = ""):
        """Print agent processing status."""
        status_icon = "✅" if status == "completed" else "🔄" if status == "processing" else "❌"
        
        content = f"{status_icon} {agent_name}: {status}"
        if details:
            content += f"\n   {details}"
        
        print(f"  {Colors.INFO}{content}{Colors.END}")
    
    def print_result(self, result: Dict[str, Any]):
        """Print the final result."""
        question_id = result.get("question_id", "unknown")
        answer = result.get("answer", "无答案")
        processing_time = result.get("processing_time", 0)
        metadata = result.get("metadata", {})
        
        # Agent processing timeline
        timeline_content = ""
        participating_agents = metadata.get("participating_agents", [])
        expert_responses = metadata.get("expert_responses", {})
        
        if participating_agents:
            timeline_content = "\n🤝 参与智能体:\n"
            for agent in participating_agents:
                agent_data = expert_responses.get(agent, {})
                if isinstance(agent_data, dict):
                    status = agent_data.get("status", "unknown")
                    response_time = agent_data.get("response_time", 0)
                    timeline_content += f"  • {agent}: {status} ({response_time:.2f}s)\n"
        
        # Answer box
        answer_preview = answer[:200] + "..." if len(answer) > 200 else answer
        answer_box = f"""
⏱️  处理时间: {processing_time:.2f} 秒
{timeline_content}
💡 答案:
{fill(answer_preview, width=self.width-8)}
        """.strip()
        
        self._print_box(f"✅ 答案 #{question_id}", answer_box, Colors.GREEN)
    
    def print_error_result(self, result: Dict[str, Any]):
        """Print error result."""
        question_id = result.get("question_id", "unknown")
        error = result.get("error", "未知错误")
        processing_time = result.get("processing_time", 0)
        
        error_box = f"""
⏱️  处理时间: {processing_time:.2f} 秒
❌ 错误信息: {error}
        """.strip()
        
        self._print_box(f"❌ 错误 #{question_id}", error_box, Colors.RED)
    
    def print_knowledge_stats(self, stats: Dict[str, Any]):
        """Print knowledge base statistics."""
        if not stats:
            return
        
        stats_content = f"""
📚 知识库统计:
  • 总文档数: {stats.get('total_count', 0)}
  • 集合信息: {len(stats.get('collections', {}))} 个集合
        """.strip()
        
        self._print_box("📊 知识库状态", stats_content, Colors.BLUE)
    
    def print_progress_bar(self, current: int, total: int, prefix: str = "", suffix: str = ""):
        """Print a progress bar."""
        if total == 0:
            return
        
        percent = (current / total) * 100
        filled_length = int(50 * current // total)
        bar = '█' * filled_length + '-' * (50 - filled_length)
        
        print(f'\r{prefix} |{Colors.GREEN}{bar}{Colors.END}| {percent:.1f}% {suffix}', end='', flush=True)
        
        if current == total:
            print()  # New line when complete
    
    def print_timeline(self, events: List[Dict[str, Any]]):
        """Print a visual timeline of events."""
        if not events:
            return
        
        self._print_box("⏰ 处理时间线", "")
        
        for i, event in enumerate(events):
            timestamp = event.get("timestamp", "")
            agent = event.get("agent", "unknown")
            action = event.get("action", "unknown")
            duration = event.get("duration", 0)
            
            # Format timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp
            else:
                time_str = "unknown"
            
            # Print event
            connector = "└──" if i > 0 else "┌──"
            print(f"  {Colors.INFO}{connector} [{time_str}] {agent}: {action}{Colors.END}")
            
            if duration > 0:
                print(f"      ⏱️  {duration:.2f}s")
    
    def print_agent_architecture(self):
        """Print the multi-agent architecture diagram."""
        architecture = """
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Brain 架构                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   用户输入   │───▶│ CoordinatorAgent │───▶│   专家智能体网络      │
└─────────────┘    └──────────────────┘    └─────────────────────┘
                          │                           │
                          ▼                           ▼
                   ┌──────────────┐         ┌────────────────────┐
                   │ SharedMemory │         │ • PythonExpert     │
                   │   知识存储    │         │ • MilvusExpert     │
                   └──────────────┘         │ • DevOpsExpert      │
                          │                   └────────────────────┘
                          ▼                           │
                   ┌──────────────┐                   ▼
                   │  历史知识检索  │         ┌────────────────────┐
                   └──────────────┘         │   综合答案生成       │
                          │                   └────────────────────┘
                          ▼                           │
                   ┌──────────────┐                   ▼
                   │  上下文增强  │         ┌────────────────────┐
                   └──────────────┘         │   知识积累存储       │
                                               └────────────────────┘
        """.strip()
        
        print(f"{Colors.CYAN}{architecture}{Colors.END}")
    
    def print_system_metrics(self, metrics: Dict[str, Any]):
        """Print system performance metrics."""
        if not metrics:
            return
        
        metrics_content = "📈 系统指标:\n"
        
        # Performance metrics
        if "avg_response_time" in metrics:
            metrics_content += f"  • 平均响应时间: {metrics['avg_response_time']:.2f}s\n"
        
        if "cache_hit_ratio" in metrics:
            metrics_content += f"  • 缓存命中率: {metrics['cache_hit_ratio']:.1%}\n"
        
        if "success_rate" in metrics:
            metrics_content += f"  • 成功率: {metrics['success_rate']:.1%}\n"
        
        # Knowledge metrics
        if "total_documents" in metrics:
            metrics_content += f"  • 知识库文档数: {metrics['total_documents']}\n"
        
        if "collections_count" in metrics:
            metrics_content += f"  • 集合数量: {metrics['collections_count']}\n"
        
        # Agent metrics
        if "agent_calls" in metrics:
            metrics_content += f"  • Agent 调用次数: {metrics['agent_calls']}\n"
        
        if "error_count" in metrics:
            metrics_content += f"  • 错误次数: {metrics['error_count']}\n"
        
        self._print_box("📊 系统指标", metrics_content.strip(), Colors.BLUE)
    
    def print_welcome(self):
        """Print welcome message and architecture."""
        welcome_msg = """
🤖 欢迎使用 Multi-Agent Brain DEMO！

这是一个完整的多智能体协作系统演示，展示：
• 智能问题分析和路由
• 多专家并行协作
• 知识积累和检索
• 上下文增强回答

请选择运行模式开始体验...
        """.strip()
        
        self._print_box("🎉 欢迎", welcome_msg, Colors.GREEN)
        self.print_agent_architecture()
    
    def print_goodbye(self, summary: Optional[Dict[str, Any]] = None):
        """Print goodbye message with optional summary."""
        goodbye_msg = "👋 感谢使用 Multi-Agent Brain DEMO！"
        
        if summary:
            stats = f"""
📊 本次会话总结:
  • 处理问题数: {summary.get('questions_processed', 0)}
  • 成功处理: {summary.get('successful', 0)}
  • 总耗时: {summary.get('total_time', 0):.2f}s
  • 平均响应时间: {summary.get('avg_response_time', 0):.2f}s
            """.strip()
            goodbye_msg = stats + "\n\n" + goodbye_msg
        
        self._print_box("🏁 结束", goodbye_msg, Colors.GREEN)