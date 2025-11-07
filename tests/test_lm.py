import pytest
from dotenv import load_dotenv
from utils.openai_client import get_openai_client, reset_openai_client

def test_language_model():
    """
    Tests the language model features of the OpenAI client.
    """
    # Force override of environment variables with .env file
    load_dotenv(override=True)
    
    # Reset the client to ensure the new environment variables are loaded
    reset_openai_client()
    
    # Get the OpenAI client
    client = get_openai_client()

    # Test chat completion
    try:
        chat_response = client.get_chat_completion(
            messages=[{"role": "user", "content": "What is the capital of France?"}],
            max_tokens=10
        )
        assert chat_response.choices[0].message.content
        print(f"Chat completion response: {chat_response.choices[0].message.content}")
    except Exception as e:
        pytest.fail(f"Chat completion failed with error: {e}")
