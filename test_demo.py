#!/usr/bin/env python3
"""
Simple test to verify demo components can be imported.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all demo components can be imported."""
    print("🔍 测试 DEMO 组件导入...")
    
    try:
        # Test demo modules
        print("  • demo_setup...")
        import demo_setup
        
        print("  • demo_output...")
        import demo_output
        
        print("  • demo_modes...")
        import demo_modes
        
        print("  • demo_runner...")
        import demo_runner
        
        print("✅ 所有 DEMO 组件导入成功")
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_questions_file():
    """Test that demo questions file exists and is valid JSON."""
    print("\n🔍 测试问题文件...")
    
    questions_file = Path("demo_questions.json")
    
    if not questions_file.exists():
        print("❌ demo_questions.json 不存在")
        return False
    
    try:
        import json
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        questions = questions_data.get("questions", [])
        print(f"✅ 问题文件有效，包含 {len(questions)} 个问题")
        return True
        
    except Exception as e:
        print(f"❌ 问题文件解析失败: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 DEMO 组件测试")
    print("=" * 40)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test questions file
    if not test_questions_file():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())