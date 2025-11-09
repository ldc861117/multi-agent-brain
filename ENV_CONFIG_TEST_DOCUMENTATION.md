# .env Configuration Test Suite Documentation

## Overview

The `tests/test_env_config.py` file provides comprehensive test coverage for .env configuration setup, validating all aspects of environment variable loading and configuration for separated chat and embedding API endpoints.

## Test Coverage Areas

### 1. Environment Variable Loading
- ✅ Load variables from .env file successfully
- ✅ Handle missing .env gracefully (use defaults)
- ✅ Verify all required variables are present

### 2. Chat API Configuration
- ✅ Correct base URL parsing
- ✅ API key loading with precedence (CHAT_API_KEY > OPENAI_API_KEY)
- ✅ Provider type validation (openai, ollama, custom)
- ✅ Model name resolution with fallbacks

### 3. Embedding API Configuration
- ✅ Separate endpoint handling
- ✅ Optional API key (empty string for Ollama)
- ✅ Provider type validation
- ✅ Model name resolution and dimension detection

### 4. Fallback Behavior
- ✅ When EMBEDDING_API_* not set, falls back to CHAT_API_*
- ✅ Legacy OPENAI_* variables work as fallback
- ✅ Precedence: specific vars > legacy vars > defaults

### 5. Per-Agent Overrides
- ✅ Agent-specific model overrides from config.yaml
- ✅ Override precedence (agent config > global config > defaults)
- ✅ Invalid agent names handled gracefully

### 6. Provider Support
- ✅ Test Ollama provider (empty key allowed)
- ✅ Test OpenAI provider (key required)
- ✅ Test custom provider
- ✅ Test Cohere provider (as custom)
- ✅ Invalid provider types rejected

### 7. Edge Cases
- ✅ Empty strings handled correctly
- ✅ Whitespace trimming in URLs
- ✅ Case sensitivity of provider names
- ✅ Malformed URLs detected (passed through, client validates)

## Test Structure

### Test Classes

1. **TestEnvironmentVariableLoading** - Tests basic environment variable loading
2. **TestChatAPIConfiguration** - Tests chat API specific configuration
3. **TestEmbeddingAPIConfiguration** - Tests embedding API specific configuration
4. **TestFallbackBehavior** - Tests fallback mechanisms
5. **TestPerAgentOverrides** - Tests per-agent configuration overrides
6. **TestProviderSupport** - Tests different provider configurations
7. **TestEdgeCases** - Tests edge cases and error conditions
8. **TestIntegration** - Integration tests for complete scenarios
9. **TestPerformanceAndReliability** - Performance and caching tests
10. **TestConfigurationValidation** - Parameter validation tests

### Fixtures

- **clean_env** - Provides clean environment variable isolation
- **mock_load_dotenv** - Prevents actual .env file loading during tests
- **temp_config_file** - Creates temporary config files for testing

## Running the Tests

### Basic Test Execution

```bash
# Run all .env configuration tests
pytest tests/test_env_config.py -v

# Run specific test class
pytest tests/test_env_config.py::TestChatAPIConfiguration -v

# Run specific test method
pytest tests/test_env_config.py::TestChatAPIConfiguration::test_api_key_loading -v

# Run with coverage (also writes coverage.xml + htmlcov/)
make cov
```

### Verification

```bash
# Quick overview of key test files
python -m tests.tools.verify_tests

# Check test compilation
python -m py_compile tests/test_env_config.py
```

## Test Examples

### Example 1: Basic Configuration Loading

```python
def test_load_variables_from_env_success(self, clean_env, mock_load_dotenv):
    """Test successful loading of all required variables."""
    # Set up environment variables
    clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
    clean_env.setenv("CHAT_API_MODEL", "gpt-4")
    clean_env.setenv("EMBEDDING_API_KEY", "sk-embed-key")
    clean_env.setenv("EMBEDDING_API_MODEL", "text-embedding-3-large")
    
    # Load configuration
    config = OpenAIConfig.from_env_with_fallback()
    
    # Verify configuration
    assert config.chat_api.api_key == "sk-chat-key"
    assert config.chat_api.model == "gpt-4"
    assert config.embedding_api.api_key == "sk-embed-key"
    assert config.embedding_api.model == "text-embedding-3-large"
```

### Example 2: Provider Validation

```python
def test_ollama_provider_empty_key_allowed(self, clean_env, mock_load_dotenv):
    """Test Ollama provider allows empty API key."""
    clean_env.setenv("CHAT_API_KEY", "sk-chat-key")
    clean_env.setenv("EMBEDDING_API_PROVIDER", "ollama")
    clean_env.setenv("EMBEDDING_API_KEY", "")  # Empty string
    
    config = EmbeddingAPIConfig.from_env()
    
    # Empty string should be preserved for ollama
    assert config.api_key == ""
    assert config.provider == ProviderType.OLLAMA
```

### Example 3: Per-Agent Overrides

```python
def test_agent_specific_model_overrides_from_env(self, clean_env, temp_config_file, mock_load_dotenv):
    """Test agent-specific model overrides from config file."""
    # Create config file with agent overrides
    config_content = """
api_config:
  agent_overrides:
    coordination:
      chat_model: "gpt-4"
      embedding_model: "text-embedding-3-large"
      embedding_dimension: 3072
"""
    temp_config_file.write_text(config_content)
    
    # Set environment variables
    clean_env.setenv("CHAT_API_KEY", "sk-test-key")
    
    # Test agent-specific configs
    config_manager = ConfigManager(str(temp_config_file))
    coord_config = config_manager.get_agent_config("coordination")
    
    assert coord_config.chat_api.model == "gpt-4"
    assert coord_config.embedding_api.model == "text-embedding-3-large"
    assert coord_config.embedding_api.dimension == 3072
```

## Configuration Scenarios Tested

### 1. Complete Separated Configuration
```bash
CHAT_API_KEY=sk-chat-key
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_MODEL=gpt-4
EMBEDDING_API_KEY=sk-embed-key
EMBEDDING_API_BASE_URL=https://api.embed.com/v1
EMBEDDING_API_MODEL=text-embedding-3-large
```

### 2. Local Ollama Configuration
```bash
CHAT_API_KEY=ollama
CHAT_API_BASE_URL=http://localhost:11434/v1
CHAT_API_MODEL=qwen2:7b
CHAT_API_PROVIDER=ollama
EMBEDDING_API_KEY=ollama
EMBEDDING_API_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_MODEL=nomic-embed-text
EMBEDDING_API_PROVIDER=ollama
EMBEDDING_DIMENSION=768
```

### 3. Mixed Provider Configuration
```bash
# OpenAI for chat
CHAT_API_KEY=sk-openai-key
CHAT_API_BASE_URL=https://api.openai.com/v1
CHAT_API_PROVIDER=openai

# Ollama for embedding
EMBEDDING_API_KEY=ollama
EMBEDDING_API_BASE_URL=http://localhost:11434/v1
EMBEDDING_API_PROVIDER=ollama
```

### 4. Legacy Configuration
```bash
OPENAI_API_KEY=sk-legacy-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-3-small
```

## Expected Test Results

When all tests pass, you should see output similar to:

```
============================= test session starts ==============================
collected 50 items

utils/test_env_config.py::TestEnvironmentVariableLoading::test_load_variables_from_env_success PASSED
utils/test_env_config.py::TestEnvironmentVariableLoading::test_handle_missing_env_gracefully PASSED
utils/test_env_config.py::TestEnvironmentVariableLoading::test_required_variables_present_validation PASSED
utils/test_env_config.py::TestEnvironmentVariableLoading::test_legacy_variables_fallback PASSED
...
utils/test_env_config.py::TestConfigurationValidation::test_numeric_parameter_validation PASSED
utils/test_env_config.py::TestConfigurationValidation::test_boolean_parameter_handling PASSED

============================== 50 passed in 2.34s ==============================
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all required modules are installed
2. **Environment Variable Conflicts**: Tests use `monkeypatch` to isolate environment
3. **File Permission Issues**: Ensure test files are readable
4. **Missing .env.example**: Copy from project root if needed

### Debug Mode

```bash
# Run with detailed output
pytest utils/test_env_config.py -v -s --tb=long

# Run specific failing test
pytest utils/test_env_config.py::TestClassName::test_method_name -v -s
```

## Integration with CI/CD

These tests are designed to integrate with existing CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run .env configuration tests
  run: |
    python -m pytest utils/test_env_config.py -v --junitxml=test-results.xml
```

## Maintenance

When adding new configuration options:

1. Add corresponding test methods to appropriate test classes
2. Update the `clean_env` fixture with new variable names
3. Update this documentation with new test coverage
4. Verify all tests pass with new .env.example

## Related Files

- `utils/openai_client.py` - Core configuration classes
- `utils/config_manager.py` - Configuration manager with agent overrides
- `config.yaml` - Agent-specific override configuration
- `.env.example` - Example environment configuration
- `utils/test_openai_client.py` - OpenAI client tests (complementary)