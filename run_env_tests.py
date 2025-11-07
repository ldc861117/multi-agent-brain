#!/usr/bin/env python3
"""Simple test runner for env_config tests."""

import sys
import os
sys.path.insert(0, '.')

def run_test():
    try:
        import pytest
        print("✅ pytest imported successfully")
        
        # Import the test module
        import utils.test_env_config
        print("✅ Test module imported successfully")
        
        # Run pytest on the specific file
        result = pytest.main([
            'utils/test_env_config.py',
            '-v',
            '--tb=short'
        ])
        
        return result == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)