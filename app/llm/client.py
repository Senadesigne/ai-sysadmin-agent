import os
from typing import List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage

# Environment variables are loaded in app.config.settings


class NullLLM:
    """
    Fallback LLM that returns a helpful message when no API key is configured.
    Implements the same interface as ChatGoogleGenerativeAI for compatibility.
    """
    
    def __init__(self):
        self.is_configured = False
    
    def invoke(self, messages: List[BaseMessage]) -> Any:
        """Return a helpful message instead of processing the request."""
        class MockResponse:
            def __init__(self):
                self.content = "LLM is not configured. Set GOOGLE_API_KEY in .env to enable AI responses."
        
        return MockResponse()
    
    async def ainvoke(self, messages: List[BaseMessage]) -> Any:
        """Async version of invoke."""
        return self.invoke(messages)

def get_llm(model_name: str = "gemini-3-pro-preview", temperature: float = 0.0):
    """
    Returns an instance of the Google Gemini Chat model, or NullLLM if not configured.
    Never returns None - always returns a usable LLM instance.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("ovdje_ide") or api_key.strip() == "":
        print("INFO: GOOGLE_API_KEY not configured, using NullLLM fallback")
        return NullLLM()

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        llm.is_configured = True
        return llm
    except Exception as e:
        print(f"ERROR: Failed to initialize Google LLM: {e}")
        print("Falling back to NullLLM")
        return NullLLM()


def is_llm_configured() -> bool:
    """
    Helper function to check if LLM is properly configured.
    Returns True if GOOGLE_API_KEY is set and valid.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    return bool(api_key and not api_key.startswith("ovdje_ide") and api_key.strip())
