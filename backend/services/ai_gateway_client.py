"""
AI Gateway Client
Handles authentication and API calls to the AI Gateway using service account credentials.
"""
import httpx
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
from backend.config import settings

logger = structlog.get_logger()


class AIGatewayClient:
    """
    Client for interacting with the AI Gateway API.
    Uses OAuth2 client credentials flow for service account authentication.
    Supports provider-specific base URLs based on the model being used.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        instance_id: Optional[str] = None,
        env: str = "prod",
        openai_base_url: Optional[str] = None,
        anthropic_base_url: Optional[str] = None,
        base_url: Optional[str] = None,  # Legacy/OAuth token endpoint
        timeout: float = 60.0
    ):
        """
        Initialize AI Gateway client.
        
        Args:
            client_id: Service account client ID
            client_secret: Service account client secret
            instance_id: AI Gateway instance ID (defaults to env var)
            env: Environment (prod, dev, etc.) - defaults to "prod"
            openai_base_url: OpenAI provider base URL (auto-constructed if not provided)
            anthropic_base_url: Anthropic provider base URL (auto-constructed if not provided)
            base_url: Legacy base URL for OAuth token endpoint (defaults to env var)
            timeout: Request timeout in seconds
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.instance_id = instance_id or getattr(settings, 'ai_gateway_instance_id', '1d8095ae-5ef9-4e61-885c-f5b031f505a4')
        self.env = env or getattr(settings, 'ai_gateway_env', 'prod')
        
        # Construct provider-specific base URLs if not provided
        if openai_base_url:
            self.openai_base_url = openai_base_url
        else:
            self.openai_base_url = f"https://openai.{self.env}.ai-gateway.quantumblack.com/{self.instance_id}/v1"
        
        if anthropic_base_url:
            self.anthropic_base_url = anthropic_base_url
        else:
            self.anthropic_base_url = f"https://anthropic.{self.env}.ai-gateway.quantumblack.com/{self.instance_id}"
        
        # OAuth token endpoint (may use general base URL or provider-specific)
        self.base_url = base_url or getattr(settings, 'ai_gateway_base_url', 'https://ai-gateway.quantumblack.com')
        self.timeout = timeout
        
        # Token management
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_lock = None  # Will be initialized lazily
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "ai_gateway_client_initialized",
            instance_id=self.instance_id,
            env=self.env,
            openai_base_url=self.openai_base_url,
            anthropic_base_url=self.anthropic_base_url,
            oauth_base_url=self.base_url
        )
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True
            )
        return self._client
    
    async def _get_token_lock(self):
        """Get token lock for thread-safe token management."""
        if self._token_lock is None:
            import asyncio
            self._token_lock = asyncio.Lock()
        return self._token_lock
    
    async def _get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.
        Uses OAuth2 client credentials flow.
        """
        # Check if we have a valid token
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at - timedelta(seconds=60):  # Refresh 1 min before expiry
                return self._access_token
        
        # Acquire lock to prevent concurrent token requests
        lock = await self._get_token_lock()
        async with lock:
            # Double-check after acquiring lock
            if self._access_token and self._token_expires_at:
                if datetime.utcnow() < self._token_expires_at - timedelta(seconds=60):
                    return self._access_token
            
            # Request new token
            # OAuth token endpoint: try different paths and authentication methods
            client = await self._get_http_client()
            
            # Try different OAuth endpoint paths
            oauth_paths = [
                "/oauth/token",
                "/oauth2/token", 
                "/token",
                "/auth/token"
            ]
            
            from httpx import BasicAuth
            import base64
            last_error = None
            response = None
            
            for path in oauth_paths:
                # Construct token URL - try OpenAI provider base without /v1
                oauth_base = self.openai_base_url.replace('/v1', '')
                token_url = f"{oauth_base}{path}"
                
                # Try 1: Bearer token with client_id:client_secret directly (as provided in API key format)
                try:
                    credentials = f"{self.client_id}:{self.client_secret}"
                    response = await client.post(
                        token_url,
                        data={"grant_type": "client_credentials"},
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Accept": "application/json",
                            "Authorization": f"Bearer {credentials}"
                        }
                    )
                    response.raise_for_status()
                    break  # Success!
                except httpx.HTTPStatusError as e1:
                    last_error = e1
                    # Try 1b: Bearer token with base64 encoded credentials
                    try:
                        encoded_creds = base64.b64encode(credentials.encode()).decode()
                        response = await client.post(
                            token_url,
                            data={"grant_type": "client_credentials"},
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded",
                                "Accept": "application/json",
                                "Authorization": f"Bearer {encoded_creds}"
                            }
                        )
                        response.raise_for_status()
                        break  # Success!
                    except httpx.HTTPStatusError as e1b:
                        last_error = e1b
                    # Try 2: Basic Auth with grant_type in body
                    try:
                        auth = BasicAuth(self.client_id, self.client_secret)
                        response = await client.post(
                            token_url,
                            data={"grant_type": "client_credentials"},
                            auth=auth,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded",
                                "Accept": "application/json"
                            }
                        )
                        response.raise_for_status()
                        break  # Success!
                    except httpx.HTTPStatusError as e2:
                        last_error = e2
                        # Try 3: Credentials in body, no auth header
                        try:
                            response = await client.post(
                                token_url,
                                data={
                                    "grant_type": "client_credentials",
                                    "client_id": self.client_id,
                                    "client_secret": self.client_secret,
                                },
                                headers={
                                    "Content-Type": "application/x-www-form-urlencoded",
                                    "Accept": "application/json"
                                }
                            )
                            response.raise_for_status()
                            break  # Success!
                        except httpx.HTTPStatusError as e3:
                            last_error = e3
                            continue
                except Exception as e:
                    last_error = e
                    continue
            
            if response is None or not response.is_success:
                if last_error:
                    error_msg = str(last_error)
                    if hasattr(last_error, 'response'):
                        error_msg = f"{last_error.response.status_code}: {last_error.response.text[:200]}"
                    logger.error("ai_gateway_token_request_failed", error=error_msg)
                    raise Exception(f"Failed to obtain AI Gateway access token: {error_msg}")
                raise Exception("Failed to find working OAuth endpoint")
            
            # Parse token response
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
            
            logger.info("ai_gateway_token_refreshed", expires_in=expires_in)
            return self._access_token
    
    def _get_provider_base_url(self, model: str) -> str:
        """
        Determine the provider-specific base URL based on the model.
        
        Args:
            model: Model identifier (e.g., 'gpt-5.1', 'claude-3-sonnet')
            
        Returns:
            Provider-specific base URL
        """
        model_lower = model.lower()
        # OpenAI models (gpt-*)
        if model_lower.startswith('gpt-') or 'openai' in model_lower:
            return self.openai_base_url
        # Anthropic models (claude-*)
        elif model_lower.startswith('claude-') or 'anthropic' in model_lower:
            return self.anthropic_base_url
        # Default to OpenAI for unknown models
        else:
            logger.warning("ai_gateway_unknown_model_provider", model=model, defaulting_to="openai")
            return self.openai_base_url
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from the AI Gateway.
        Uses OpenAI endpoint for listing models.
        
        Returns:
            List of model dictionaries with model information
        """
        token = await self._get_access_token()
        client = await self._get_http_client()
        
        try:
            # Use OpenAI endpoint for listing models
            response = await client.get(
                f"{self.openai_base_url}/models",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except httpx.HTTPStatusError as e:
            logger.error(
                "ai_gateway_list_models_failed",
                status_code=e.response.status_code,
                response_text=e.response.text[:200]
            )
            raise Exception(f"Failed to list AI Gateway models: {e.response.status_code}")
        except Exception as e:
            logger.error("ai_gateway_list_models_error", error=str(e))
            raise
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion using the AI Gateway.
        
        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-3-sonnet', 'gpt-5.1')
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate (for older models)
            max_completion_tokens: Maximum completion tokens (for GPT-5.1 models)
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            Completion response dictionary
        """
        token = await self._get_access_token()
        client = await self._get_http_client()
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        # GPT-5.1 models use max_completion_tokens, others use max_tokens
        if max_completion_tokens is not None:
            payload["max_completion_tokens"] = max_completion_tokens
        elif max_tokens:
            payload["max_tokens"] = max_tokens
        
        if stream:
            payload["stream"] = True
        
        # Add any additional parameters
        payload.update(kwargs)
        
        # Determine provider-specific base URL based on model
        provider_base_url = self._get_provider_base_url(model)
        
        try:
            response = await client.post(
                f"{provider_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            
            # Handle streaming response
            if stream:
                # Return async generator for streaming
                async def stream_generator():
                    try:
                        async for line in response.aiter_lines():
                            if line.strip():
                                # Parse SSE format (data: {...})
                                if line.startswith("data: "):
                                    data_str = line[6:]  # Remove "data: " prefix
                                    if data_str.strip() == "[DONE]":
                                        break
                                    try:
                                        import json
                                        chunk = json.loads(data_str)
                                        yield chunk
                                    except json.JSONDecodeError:
                                        logger.warning("ai_gateway_invalid_json_chunk", line=data_str[:100])
                                elif line.startswith("{"):
                                    # Try to parse as JSON directly (non-SSE format)
                                    try:
                                        import json
                                        chunk = json.loads(line)
                                        yield chunk
                                    except json.JSONDecodeError:
                                        logger.warning("ai_gateway_invalid_json_line", line=line[:100])
                    except Exception as e:
                        logger.error("ai_gateway_stream_error", error=str(e))
                        raise
                
                return stream_generator()
            else:
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "ai_gateway_chat_completion_failed",
                model=model,
                status_code=e.response.status_code,
                response_text=e.response.text[:500]
            )
            raise Exception(f"AI Gateway chat completion failed: {e.response.status_code}")
        except Exception as e:
            logger.error("ai_gateway_chat_completion_error", model=model, error=str(e))
            raise
    
    async def verify_credentials(self) -> bool:
        """
        Verify that the service account credentials are valid.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            await self._get_access_token()
            # Try to list models as a verification step
            await self.list_models()
            return True
        except Exception as e:
            logger.warning("ai_gateway_credentials_verification_failed", error=str(e))
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

