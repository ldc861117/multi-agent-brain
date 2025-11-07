#!/usr/bin/env python3
"""Direct shared memory test without package imports."""

import sys
import os
sys.path.insert(0, os.getcwd())

def test_shared_memory_directly():
    """Test shared memory without importing the full agents package."""
    try:
        print("Testing direct imports...")
        
        # Import utils directly
        from utils.config_manager import get_agent_config
        from utils.openai_client import get_openai_client, OpenAIClientWrapper
        print("✅ Utils direct imports successful")
        
        # Import shared memory directly
        from agents.shared_memory import SharedMemory
        print("✅ SharedMemory direct import successful")
        
        # Test creating SharedMemory with agent_name parameter
        memory = SharedMemory(agent_name="test")
        print("✅ SharedMemory instance created with agent_name")
        
        # Test health check
        health = memory.health_check()
        print(f"✅ Health check: {health}")
        
        print("✅ All direct tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_shared_memory_directly()
    sys.exit(0 if success else 1)