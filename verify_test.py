#!/usr/bin/env python3
"""Basic verification of the env_config test file."""

import sys
import os
sys.path.insert(0, '.')

def verify_test_file():
    """Verify the test file structure and imports."""
    try:
        # Check if file exists
        if not os.path.exists('utils/test_env_config.py'):
            print("❌ Test file does not exist")
            return False
        
        print("✅ Test file exists")
        
        # Try to import required modules
        import pytest
        print("✅ pytest imported")
        
        import os
        from unittest.mock import Mock, patch, MagicMock
        print("✅ unittest.mock imported")
        
        # Try to import our modules
        from utils.openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType
        print("✅ openai_client modules imported")
        
        from utils.config_manager import ConfigManager, get_config_manager, get_agent_config
        print("✅ config_manager modules imported")
        
        # Try to compile the test file
        with open('utils/test_env_config.py', 'r') as f:
            test_code = f.read()
        
        compile(test_code, 'utils/test_env_config.py', 'exec')
        print("✅ Test file compiles successfully")
        
        # Count test classes and methods
        test_classes = []
        test_methods = []
        
        for line in test_code.split('\n'):
            line = line.strip()
            if line.startswith('class Test') and '(' in line:
                class_name = line.split('(')[0].replace('class ', '')
                test_classes.append(class_name)
            elif line.startswith('def test_') and '(' in line:
                method_name = line.split('(')[0].replace('def test_', '')
                test_methods.append(method_name)
        
        print(f"✅ Found {len(test_classes)} test classes:")
        for cls in test_classes:
            print(f"   - {cls}")
        
        print(f"✅ Found {len(test_methods)} test methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying test file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_test_file()
    print(f"\n{'✅ Verification successful' if success else '❌ Verification failed'}")