import os
import logging
from typing import List, Any, Optional, Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger(__name__)


class NullLLM:
    """
    Fallback LLM that returns a helpful message when LLM is disabled/unavailable.
    Implements a minimal invoke/ainvoke interface compatible with LangChain chat models.
    """

    def __init__(self, reason: str = "unconfigured"):
        self.is_configured = False
        self.fallback_reason = reason

    def _message_for_reason(self) -> str:
        if self.fallback_reason == "offline":
            return (
                "LLM is disabled (offline mode). "
                "To enable it, set OFFLINE_MODE=false and configure a valid API key."
            )
        if self.fallback_reason == "init_error":
            return (
                "LLM is unavailable (initialization failed). "
                "Please verify your API key, credentials, and provider configuration."
            )
        # unconfigured (default)
        return (
            "LLM unavailable (missing API key). "
            "To enable it, set GOOGLE_API_KEY in your environment."
        )

    def invoke(self, messages: List[BaseMessage]) -> Any:
        return AIMessage(content=self._message_for_reason())

    async def ainvoke(self, messages: List[BaseMessage]) -> Any:
        return self.invoke(messages)


def get_llm(model_name: str = "gemini-3-pro-preview", temperature: float = 0.0):
    """
    Returns an instance of the Google Gemini Chat model, or NullLLM if not configured.
    Never returns None - always returns a usable LLM instance.

    Fallback scenarios:
    1) OFFLINE_MODE=true -> NullLLM("offline")
    2) Missing/invalid API key -> NullLLM("unconfigured")
    3) Provider init error -> NullLLM("init_error")

    Emits (if ENABLE_EVENTS=true):
    - llm_fallback: {reason, provider, auth_mode?, error_type?}
    """
    from app.config.settings import OFFLINE_MODE, ENABLE_EVENTS

    def emit_fallback_event(reason: str, provider: str = "google", extra_data: Optional[Dict] = None) -> None:
        """Emit llm_fallback event if enabled. Must never crash the app."""
        if not ENABLE_EVENTS:
            return
        try:
            from app.core.events import get_emitter
            emitter = get_emitter()

            event_data: Dict[str, Any] = {
                "reason": reason,
                "provider": provider,
            }
            if extra_data:
                event_data.update(extra_data)

            emitter.emit("llm_fallback", event_data)
        except Exception:
            pass  # Events must never crash the app

    if OFFLINE_MODE:
        emit_fallback_event("offline_mode", extra_data={"auth_mode": os.getenv("AUTH_MODE", "dev")})
        return NullLLM(reason="offline")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("ovdje_ide") or api_key.strip() == "":
        emit_fallback_event("missing_api_key")
        return NullLLM(reason="unconfigured")

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,
        )
        llm.is_configured = True
        return llm
    except Exception as e:
        error_type = type(e).__name__
        logger.warning("[LLM] Provider init failed (%s); falling back to NullLLM", error_type)

        emit_fallback_event("provider_init_error", extra_data={"error_type": error_type})
        return NullLLM(reason="init_error")


def is_llm_configured() -> bool:
    """
    Helper function to check if LLM can be used in the current runtime.
    Returns False if OFFLINE_MODE=true.
    """
    try:
        from app.config.settings import OFFLINE_MODE
        if OFFLINE_MODE:
            return False
    except Exception:
        pass

    api_key = os.getenv("GOOGLE_API_KEY")
    return bool(api_key and not api_key.startswith("ovdje_ide") and api_key.strip())
