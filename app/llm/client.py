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
    
    def __init__(self, reason: str = "unconfigured"):
        self.is_configured = False
        self.fallback_reason = reason
    
    def invoke(self, messages: List[BaseMessage]) -> Any:
        """Return a helpful message instead of processing the request."""
        class MockResponse:
            def __init__(self, reason: str):
                if reason == "offline":
                    self.content = "LLM unavailable (offline mode). To enable, configure API key and disable offline mode."
                elif reason == "init_error":
                    self.content = "LLM unavailable (initialization failed). Check API key and credentials."
                else:
                    self.content = "LLM unavailable (offline mode). To enable, configure API key."
        
        return MockResponse(self.fallback_reason)
    
    async def ainvoke(self, messages: List[BaseMessage]) -> Any:
        """Async version of invoke."""
        return self.invoke(messages)


def get_llm(model_name: str = "gemini-3-pro-preview", temperature: float = 0.0):
    """
    Returns an instance of the Google Gemini Chat model, or NullLLM if not configured.
    Never returns None - always returns a usable LLM instance.
    
    Fallback scenarios (no crash, safe NullLLM):
    1. OFFLINE_MODE=true → NullLLM with "offline" reason
    2. Missing/invalid API key → NullLLM with "unconfigured" reason
    3. Provider init error → NullLLM with "init_error" reason
    
    Events emitted (if ENABLE_EVENTS=true):
    - llm_fallback: {reason, provider, auth_mode (optional)}
    """
    from app.config.settings import OFFLINE_MODE, ENABLE_EVENTS
    
    # Safe event emission helper (never crashes)
    def emit_fallback_event(reason: str, provider: str = "google", extra_data: dict = None):
        """Emit llm_fallback event if events are enabled (fail-safe)."""
        if not ENABLE_EVENTS:
            return
        
        try:
            from app.core.events import get_emitter
            emitter = get_emitter()
            
            event_data = {
                "reason": reason,
                "provider": provider,
            }
            
            # Add optional auth_mode (safe - never log secrets)
            if extra_data:
                event_data.update(extra_data)
            
            emitter.emit("llm_fallback", event_data)
        except Exception:
            # Events must never crash the app
            pass
    
    # Scenario 1: OFFLINE_MODE is true
    if OFFLINE_MODE:
        emit_fallback_event("offline_mode", extra_data={"auth_mode": os.getenv("AUTH_MODE", "dev")})
        return NullLLM(reason="offline")
    
    # Scenario 2: Missing or invalid API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("ovdje_ide") or api_key.strip() == "":
        emit_fallback_event("missing_api_key")
        return NullLLM(reason="unconfigured")
    
    # Scenario 3: Provider initialization (wrapped in try/except)
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
        # Log error without exposing secrets
        error_type = type(e).__name__
        print(f"[LLM] Provider init failed ({error_type}), falling back to NullLLM")
        
        emit_fallback_event("provider_init_error", extra_data={"error_type": error_type})
        return NullLLM(reason="init_error")


def is_llm_configured() -> bool:
    """
    Helper function to check if LLM is properly configured.
    Returns True if GOOGLE_API_KEY is set and valid.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    return bool(api_key and not api_key.startswith("ovdje_ide") and api_key.strip())
