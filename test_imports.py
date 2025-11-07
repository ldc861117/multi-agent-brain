#!/usr/bin/env python3
"""Test import fix."""

import sys
sys.path.insert(0, '.')

def test_imports():
    try:
        print("Testing imports...")
        
        # Test utils imports
        from utils import get_agent_config, get_openai_client, OpenAIClientWrapper
        print("✅ utils imports successful")
        
        # Test shared memory imports
        from agents.shared_memory import AsyncSharedMemory, EmbeddingCache, MemoryMetrics, SharedMemory
        print("✅ shared_memory imports successful")
        
        # Test coordination agent imports
        from agents.coordination.agent import CoordinationAgent
        print("✅ coordination agent imports successful")
        
        print("✅ All imports working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)