"""McKinsey OIDC Provider Manager for SSO authentication.

This module manages McKinsey's OIDC provider configuration and operations,
including authorization URL generation, token exchange, and token refresh.
McKinsey uses Keycloak as their identity provider.
"""

import structlog
from typing import Dict, List, Optional
from urllib.parse import urlencode
import httpx
from backend.config import settings

logger = structlog.get_logger()


class McKinseyOIDCProvider:
    """Manages mckinsey.id OIDC provider configuration and operations.

    McKinsey's identity provider (auth.mckinsey.id) is based on Keycloak.
    This class handles OAuth 2.0 / OIDC Authorization Code Flow operations.
    """

    def __init__(self):
        """Initialize McKinsey OIDC provider with configuration from settings."""
        self.client_id: str = settings.mckinsey_client_id
        self.client_secret: str = settings.mckinsey_client_secret
        self.authorization_endpoint: str = settings.mckinsey_authorization_endpoint
        self.token_endpoint: str = settings.mckinsey_token_endpoint
        self.redirect_uri: str = settings.mckinsey_redirect_uri
        self.scopes: List[str] = ["openid", "profile", "email"]

        # McKinsey uses Keycloak, so JWKS endpoint follows Keycloak pattern
        # Format: https://auth.mckinsey.id/auth/realms/{realm}/protocol/openid-connect/certs
        self.jwks_uri: str = (
            "https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/certs"
        )

        # HTTP client for token operations
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "mckinsey_oidc_provider_initialized",
            client_id=self.client_id,
            authorization_endpoint=self.authorization_endpoint,
            token_endpoint=self.token_endpoint,
            redirect_uri=self.redirect_uri,
            jwks_uri=self.jwks_uri,
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for token operations."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._http_client

    async def get_authorization_url(self, state: str, nonce: str) -> str:
        """Generate authorization URL for McKinsey SSO login.

        Args:
            state: CSRF protection token
            nonce: Token replay protection value

        Returns:
            Complete authorization URL with all required parameters

        Example:
            https://auth.mckinsey.id/auth/realms/r/protocol/openid-connect/auth?
            client_id=...&redirect_uri=...&response_type=code&scope=openid+profile+email&
            state=...&nonce=...
        """
        # Validate required configuration
        if not self.client_id or not self.client_id.strip():
            logger.error(
                "mckinsey_client_id_missing",
                client_id=self.client_id,
                has_client_id=bool(self.client_id),
            )
            raise ValueError(
                "McKinsey SSO client ID is not configured. Please set MCKINSEY_CLIENT_ID environment variable."
            )
        
        if not self.redirect_uri or not self.redirect_uri.strip():
            logger.error(
                "mckinsey_redirect_uri_missing",
                redirect_uri=self.redirect_uri,
                has_redirect_uri=bool(self.redirect_uri),
            )
            raise ValueError(
                "McKinsey SSO redirect URI is not configured. Please set MCKINSEY_REDIRECT_URI environment variable."
            )
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "nonce": nonce,
        }

        authorization_url = f"{self.authorization_endpoint}?{urlencode(params)}"

        logger.info(
            "authorization_url_generated",
            state=state[:10] + "...",
            nonce=nonce[:10] + "...",
            scopes=self.scopes,
        )

        return authorization_url

    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """Exchange authorization code for access token, ID token, and refresh token.

        Args:
            code: Authorization code from McKinsey callback

        Returns:
            Dictionary containing:
                - access_token: Access token for API calls
                - id_token: JWT containing user identity information
                - refresh_token: Token for obtaining new access tokens
                - expires_in: Token expiration time in seconds
                - token_type: Token type (usually "Bearer")

        Raises:
            httpx.HTTPStatusError: If token exchange fails
            httpx.RequestError: If network request fails
        """
        client = await self._get_http_client()

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        logger.info(
            "exchanging_authorization_code",
            code=code[:10] + "...",
            token_endpoint=self.token_endpoint,
        )

        try:
            response = await client.post(
                self.token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            tokens = response.json()

            logger.info(
                "token_exchange_successful",
                has_access_token=bool(tokens.get("access_token")),
                has_id_token=bool(tokens.get("id_token")),
                has_refresh_token=bool(tokens.get("refresh_token")),
                expires_in=tokens.get("expires_in"),
            )

            return tokens

        except httpx.HTTPStatusError as e:
            logger.error(
                "token_exchange_failed",
                status_code=e.response.status_code,
                error=str(e),
                response_body=e.response.text,
            )
            raise
        except httpx.RequestError as e:
            logger.error("token_exchange_request_failed", error=str(e))
            raise

    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            Dictionary containing:
                - access_token: New access token
                - id_token: New ID token (may be included)
                - refresh_token: New refresh token (may be rotated)
                - expires_in: Token expiration time in seconds
                - token_type: Token type (usually "Bearer")

        Raises:
            httpx.HTTPStatusError: If token refresh fails
            httpx.RequestError: If network request fails
        """
        client = await self._get_http_client()

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        logger.info(
            "refreshing_access_token",
            refresh_token=refresh_token[:10] + "...",
            token_endpoint=self.token_endpoint,
        )

        try:
            response = await client.post(
                self.token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            tokens = response.json()

            logger.info(
                "token_refresh_successful",
                has_access_token=bool(tokens.get("access_token")),
                has_id_token=bool(tokens.get("id_token")),
                has_refresh_token=bool(tokens.get("refresh_token")),
                expires_in=tokens.get("expires_in"),
            )

            return tokens

        except httpx.HTTPStatusError as e:
            logger.error(
                "token_refresh_failed",
                status_code=e.response.status_code,
                error=str(e),
                response_body=e.response.text,
            )
            raise
        except httpx.RequestError as e:
            logger.error("token_refresh_request_failed", error=str(e))
            raise

    async def get_jwks(self) -> Dict:
        """Fetch JSON Web Key Set (JWKS) from McKinsey's Keycloak.

        JWKS contains public keys used to verify JWT signatures.

        Returns:
            Dictionary containing JWKS with keys array

        Raises:
            httpx.HTTPStatusError: If JWKS fetch fails
            httpx.RequestError: If network request fails
        """
        client = await self._get_http_client()

        logger.info("fetching_jwks", jwks_uri=self.jwks_uri)

        try:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()

            jwks = response.json()

            logger.info("jwks_fetch_successful", num_keys=len(jwks.get("keys", [])))

            return jwks

        except httpx.HTTPStatusError as e:
            logger.error(
                "jwks_fetch_failed",
                status_code=e.response.status_code,
                error=str(e),
                response_body=e.response.text,
            )
            raise
        except httpx.RequestError as e:
            logger.error("jwks_fetch_request_failed", error=str(e))
            raise

    async def close(self):
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("mckinsey_oidc_provider_closed")


# Global provider instance
_mckinsey_provider: Optional[McKinseyOIDCProvider] = None


async def get_mckinsey_provider() -> McKinseyOIDCProvider:
    """Get or create global McKinsey OIDC provider instance.

    Returns:
        Singleton instance of McKinseyOIDCProvider
    """
    global _mckinsey_provider
    if _mckinsey_provider is None:
        _mckinsey_provider = McKinseyOIDCProvider()
    return _mckinsey_provider
