from __future__ import annotations

from threading import Lock
from typing import List, Optional

from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from backend.config import settings


class ProviderRegistry:
    """Centralized registry for AI provider credentials and clients."""

    def __init__(self):
        self._lock = Lock()
        # Strip whitespace and ensure non-empty strings
        self._openai_key: Optional[str] = (settings.openai_api_key.strip() if settings.openai_api_key else None) or None
        self._claude_key: Optional[str] = (settings.anthropic_api_key.strip() if settings.anthropic_api_key else None) or None
        self._gemini_key: Optional[str] = (settings.google_api_key.strip() if settings.google_api_key else None) or None

        self._openai_client: Optional[OpenAI] = None
        self._claude_client: Optional[Anthropic] = None
        self._gemini_configured: bool = False

        self._rebuild_clients()

    def _rebuild_clients(self) -> None:
        """Rebuild provider clients from current keys. Can be called to refresh clients after keys are updated."""
        # Only create clients if keys are non-empty after stripping
        self._openai_client = None
        if self._openai_key and self._openai_key.strip():
            try:
                self._openai_client = OpenAI(api_key=self._openai_key.strip())
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("openai_client_creation_failed", error=str(e))
                self._openai_client = None
        
        self._claude_client = None
        if self._claude_key and self._claude_key.strip():
            try:
                self._claude_client = Anthropic(api_key=self._claude_key.strip())
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("claude_client_creation_failed", error=str(e))
                self._claude_client = None
        
        self._gemini_configured = False
        if self._gemini_key and self._gemini_key.strip():
            try:
                genai.configure(api_key=self._gemini_key.strip())
                self._gemini_configured = True
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("gemini_client_creation_failed", error=str(e))
                self._gemini_configured = False

    def update_keys(
        self,
        *,
        openai_key: Optional[str] = None,
        claude_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
    ) -> List[str]:
        """
        Update provider API keys and rebuild clients. None means 'no change'.
        If a key is provided, it overrides the .env key. If None, keeps existing value.
        If empty string, clears the key (falls back to .env if available).
        """
        with self._lock:
            if openai_key is not None:
                # If empty string, fall back to .env key, otherwise use provided key
                if openai_key.strip():
                    self._openai_key = openai_key.strip()
                else:
                    # Empty string means clear user override, fall back to .env
                    self._openai_key = (settings.openai_api_key.strip() if settings.openai_api_key else None) or None
            if claude_key is not None:
                if claude_key.strip():
                    self._claude_key = claude_key.strip()
                else:
                    self._claude_key = (settings.anthropic_api_key.strip() if settings.anthropic_api_key else None) or None
            if gemini_key is not None:
                if gemini_key.strip():
                    self._gemini_key = gemini_key.strip()
                else:
                    self._gemini_key = (settings.google_api_key.strip() if settings.google_api_key else None) or None

            self._rebuild_clients()

        return self.get_configured_providers()

    def get_openai_client(self) -> Optional[OpenAI]:
        return self._openai_client

    def get_claude_client(self) -> Optional[Anthropic]:
        return self._claude_client

    def has_gemini_key(self) -> bool:
        return self._gemini_configured

    def has_openai_key(self) -> bool:
        return self._openai_client is not None

    def has_claude_key(self) -> bool:
        return self._claude_client is not None

    def get_configured_providers(self) -> List[str]:
        providers: List[str] = []
        if self.has_openai_key():
            providers.append("openai")
        if self.has_claude_key():
            providers.append("claude")
        if self.has_gemini_key():
            providers.append("gemini")
        return providers

    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return self._openai_key
    
    def get_claude_key(self) -> Optional[str]:
        """Get Claude API key."""
        return self._claude_key
    
    def get_gemini_key(self) -> Optional[str]:
        """Get Gemini API key."""
        return self._gemini_key


provider_registry = ProviderRegistry()

