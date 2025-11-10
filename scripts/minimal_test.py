#!/usr/bin/env python3
"""Minimal shared memory test."""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    print("=== Minimal Shared Memory Test ===")
    
    try:
        # Step 1: Test utils imports
        print("1. Testing utils imports...")
        from utils.config_manager import get_agent_config
        from utils.openai_client import get_openai_client, OpenAIClientWrapper
        print("   ✅ Utils imports successful")
        
        # Step 2: Test shared memory imports
        print("2. Testing SharedMemory imports...")
        # Import shared memory components directly without going through agents package
        sys.path.insert(0, os.path.join(project_root, 'agents'))
        from shared_memory import SharedMemory
        print("   ✅ SharedMemory import successful")
        
        # Step 3: Test creating SharedMemory
        print("3. Testing SharedMemory creation...")
        memory = SharedMemory(agent_name="test")
        print("   ✅ SharedMemory instance created")
        
        # Step 4: Test basic functionality
        print("4. Testing basic functionality...")
        health = memory.health_check()
        print(f"   ✅ Health check: {health}")
        
        print("\n=== All Tests Passed! ===")
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("This indicates the import fix may not be working correctly.")
        return False
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)