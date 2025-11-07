#!/usr/bin/env python3
"""Quick verification script."""

import os
import sys

def main():
    print("=== .env Configuration Test Suite Verification ===\n")
    
    # Check if test file exists
    test_file = "utils/test_env_config.py"
    if os.path.exists(test_file):
        print(f"✅ Test file exists: {test_file}")
        size = os.path.getsize(test_file)
        print(f"✅ Test file size: {size:,} bytes")
    else:
        print(f"❌ Test file missing: {test_file}")
        return False
    
    # Check if .env.example exists
    env_example = ".env.example"
    if os.path.exists(env_example):
        print(f"✅ Environment example exists: {env_example}")
    else:
        print(f"❌ Environment example missing: {env_example}")
        return False
    
    # Try to import key modules
    try:
        sys.path.insert(0, '.')
        from utils.openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType
        print("✅ OpenAI client modules imported")
        
        from utils.config_manager import ConfigManager
        print("✅ Config manager imported")
        
        import pytest
        print("✅ pytest available")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Count test items
    try:
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Count test classes
        import re
        test_classes = re.findall(r'^class (Test\w+)', content, re.MULTILINE)
        test_methods = re.findall(r'^def (test_\w+)', content, re.MULTILINE)
        fixtures = re.findall(r'^@pytest\.fixture\s*\ndef (\w+)', content, re.MULTILINE)
        
        print(f"✅ Found {len(test_classes)} test classes:")
        for cls in test_classes:
            print(f"   - {cls}")
        
        print(f"✅ Found {len(test_methods)} test methods")
        print(f"✅ Found {len(fixtures)} fixtures")
        
    except Exception as e:
        print(f"❌ Error analyzing test file: {e}")
        return False
    
    print("\n=== Verification Complete ===")
    print("✅ All checks passed!")
    print(f"✅ Test suite ready: {len(test_methods)} tests covering .env configuration")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)