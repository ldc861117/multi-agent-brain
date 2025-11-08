#!/usr/bin/env python3
"""Simple test script for verbose configuration functionality."""

import sys
import os
sys.path.insert(0, '.')

# Mock the dependencies that aren't available
class MockSharedMemory:
    def __init__(self, agent_name=None):
        pass

class MockOpenAIClientWrapper:
    def __init__(self, config=None):
        pass

# Mock the imports
sys.modules['agents.shared_memory'] = type(sys)('mock_module')
sys.modules['agents.shared_memory'].SharedMemory = MockSharedMemory
sys.modules['utils.openai_client'] = type(sys)('mock_module')
sys.modules['utils.openai_client'].OpenAIClientWrapper = MockOpenAIClientWrapper

# Mock loguru
class MockLogger:
    def bind(self, **kwargs):
        return self
    def info(self, msg, **kwargs):
        print(f"INFO: {msg}")
    def error(self, msg, **kwargs):
        print(f"ERROR: {msg}")

sys.modules['loguru'] = type(sys)('mock_module')
sys.modules['loguru'].logger = MockLogger()

# Now import the config manager
from utils.config_manager import ConfigManager


def test_verbose_configuration():
    """Test verbose configuration functionality."""
    print("Testing verbose configuration...")
    
    # Create a temporary config file
    test_config = {
        'api_config': {
            'agent_overrides': {
                'coordination': {
                    'answer_verbose': True
                },
                'python_expert': {
                    'answer_verbose': False
                }
            }
        }
    }
    
    # Write temporary config
    import yaml
    with open('test_config.yaml', 'w') as f:
        yaml.dump(test_config, f)
    
    try:
        # Test ConfigManager with the test config
        config_manager = ConfigManager('test_config.yaml')
        
        # Test coordination agent verbose setting
        coordination_verbose = config_manager.get_agent_answer_verbose('coordination')
        print(f"Coordination verbose: {coordination_verbose}")
        assert coordination_verbose == True, f"Expected True, got {coordination_verbose}"
        
        # Test python_expert verbose setting
        python_verbose = config_manager.get_agent_answer_verbose('python_expert')
        print(f"Python expert verbose: {python_verbose}")
        assert python_verbose == False, f"Expected False, got {python_verbose}"
        
        # Test default for agent not in config
        default_verbose = config_manager.get_agent_answer_verbose('unknown_agent')
        print(f"Unknown agent verbose (should default to False): {default_verbose}")
        assert default_verbose == False, f"Expected False, got {default_verbose}"
        
        print("All verbose configuration tests passed! ✓")
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False
    
    finally:
        # Clean up
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')


if __name__ == "__main__":
    success = test_verbose_configuration()
    if not success:
        exit(1)