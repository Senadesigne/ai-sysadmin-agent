"""
Capability State Management for AI SysAdmin Agent

This module provides centralized capability checking for the application,
determining what features are available based on configuration and environment.
"""

import os
from typing import Dict, Any
from app.config import settings


class CapabilityState:
    """
    Centralized capability state management.
    
    Determines what features are available based on configuration,
    environment variables, and system state.
    """
    
    def __init__(self):
        """Initialize capability state by checking configuration and environment."""
        self._offline_mode = getattr(settings, 'OFFLINE_MODE', False)
        self._execution_enabled = getattr(settings, 'EXECUTION_ENABLED', False)
        self._rag_enabled = getattr(settings, 'RAG_ENABLED', False)
        
        # Cache capability states
        self._capabilities = self._evaluate_capabilities()
    
    def _evaluate_capabilities(self) -> Dict[str, bool]:
        """Evaluate all capability states."""
        capabilities = {}
        
        # LLM availability - check for API key conservatively
        capabilities['llm'] = self._check_llm_availability()
        
        # RAG availability - based on RAG_ENABLED flag and offline mode
        capabilities['rag'] = self._check_rag_availability()
        
        # Execution availability - based on EXECUTION_ENABLED flag and offline mode
        capabilities['execution'] = self._check_execution_availability()
        
        # Persistence availability - always True for now (Commit 8 will handle failure boundaries)
        capabilities['persistence'] = True
        
        return capabilities
    
    def _check_llm_availability(self) -> bool:
        """Check if LLM is available based on configuration."""
        if self._offline_mode:
            return False
            
        # Conservative check for Google API key
        api_key = os.getenv("GOOGLE_API_KEY")
        return bool(api_key and not api_key.startswith("ovdje_ide") and api_key.strip())
    
    def _check_rag_availability(self) -> bool:
        """Check if RAG is available based on configuration."""
        if self._offline_mode:
            return False
            
        # RAG requires both the flag to be enabled AND a valid API key for embeddings
        if not self._rag_enabled:
            return False
            
        # RAG uses the same Google API key for embeddings
        api_key = os.getenv("GOOGLE_API_KEY")
        return bool(api_key and not api_key.startswith("ovdje_ide") and api_key.strip())
    
    def _check_execution_availability(self) -> bool:
        """Check if execution is available based on configuration."""
        if self._offline_mode:
            return False
            
        return self._execution_enabled
    
    def is_llm_available(self) -> bool:
        """Check if LLM functionality is available."""
        return self._capabilities.get('llm', False)
    
    def is_rag_available(self) -> bool:
        """Check if RAG functionality is available."""
        return self._capabilities.get('rag', False)
    
    def is_execution_available(self) -> bool:
        """Check if command execution functionality is available."""
        return self._capabilities.get('execution', False)
    
    def is_persistence_available(self) -> bool:
        """Check if persistence functionality is available."""
        return self._capabilities.get('persistence', True)
    
    def get_status_message(self) -> str:
        """
        Get a concise status message for the UI.
        
        Returns:
            A brief English status string showing capability states.
        """
        if self._offline_mode:
            return "Status: Offline Mode - Limited functionality available"
        
        # Build status indicators
        chat_status = "OK Chat" if True else "NO Chat"  # Chat UI is always available
        llm_status = "OK LLM" if self.is_llm_available() else "NO LLM"
        rag_status = "OK RAG" if self.is_rag_available() else "NO RAG"
        exec_status = "OK Execution" if self.is_execution_available() else "NO Execution"
        
        return f"Status: {chat_status} | {llm_status} | {rag_status} | {exec_status}"
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed status information for debugging or advanced UI.
        
        Returns:
            Dictionary with detailed capability information.
        """
        return {
            'offline_mode': self._offline_mode,
            'capabilities': self._capabilities.copy(),
            'settings': {
                'execution_enabled': self._execution_enabled,
                'rag_enabled': self._rag_enabled,
            },
            'environment': {
                'has_google_api_key': bool(os.getenv("GOOGLE_API_KEY")),
            }
        }
