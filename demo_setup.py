"""
Demo environment setup and validation utilities.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from loguru import logger


class DemoEnvironmentError(Exception):
    """Raised when demo environment setup fails."""
    pass


def check_env_file() -> bool:
    """Check if .env file exists and has required variables."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("❌ .env 文件不存在")
        print("💡 请复制 .env.example 到 .env 并配置必要的环境变量")
        return False
    
    # Check for essential environment variables
    required_vars = [
        "CHAT_API_KEY",  # At minimum, need chat API key
    ]
    
    optional_vars = [
        "CHAT_API_BASE_URL",
        "CHAT_API_MODEL", 
        "EMBEDDING_API_KEY",
        "EMBEDDING_API_BASE_URL",
        "EMBEDDING_API_MODEL",
        "MILVUS_URI"
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ 缺少必需的环境变量: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"⚠️  缺少可选的环境变量: {', '.join(missing_optional)}")
        print("💡 系统将使用默认值，但建议配置这些变量以获得最佳体验")
    
    print("✅ .env 文件检查通过")
    return True


def check_openai_connection() -> bool:
    """Test OpenAI API connectivity."""
    try:
        from utils import get_agent_config, OpenAIClientWrapper
        
        # Get configuration for coordinator
        config = get_agent_config("coordination")
        client = OpenAIClientWrapper(config=config)
        
        # Test with a minimal request
        response = client.get_chat_completion(
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1
        )
        
        if response and response.choices:
            print("✅ OpenAI API 连接测试通过")
            return True
        else:
            print("❌ OpenAI API 返回空响应")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API 连接测试失败: {e}")
        return False


def check_milvus_connection() -> bool:
    """Test Milvus database connectivity."""
    try:
        from agents.shared_memory import SharedMemory
        
        memory = SharedMemory()
        health = memory.health_check()
        
        if health.get("milvus_connected", False):
            print("✅ Milvus 数据库连接正常")
            
            # Check collections
            collections = health.get("collections", {})
            if collections:
                print(f"✅ 找到 {len(collections)} 个集合: {', '.join(collections.keys())}")
            else:
                print("⚠️  没有找到现有集合，将在首次使用时创建")
            
            return True
        else:
            print("❌ Milvus 数据库连接失败")
            return False
            
    except Exception as e:
        print(f"❌ Milvus 连接测试失败: {e}")
        return False


def check_python_packages() -> bool:
    """Check if required Python packages are installed."""
    required_packages = [
        "openai",
        "pymilvus", 
        "loguru",
        "pydantic",
        "click",
        "asyncio",
        "pathlib"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少必需的 Python 包: {', '.join(missing_packages)}")
        print("💡 请运行: pip install -r requirements.txt")
        return False
    
    print("✅ Python 包检查通过")
    return True


def check_agent_imports() -> bool:
    """Check if all agent modules can be imported."""
    agents_to_check = [
        ("agents.coordination", "CoordinationAgent"),
        ("agents.python_expert", "PythonExpertAgent"),
        ("agents.milvus_expert", "MilvusExpertAgent"),
        ("agents.devops_expert", "DevOpsExpertAgent"),
        ("agents.shared_memory", "SharedMemory")
    ]
    
    failed_imports = []
    
    for module_name, class_name in agents_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            
            # Try to instantiate (if it's an agent class)
            if class_name != "SharedMemory":  # SharedMemory needs config
                # Just check if it's callable
                if not callable(agent_class):
                    failed_imports.append(f"{module_name}.{class_name} (not callable)")
            
        except Exception as e:
            failed_imports.append(f"{module_name}.{class_name}: {e}")
    
    if failed_imports:
        print("❌ Agent 导入检查失败:")
        for failure in failed_imports:
            print(f"  • {failure}")
        return False
    
    print("✅ Agent 模块导入检查通过")
    return True


def check_config_file() -> bool:
    """Check if config.yaml exists and is valid."""
    config_file = Path("config.yaml")
    
    if not config_file.exists():
        print("❌ config.yaml 文件不存在")
        return False
    
    try:
        import yaml
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ["channels", "network"]
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ config.yaml 缺少必需的配置节: {', '.join(missing_sections)}")
            return False
        
        # Check agent channels
        channels = config.get("channels", {})
        required_agents = ["coordination", "python_expert", "milvus_expert", "devops_expert"]
        missing_agents = []
        
        for agent in required_agents:
            if agent not in channels:
                missing_agents.append(agent)
        
        if missing_agents:
            print(f"❌ config.yaml 缺少必需的 agent 配置: {', '.join(missing_agents)}")
            return False
        
        print("✅ config.yaml 配置检查通过")
        return True
        
    except Exception as e:
        print(f"❌ config.yaml 解析失败: {e}")
        return False


def check_file_permissions() -> bool:
    """Check if we have necessary file permissions."""
    checks = [
        ("当前目录可写", Path(".").stat().st_mode & 0o200),
        ("agents 目录可读", Path("agents").exists() and Path("agents").stat().st_mode & 0o444),
        ("utils 目录可读", Path("utils").exists() and Path("utils").stat().st_mode & 0o444),
    ]
    
    failed_checks = []
    
    for check_name, condition in checks:
        if not condition:
            failed_checks.append(check_name)
    
    if failed_checks:
        print(f"❌ 文件权限检查失败: {', '.join(failed_checks)}")
        return False
    
    print("✅ 文件权限检查通过")
    return True


def check_python_version() -> bool:
    """Check Python version compatibility."""
    version_info = sys.version_info
    
    if version_info < (3, 8):
        print(f"❌ Python 版本过低: {version_info.major}.{version_info.minor}")
        print("💡 需要 Python 3.8 或更高版本")
        return False
    
    if version_info >= (3, 12):
        print(f"⚠️  Python 版本较新: {version_info.major}.{version_info.minor}")
        print("💡 建议使用 Python 3.9-3.11 以获得最佳兼容性")
    else:
        print(f"✅ Python 版本检查通过: {version_info.major}.{version_info.minor}.{version_info.micro}")
    
    return True


def check_system_resources() -> bool:
    """Check system resources."""
    try:
        import psutil
        
        # Check memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        
        if available_gb < 1.0:
            print(f"⚠️  可用内存较低: {available_gb:.1f}GB")
            print("💡 建议至少有 2GB 可用内存以获得最佳性能")
        else:
            print(f"✅ 内存检查通过: {available_gb:.1f}GB 可用")
        
        # Check disk space
        disk = psutil.disk_usage('.')
        available_gb = disk.free / (1024**3)
        
        if available_gb < 0.5:
            print(f"⚠️  磁盘空间较低: {available_gb:.1f}GB")
            print("💡 建议至少有 1GB 可用磁盘空间")
        else:
            print(f"✅ 磁盘空间检查通过: {available_gb:.1f}GB 可用")
        
        return True
        
    except ImportError:
        print("⚠️  psutil 未安装，跳过系统资源检查")
        print("💡 可以安装 psutil 来监控系统资源: pip install psutil")
        return True
    except Exception as e:
        print(f"⚠️  系统资源检查失败: {e}")
        return True


def check_environment() -> bool:
    """Run all environment checks."""
    print("🔍 开始环境检查...")
    print("=" * 50)
    
    checks = [
        ("Python 版本", check_python_version),
        ("Python 包", check_python_packages),
        ("配置文件", check_config_file),
        ("环境变量", check_env_file),
        ("Agent 模块", check_agent_imports),
        ("文件权限", check_file_permissions),
        ("系统资源", check_system_resources),
        ("OpenAI 连接", check_openai_connection),
        ("Milvus 连接", check_milvus_connection),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n🔍 检查 {check_name}...")
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ {check_name} 检查失败")
        except Exception as e:
            print(f"❌ {check_name} 检查出错: {e}")
    
    print("\n" + "=" * 50)
    success_rate = (passed / total) * 100
    
    if passed == total:
        print(f"🎉 所有检查通过！({passed}/{total})")
        return True
    elif passed >= total - 2:  # Allow up to 2 failures
        print(f"⚠️  大部分检查通过 ({passed}/{total}, {success_rate:.1f}%)")
        print("💡 系统应该可以正常运行，但建议修复失败的检查项")
        return True
    else:
        print(f"❌ 多项检查失败 ({passed}/{total}, {success_rate:.1f}%)")
        print("💡 请修复失败的检查项后再运行 DEMO")
        return False


def setup_demo_environment() -> bool:
    """Setup the demo environment if needed."""
    print("🛠️  设置 DEMO 环境...")
    
    # Create necessary directories
    directories_to_create = [
        "logs",
        "data",
        "temp"
    ]
    
    for directory in directories_to_create:
        dir_path = Path(directory)
        if not dir_path.exists():
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"✅ 创建目录: {directory}")
            except Exception as e:
                print(f"❌ 创建目录失败 {directory}: {e}")
                return False
        else:
            print(f"✅ 目录已存在: {directory}")
    
    # Check if demo questions file exists
    demo_questions_file = Path("demo_questions.json")
    if not demo_questions_file.exists():
        print("⚠️  demo_questions.json 不存在，将在运行时创建默认问题集")
    
    return True


if __name__ == "__main__":
    # Run environment check when called directly
    success = check_environment()
    
    if success:
        print("\n🚀 环境检查完成，可以运行 DEMO！")
        sys.exit(0)
    else:
        print("\n❌ 环境检查失败，请修复问题后再运行 DEMO")
        sys.exit(1)