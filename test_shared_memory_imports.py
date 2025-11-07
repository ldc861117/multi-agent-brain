#!/usr/bin/env python3
"""Test shared memory imports directly."""

import sys
import os
sys.path.insert(0, os.getcwd())

def main():
    print("Testing shared memory imports...")
    
    try:
        # Test utils imports first
        from utils import get_agent_config, get_openai_client, OpenAIClientWrapper
        print("✅ Utils imports successful")
        
        # Test shared memory imports
        from agents.shared_memory import AsyncSharedMemory, EmbeddingCache, MemoryMetrics, SharedMemory
        print("✅ SharedMemory imports successful")
        
        # Test creating a SharedMemory instance
        memory = SharedMemory()
        print("✅ SharedMemory instance created successfully")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)