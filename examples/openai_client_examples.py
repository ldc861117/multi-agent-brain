"""Example usage of the OpenAI client wrapper.

This module demonstrates how to use the OpenAI client wrapper
in various scenarios within the multi-agent system.
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.openai_client import (
    OpenAIConfig,
    OpenAIClientWrapper,
    ChatMessage,
    get_openai_client,
)


def example_basic_usage():
    """Example of basic OpenAI client usage."""
    print("=== Basic Usage Example ===")
    
    # Set up environment variables for demo
    os.environ["OPENAI_API_KEY"] = "sk-demo-key"
    
    # Get the global client (loads from environment)
    client = get_openai_client()
    
    # Simple chat completion example (won't actually call API with demo key)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! How are you?"}
    ]
    
    print(f"Chat completion with {len(messages)} messages:")
    for msg in messages:
        print(f"  {msg['role']}: {msg['content']}")
    
    # Simple embedding example
    print(f"\\nEmbedding example for text: 'Hello, world!'")
    print("This would generate a 1536-dimensional embedding vector.")


def example_with_custom_config():
    """Example of using custom configuration."""
    print("\\n=== Custom Configuration Example ===")
    
    # Create custom config for DeepSeek (as example)
    config = OpenAIConfig(
        api_key="your-deepseek-api-key",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        embedding_model="text-embedding-3-small",
        max_retries=5,
        timeout=60
    )
    
    client = OpenAIClientWrapper(config)
    
    # Use ChatMessage objects for type safety
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="What is the capital of France?")
    ]
    
    print(f"Custom config with base_url: {config.base_url}")
    print(f"Using model: {config.default_model}")
    print(f"Chat message objects: {len(messages)} messages")


def example_batch_embeddings():
    """Example of batch embedding generation."""
    print("\\n=== Batch Embeddings Example ===")
    
    client = get_openai_client()
    
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Artificial intelligence is transforming the world.",
        "Python is a versatile programming language.",
        "Machine learning requires good data.",
        "OpenAI provides powerful language models."
    ]
    
    print(f"Batch embedding for {len(texts)} texts:")
    for i, text in enumerate(texts, 1):
        print(f"  {i}. {text}")
    
    total_chars = sum(len(text) for text in texts)
    print(f"Total characters: {total_chars}")
    print("This would generate 5 embedding vectors of 1536 dimensions each.")


def example_agent_integration():
    """Example of how an agent might use the OpenAI client."""
    print("\\n=== Agent Integration Example ===")
    
    class SimpleAgent:
        """Example agent that uses the OpenAI client."""
        
        def __init__(self, name: str, system_prompt: str):
            self.name = name
            self.system_prompt = system_prompt
            self.client = get_openai_client()
            self.conversation_history = []
        
        def process_message(self, user_message: str) -> str:
            """Process a user message and generate a response."""
            
            # Add system message if this is the first message
            if not self.conversation_history:
                self.conversation_history.append({
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Add user message
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # In a real implementation, this would call the API
            print(f"Agent {self.name} would process:")
            print(f"  System: {self.system_prompt}")
            print(f"  User: {user_message}")
            print(f"  Conversation history: {len(self.conversation_history)} messages")
            
            # Simulate a response
            response = f"I understand you said: '{user_message}'. This is {self.name}'s response."
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
        
        def get_memory_embedding(self, text: str) -> list:
            """Get embedding for memory storage."""
            print(f"Generating embedding for memory: '{text}'")
            # In real implementation, this would call:
            # embeddings = self.client.get_embedding_vector(text)
            # return embeddings[0]
            return [0.1, 0.2, 0.3]  # Dummy embedding
    
    # Create a simple agent
    agent = SimpleAgent(
        name="HelpfulAssistant",
        system_prompt="You are a helpful and friendly assistant. Be concise and helpful."
    )
    
    # Simulate a conversation
    conversation = [
        "Hello! Can you help me understand Python?",
        "What are the main features of Python?",
        "Can you give me a simple example?"
    ]
    
    for user_msg in conversation:
        print(f"\\nUser: {user_msg}")
        response = agent.process_message(user_msg)
        print(f"Agent: {response}")
        print("-" * 50)
    
    # Example of generating embeddings for memory
    memory_text = "Python is a high-level, interpreted programming language."
    embedding = agent.get_memory_embedding(memory_text)
    print(f"\\nMemory embedding dimension: {len(embedding)}")


def example_error_handling():
    """Example of error handling patterns."""
    print("\\n=== Error Handling Example ===")
    
    from utils.openai_client import OpenAIError
    
    # Example of how to handle errors in real usage
    def safe_api_call(client, messages):
        """Example of safe API call with error handling."""
        try:
            # This would be the actual API call:
            # response = client.get_chat_completion(messages)
            # return response.choices[0].message.content
            
            # For demo, just show the pattern
            print("Making API call with error handling...")
            return "Simulated successful response"
            
        except OpenAIError as e:
            print(f"OpenAI client error: {e}")
            if e.original_error:
                print(f"Original error: {e.original_error}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    # Test the error handling
    messages = [{"role": "user", "content": "Hello"}]
    result = safe_api_call(get_openai_client(), messages)
    print(f"Result: {result}")


def main():
    """Run all examples."""
    print("OpenAI Client Wrapper Usage Examples")
    print("=" * 50)
    print("Note: These are demonstration examples that show the API patterns.")
    print("To make actual API calls, set a real OPENAI_API_KEY environment variable.")
    print()
    
    # Set up demo environment
    os.environ["OPENAI_API_KEY"] = "sk-demo-key"
    
    example_basic_usage()
    example_with_custom_config()
    example_batch_embeddings()
    example_agent_integration()
    example_error_handling()
    
    print("\\n" + "=" * 50)
    print("Examples completed!")
    print("\\nTo use with real API calls:")
    print("1. Set OPENAI_API_KEY environment variable")
    print("2. Optionally set OPENAI_BASE_URL for custom providers")
    print("3. Import and use the client in your agents")


if __name__ == "__main__":
    main()