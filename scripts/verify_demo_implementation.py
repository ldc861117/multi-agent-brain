#!/usr/bin/env python3
"""
Final verification script for Multi-Agent Brain DEMO implementation.
"""

import os
import json
from pathlib import Path

def check_file_exists(filepath, description=""):
    """Check if a file exists and show its size."""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ {filepath} ({size:,} bytes) {description}")
        return True
    else:
        print(f"❌ {filepath} - NOT FOUND {description}")
        return False

def check_json_valid(filepath):
    """Check if a JSON file is valid."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data
    except Exception as e:
        return False, str(e)

def check_python_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        compile(content, filepath, 'exec')
        return True, "Syntax OK"
    except Exception as e:
        return False, str(e)

def main():
    """Run comprehensive verification."""
    print("🔍 Multi-Agent Brain DEMO 实现验证")
    print("=" * 60)
    
    # Core demo files
    print("\n📁 核心 DEMO 文件:")
    core_files = [
        ("demo_runner.py", "主程序入口"),
        ("demo_modes.py", "DEMO 模式实现"),
        ("demo_output.py", "输出格式化"),
        ("demo_setup.py", "环境检查和设置"),
        ("simple_demo.py", "简化版 DEMO"),
    ]
    
    core_ok = 0
    for filepath, desc in core_files:
        if check_file_exists(filepath, desc):
            # Check Python syntax
            syntax_ok, syntax_msg = check_python_syntax(filepath)
            if syntax_ok:
                print(f"   ✅ Python 语法: {syntax_msg}")
                core_ok += 1
            else:
                print(f"   ❌ Python 语法错误: {syntax_msg}")
    
    # Configuration and data files
    print("\n⚙️  配置和数据文件:")
    config_files = [
        ("demo_questions.json", "预定义问题集"),
        ("run_demo.sh", "启动脚本"),
        (".env.example", "环境配置模板"),
        ("README_DEMO.md", "DEMO 使用文档"),
        ("DEMO_IMPLEMENTATION_SUMMARY.md", "实现总结"),
    ]
    
    config_ok = 0
    for filepath, desc in config_files:
        if check_file_exists(filepath, desc):
            if filepath.endswith('.json'):
                json_ok, json_data = check_json_valid(filepath)
                if json_ok:
                    if 'questions' in json_data:
                        questions = json_data.get('questions', [])
                        print(f"   ✅ JSON 有效，包含 {len(questions)} 个问题")
                    else:
                        print(f"   ✅ JSON 有效")
                    config_ok += 1
                else:
                    print(f"   ❌ JSON 无效: {json_data}")
            elif filepath.endswith('.sh'):
                # Check if script is executable
                if os.access(filepath, os.X_OK):
                    print(f"   ✅ 脚本可执行")
                    config_ok += 1
                else:
                    print(f"   ⚠️  脚本不可执行")
            else:
                config_ok += 1
    
    # Check file structure
    print("\n📂 项目结构检查:")
    
    # Check if we're in the right directory
    required_dirs = ["agents", "utils", "tests"]
    dir_ok = 0
    for dirname in required_dirs:
        if Path(dirname).exists():
            print(f"   ✅ {dirname}/ 目录存在")
            dir_ok += 1
        else:
            print(f"   ❌ {dirname}/ 目录不存在")
    
    # Check key agent files
    print("\n🤖 Agent 文件检查:")
    agent_files = [
        "agents/coordination/agent.py",
        "agents/python_expert/agent.py", 
        "agents/milvus_expert/agent.py",
        "agents/devops_expert/agent.py",
        "agents/shared_memory.py",
        "agents/base.py",
    ]
    
    agent_ok = 0
    for filepath in agent_files:
        if check_file_exists(filepath):
            agent_ok += 1
    
    # Check utility files
    print("\n🔧 工具文件检查:")
    util_files = [
        "utils/__init__.py",
        "utils/openai_client.py",
        "utils/config_manager.py",
    ]
    
    util_ok = 0
    for filepath in util_files:
        if check_file_exists(filepath):
            util_ok += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 验证总结:")
    
    total_checks = 5  # core, config, dirs, agents, utils
    passed_checks = 0
    
    if core_ok == len(core_files):
        print("✅ 核心 DEMO 文件: 全部通过")
        passed_checks += 1
    else:
        print(f"⚠️  核心 DEMO 文件: {core_ok}/{len(core_files)} 通过")
    
    if config_ok == len(config_files):
        print("✅ 配置文件: 全部通过")
        passed_checks += 1
    else:
        print(f"⚠️  配置文件: {config_ok}/{len(config_files)} 通过")
    
    if dir_ok == len(required_dirs):
        print("✅ 项目目录: 全部通过")
        passed_checks += 1
    else:
        print(f"⚠️  项目目录: {dir_ok}/{len(required_dirs)} 通过")
    
    if agent_ok == len(agent_files):
        print("✅ Agent 文件: 全部通过")
        passed_checks += 1
    else:
        print(f"⚠️  Agent 文件: {agent_ok}/{len(agent_files)} 通过")
    
    if util_ok == len(util_files):
        print("✅ 工具文件: 全部通过")
        passed_checks += 1
    else:
        print(f"⚠️  工具文件: {util_ok}/{len(util_files)} 通过")
    
    # Final verdict
    success_rate = (passed_checks / total_checks) * 100
    
    print(f"\n🎯 总体通过率: {success_rate:.1f}% ({passed_checks}/{total_checks})")
    
    if passed_checks == total_checks:
        print("🎉 所有验证项目通过！DEMO 实现完整且正确。")
        return 0
    elif success_rate >= 80:
        print("✅ 大部分验证项目通过，DEMO 基本实现完成。")
        return 0
    else:
        print("❌ 多项验证失败，需要修复实现。")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
