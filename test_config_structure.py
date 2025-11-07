#!/usr/bin/env python3
"""Simple test script to verify the new configuration structure works."""

import os
import sys

def test_basic_import():
    """Test basic imports work."""
    try:
        from utils.openai_client import ChatAPIConfig, EmbeddingAPIConfig, OpenAIConfig, ProviderType
        from utils.config_manager import ConfigManager, get_agent_config
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_legacy_config():
    """Test legacy configuration still works."""
    try:
        # Set legacy environment variables
        os.environ['OPENAI_API_KEY'] = 'sk-test-key'
        os.environ['OPENAI_MODEL'] = 'gpt-4'
        os.environ['EMBEDDING_MODEL'] = 'text-embedding-3-large'
        os.environ['EMBEDDING_DIMENSION'] = '3072'
        
        from utils.openai_client import OpenAIConfig
        config = OpenAIConfig.from_env_with_fallback()
        
        assert config.chat_api.api_key == 'sk-test-key'
        assert config.chat_api.model == 'gpt-4'
        assert config.embedding_api.model == 'text-embedding-3-large'
        assert config.embedding_api.dimension == 3072
        
        # Test legacy properties
        assert config.api_key == 'sk-test-key'
        assert config.default_model == 'gpt-4'
        assert config.embedding_model == 'text-embedding-3-large'
        assert config.embedding_dimension == 3072
        
        print("✅ Legacy configuration test passed")
        return True
    except Exception as e:
        print(f"❌ Legacy config test failed: {e}")
        return False

def test_separate_config():
    """Test separate chat and embedding configuration."""
    try:
        # Clear environment first
        for key in list(os.environ.keys()):
            if key.startswith(('CHAT_API_', 'EMBEDDING_API_', 'OPENAI_')):
                del os.environ[key]
        
        # Set separate configurations
        os.environ['CHAT_API_KEY'] = 'sk-chat-key'
        os.environ['CHAT_API_MODEL'] = 'gpt-4'
        os.environ['EMBEDDING_API_KEY'] = 'sk-embed-key'
        os.environ['EMBEDDING_API_MODEL'] = 'text-embedding-3-small'
        os.environ['EMBEDDING_API_PROVIDER'] = 'ollama'
        os.environ['EMBEDDING_DIMENSION'] = '768'
        
        from utils.openai_client import OpenAIConfig, ProviderType
        config = OpenAIConfig.from_env()
        
        assert config.chat_api.api_key == 'sk-chat-key'
        assert config.chat_api.model == 'gpt-4'
        assert config.embedding_api.api_key == 'sk-embed-key'
        assert config.embedding_api.model == 'text-embedding-3-small'
        assert config.embedding_api.provider == ProviderType.OLLAMA
        assert config.embedding_api.dimension == 768
        
        print("✅ Separate configuration test passed")
        return True
    except Exception as e:
        print(f"❌ Separate config test failed: {e}")
        return False

def test_config_manager():
    """Test configuration manager with agent overrides."""
    try:
        from utils.config_manager import ConfigManager
        
        # Create a test config file
        test_config = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
"""
        with open('test_config.yaml', 'w') as f:
            f.write(test_config)
        
        # Test config manager
        config_manager = ConfigManager('test_config.yaml')
        
        # Set basic environment
        os.environ['OPENAI_API_KEY'] = 'sk-test-key'
        
        # Test agent with override
        config = config_manager.get_agent_config('coordination')
        assert config.chat_api.model == 'gpt-4'
        assert config.embedding_api.model == 'text-embedding-3-large'
        assert config.embedding_api.dimension == 3072
        
        # Test agent without override
        config = config_manager.get_agent_config('python_expert')
        assert config.chat_api.model == 'gpt-3.5-turbo'  # Default
        
        # Clean up
        os.remove('test_config.yaml')
        
        print("✅ Configuration manager test passed")
        return True
    except Exception as e:
        print(f"❌ Config manager test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing new configuration structure...")
    
    tests = [
        test_basic_import,
        test_legacy_config,
        test_separate_config,
        test_config_manager,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Configuration structure is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())