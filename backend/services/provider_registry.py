from __future__ import annotations

from threading import Lock
from typing import List, Optional
import random
import os

from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from backend.config import settings
from backend.services.ai_gateway_client import AIGatewayClient


class ProviderRegistry:
    """Centralized registry for AI provider credentials and clients.
    
    Supports multiple OpenAI API keys for rate limiting - keys are rotated
    using round-robin or random selection to distribute load.
    """

    def __init__(self):
        self._lock = Lock()
        # Strip whitespace and ensure non-empty strings
        self._openai_key: Optional[str] = (settings.openai_api_key.strip() if settings.openai_api_key else None) or None
        self._claude_key: Optional[str] = (settings.anthropic_api_key.strip() if settings.anthropic_api_key else None) or None
        self._gemini_key: Optional[str] = (settings.google_api_key.strip() if settings.google_api_key else None) or None
        
        # Multiple OpenAI API keys support (for rate limiting)
        # Parse OPENAI_API_KEYS (comma-separated) or use single OPENAI_API_KEY
        self._openai_keys: List[str] = []
        self._openai_key_index: int = 0  # For round-robin selection
        self._load_openai_keys()
        
        # AI Gateway credentials (service account)
        self._ai_gateway_client_id: Optional[str] = (getattr(settings, 'ai_gateway_client_id', None) or "").strip() or None
        self._ai_gateway_client_secret: Optional[str] = (getattr(settings, 'ai_gateway_client_secret', None) or "").strip() or None

        self._openai_client: Optional[OpenAI] = None
        self._claude_client: Optional[Anthropic] = None
        self._gemini_configured: bool = False
        self._ai_gateway_client: Optional[AIGatewayClient] = None

        self._rebuild_clients()
    
    def _load_openai_keys(self) -> None:
        """Load OpenAI API keys from environment variables.
        
        Supports:
        - OPENAI_API_KEY: Single key (backward compatible)
        - OPENAI_API_KEYS: Comma-separated list of keys (for rate limiting)
        """
        # Check for multiple keys first (OPENAI_API_KEYS)
        openai_keys_env = os.getenv("OPENAI_API_KEYS", "").strip()
        if openai_keys_env:
            # Parse comma-separated keys
            keys = [key.strip().strip('"').strip("'") for key in openai_keys_env.split(",")]
            self._openai_keys = [key for key in keys if key and key.startswith("sk-")]
            if self._openai_keys:
                # Use first key as primary for backward compatibility
                self._openai_key = self._openai_keys[0]
                return
        
        # Fall back to single OPENAI_API_KEY
        if self._openai_key:
            self._openai_keys = [self._openai_key]
        else:
            self._openai_keys = []

    def _rebuild_clients(self) -> None:
        """Rebuild provider clients from current keys. Can be called to refresh clients after keys are updated."""
        # Only create clients if keys are non-empty after stripping
        # For OpenAI, we create a client with the primary key (first in list)
        self._openai_client = None
        if self._openai_keys:
            primary_key = self._openai_keys[0].strip()
            if primary_key:
                try:
                    self._openai_client = OpenAI(api_key=primary_key)
                except Exception as e:
                    import structlog
                    logger = structlog.get_logger()
                    logger.warning("openai_client_creation_failed", error=str(e))
                    self._openai_client = None
        elif self._openai_key and self._openai_key.strip():
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
        
        # Rebuild AI Gateway client (only if enabled)
        self._ai_gateway_client = None
        ai_gateway_enabled = getattr(settings, 'ai_gateway_enabled', False)
        # Check if AI Gateway is enabled (can be bool True, string "true", or "1")
        if isinstance(ai_gateway_enabled, str):
            ai_gateway_enabled = ai_gateway_enabled.lower() in ('true', '1', 'yes')
        
        if ai_gateway_enabled and self._ai_gateway_client_id and self._ai_gateway_client_secret:
            try:
                # Get provider-specific base URLs and instance ID
                instance_id = getattr(settings, 'ai_gateway_instance_id', None)
                env = getattr(settings, 'ai_gateway_env', 'prod')
                openai_base_url = getattr(settings, 'ai_gateway_openai_base_url', None)
                anthropic_base_url = getattr(settings, 'ai_gateway_anthropic_base_url', None)
                base_url = getattr(settings, 'ai_gateway_base_url', None)  # For OAuth token endpoint
                
                self._ai_gateway_client = AIGatewayClient(
                    client_id=self._ai_gateway_client_id,
                    client_secret=self._ai_gateway_client_secret,
                    instance_id=instance_id,
                    env=env,
                    openai_base_url=openai_base_url,
                    anthropic_base_url=anthropic_base_url,
                    base_url=base_url
                )
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("ai_gateway_client_creation_failed", error=str(e))
                self._ai_gateway_client = None

    def update_keys(
        self,
        *,
        openai_key: Optional[str] = None,
        claude_key: Optional[str] = None,
        gemini_key: Optional[str] = None,
        ai_gateway_client_id: Optional[str] = None,
        ai_gateway_client_secret: Optional[str] = None,
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
                    # Update keys list if single key provided
                    if not self._openai_keys:
                        self._openai_keys = [self._openai_key]
                    elif len(self._openai_keys) == 1:
                        self._openai_keys[0] = self._openai_key
                else:
                    # Empty string means clear user override, fall back to .env
                    self._openai_key = (settings.openai_api_key.strip() if settings.openai_api_key else None) or None
                    self._load_openai_keys()  # Reload keys from environment
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
            
            # Update AI Gateway credentials
            if ai_gateway_client_id is not None:
                if ai_gateway_client_id.strip():
                    self._ai_gateway_client_id = ai_gateway_client_id.strip()
                else:
                    self._ai_gateway_client_id = (getattr(settings, 'ai_gateway_client_id', None) or "").strip() or None
            if ai_gateway_client_secret is not None:
                if ai_gateway_client_secret.strip():
                    self._ai_gateway_client_secret = ai_gateway_client_secret.strip()
                else:
                    self._ai_gateway_client_secret = (getattr(settings, 'ai_gateway_client_secret', None) or "").strip() or None

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
        if self.has_ai_gateway():
            providers.append("ai_gateway")
        return providers

    def get_openai_key(self, strategy: str = "round_robin") -> Optional[str]:
        """Get OpenAI API key with rotation support for rate limiting.
        
        Args:
            strategy: "round_robin" (default) or "random" for key selection
        
        Returns:
            An OpenAI API key, rotated if multiple keys are available
        """
        if not self._openai_keys:
            return self._openai_key
        
        if len(self._openai_keys) == 1:
            return self._openai_keys[0]
        
        # Multiple keys available - rotate
        with self._lock:
            if strategy == "random":
                return random.choice(self._openai_keys)
            else:  # round_robin (default)
                key = self._openai_keys[self._openai_key_index]
                self._openai_key_index = (self._openai_key_index + 1) % len(self._openai_keys)
                return key
    
    def get_openai_keys_count(self) -> int:
        """Get the number of available OpenAI API keys."""
        return len(self._openai_keys) if self._openai_keys else (1 if self._openai_key else 0)
    
    def get_claude_key(self) -> Optional[str]:
        """Get Claude API key."""
        return self._claude_key
    
    def get_gemini_key(self) -> Optional[str]:
        """Get Gemini API key."""
        return self._gemini_key
    
    def has_ai_gateway(self) -> bool:
        """Check if AI Gateway is configured and enabled."""
        ai_gateway_enabled = getattr(settings, 'ai_gateway_enabled', False)
        # Check if AI Gateway is enabled (can be bool True, string "true", or "1")
        if isinstance(ai_gateway_enabled, str):
            ai_gateway_enabled = ai_gateway_enabled.lower() in ('true', '1', 'yes')
        return ai_gateway_enabled and self._ai_gateway_client is not None
    
    def get_ai_gateway_client(self) -> Optional[AIGatewayClient]:
        """Get AI Gateway client."""
        return self._ai_gateway_client
    
    def get_ai_gateway_client_id(self) -> Optional[str]:
        """Get AI Gateway client ID."""
        return self._ai_gateway_client_id
    
    def get_ai_gateway_client_secret(self) -> Optional[str]:
        """Get AI Gateway client secret."""
        return self._ai_gateway_client_secret
    
    def reload_from_environment(self) -> List[str]:
        """
        Reload API keys from environment variables (Settings).
        Useful when environment variables are updated after module initialization.
        """
        with self._lock:
            # Reload from settings (which reads from os.getenv)
            import os
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            google_key = os.getenv("GOOGLE_API_KEY", "").strip()
            ai_gateway_client_id = os.getenv("AI_GATEWAY_CLIENT_ID", "").strip()
            ai_gateway_client_secret = os.getenv("AI_GATEWAY_CLIENT_SECRET", "").strip()
            
            # Remove quotes if present
            if openai_key.startswith('"') and openai_key.endswith('"'):
                openai_key = openai_key[1:-1]
            if anthropic_key.startswith('"') and anthropic_key.endswith('"'):
                anthropic_key = anthropic_key[1:-1]
            if google_key.startswith('"') and google_key.endswith('"'):
                google_key = google_key[1:-1]
            if ai_gateway_client_id.startswith('"') and ai_gateway_client_id.endswith('"'):
                ai_gateway_client_id = ai_gateway_client_id[1:-1]
            if ai_gateway_client_secret.startswith('"') and ai_gateway_client_secret.endswith('"'):
                ai_gateway_client_secret = ai_gateway_client_secret[1:-1]
            
            # Update keys if they're different
            if openai_key and openai_key != self._openai_key:
                self._openai_key = openai_key
                self._load_openai_keys()  # Reload keys (handles multiple keys)
            if anthropic_key and anthropic_key != self._claude_key:
                self._claude_key = anthropic_key
            if google_key and google_key != self._gemini_key:
                self._gemini_key = google_key
            if ai_gateway_client_id and ai_gateway_client_id != self._ai_gateway_client_id:
                self._ai_gateway_client_id = ai_gateway_client_id
            if ai_gateway_client_secret and ai_gateway_client_secret != self._ai_gateway_client_secret:
                self._ai_gateway_client_secret = ai_gateway_client_secret
            
            # Rebuild clients with updated keys
            self._rebuild_clients()
        
        return self.get_configured_providers()


provider_registry = ProviderRegistry()

