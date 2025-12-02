"""McKinsey Token Validator for OIDC ID token validation.

This module validates ID tokens from McKinsey's OIDC provider (Keycloak),
including signature verification, claims validation, and user info extraction.
"""

import structlog
from typing import Dict, Optional, List
from datetime import datetime, timezone
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidIssuerError,
    InvalidAudienceError,
)
from backend.services.mckinsey_oidc import McKinseyOIDCProvider
from backend.config import settings

logger = structlog.get_logger()


class McKinseyTokenValidator:
    """Validates McKinsey OIDC ID tokens.

    Performs comprehensive validation including:
    - JWT signature verification using JWKS
    - Issuer validation
    - Audience validation
    - Expiration validation
    - Nonce validation
    - Algorithm whitelist enforcement
    """

    # Allowed signing algorithms (RS256 and ES256 are secure asymmetric algorithms)
    ALLOWED_ALGORITHMS = ["RS256", "ES256"]

    # Expected issuer for McKinsey tokens
    EXPECTED_ISSUER = "https://auth.mckinsey.id/auth/realms/r"

    def __init__(self, provider: McKinseyOIDCProvider):
        """Initialize token validator with OIDC provider.

        Args:
            provider: McKinsey OIDC provider instance for JWKS access
        """
        self.provider = provider
        self._jwks_client: Optional[PyJWKClient] = None

        logger.info(
            "mckinsey_token_validator_initialized",
            jwks_uri=provider.jwks_uri,
            allowed_algorithms=self.ALLOWED_ALGORITHMS,
            expected_issuer=self.EXPECTED_ISSUER,
        )

    def _get_jwks_client(self) -> PyJWKClient:
        """Get or create JWKS client for fetching public keys.

        PyJWKClient handles caching and automatic key rotation.

        Returns:
            PyJWKClient instance configured for McKinsey's JWKS endpoint
        """
        if self._jwks_client is None:
            self._jwks_client = PyJWKClient(
                uri=self.provider.jwks_uri,
                cache_keys=True,
                max_cached_keys=10,
                cache_jwk_set=True,
                lifespan=3600,  # Cache JWKS for 1 hour
            )
            logger.info(
                "jwks_client_created",
                jwks_uri=self.provider.jwks_uri,
                cache_enabled=True,
                lifespan=3600,
            )
        return self._jwks_client

    async def validate_id_token(
        self, id_token: str, nonce: Optional[str] = None
    ) -> Dict:
        """Validate ID token and extract claims.

        Performs comprehensive validation:
        1. Signature verification using JWKS
        2. Algorithm whitelist enforcement
        3. Issuer validation
        4. Audience validation
        5. Expiration validation
        6. Nonce validation (if provided)

        Args:
            id_token: JWT ID token from McKinsey
            nonce: Expected nonce value for replay protection

        Returns:
            Dictionary containing validated claims from the ID token

        Raises:
            InvalidTokenError: If token validation fails
            ExpiredSignatureError: If token has expired
            InvalidSignatureError: If signature verification fails
            InvalidIssuerError: If issuer doesn't match expected value
            InvalidAudienceError: If audience doesn't match client ID
        """
        logger.info(
            "validating_id_token",
            token_preview=id_token[:20] + "...",
            has_nonce=nonce is not None,
        )

        try:
            # Step 1: Verify signature and decode token
            claims = await self.verify_signature(id_token)

            # Step 2: Verify all claims
            await self.verify_claims(claims, nonce)

            # Step 3: Extract user info
            user_info = await self.extract_user_info(claims)

            logger.info(
                "id_token_validation_successful",
                subject=claims.get("sub"),
                email=user_info.get("email"),
                issuer=claims.get("iss"),
            )

            return claims

        except ExpiredSignatureError as e:
            logger.error(
                "id_token_expired",
                error=str(e),
                exp=claims.get("exp") if "claims" in locals() else None,
            )
            raise
        except InvalidSignatureError as e:
            logger.error("id_token_invalid_signature", error=str(e))
            raise
        except InvalidIssuerError as e:
            logger.error(
                "id_token_invalid_issuer",
                error=str(e),
                issuer=claims.get("iss") if "claims" in locals() else None,
                expected_issuer=self.EXPECTED_ISSUER,
            )
            raise
        except InvalidAudienceError as e:
            logger.error(
                "id_token_invalid_audience",
                error=str(e),
                audience=claims.get("aud") if "claims" in locals() else None,
                expected_audience=self.provider.client_id,
            )
            raise
        except InvalidTokenError as e:
            logger.error(
                "id_token_validation_failed", error=str(e), error_type=type(e).__name__
            )
            raise

    async def verify_signature(self, token: str) -> Dict:
        """Verify JWT signature using JWKS public keys.

        Args:
            token: JWT token to verify

        Returns:
            Dictionary containing decoded token claims

        Raises:
            InvalidSignatureError: If signature verification fails
            InvalidTokenError: If token is malformed
        """
        try:
            # Get JWKS client (with caching)
            jwks_client = self._get_jwks_client()

            # Get signing key from JWKS
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify token
            # Note: We only verify signature here, claims are verified separately
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.ALLOWED_ALGORITHMS,
                options={
                    "verify_signature": True,
                    "verify_exp": False,  # We verify expiration separately
                    "verify_aud": False,  # We verify audience separately
                    "verify_iss": False,  # We verify issuer separately
                },
            )

            logger.info(
                "signature_verification_successful",
                algorithm=claims.get("alg"),
                key_id=signing_key.key_id,
            )

            return claims

        except InvalidSignatureError as e:
            logger.error("signature_verification_failed", error=str(e))
            raise
        except InvalidTokenError as e:
            logger.error(
                "token_decode_failed", error=str(e), error_type=type(e).__name__
            )
            raise

    async def verify_claims(self, claims: Dict, nonce: Optional[str] = None) -> bool:
        """Verify all required claims in the ID token.

        Args:
            claims: Decoded token claims
            nonce: Expected nonce value

        Returns:
            True if all claims are valid

        Raises:
            InvalidIssuerError: If issuer is invalid
            InvalidAudienceError: If audience is invalid
            ExpiredSignatureError: If token has expired
            InvalidTokenError: If nonce validation fails or required claims are missing
        """
        # Verify issuer
        issuer = claims.get("iss")
        if issuer != self.EXPECTED_ISSUER:
            logger.error(
                "issuer_validation_failed",
                actual_issuer=issuer,
                expected_issuer=self.EXPECTED_ISSUER,
            )
            raise InvalidIssuerError(
                f"Invalid issuer: expected {self.EXPECTED_ISSUER}, got {issuer}"
            )

        # Verify audience
        audience = claims.get("aud")
        # Audience can be a string or list of strings
        if isinstance(audience, list):
            if self.provider.client_id not in audience:
                logger.error(
                    "audience_validation_failed",
                    actual_audience=audience,
                    expected_audience=self.provider.client_id,
                )
                raise InvalidAudienceError(
                    f"Invalid audience: client_id {self.provider.client_id} not in {audience}"
                )
        else:
            if audience != self.provider.client_id:
                logger.error(
                    "audience_validation_failed",
                    actual_audience=audience,
                    expected_audience=self.provider.client_id,
                )
                raise InvalidAudienceError(
                    f"Invalid audience: expected {self.provider.client_id}, got {audience}"
                )

        # Verify expiration
        exp = claims.get("exp")
        if not exp:
            logger.error("expiration_claim_missing")
            raise InvalidTokenError("Token missing 'exp' claim")

        current_time = datetime.now(timezone.utc).timestamp()
        if current_time >= exp:
            logger.error(
                "token_expired",
                exp=exp,
                current_time=current_time,
                expired_seconds_ago=current_time - exp,
            )
            raise ExpiredSignatureError("Token has expired")

        # Verify nonce if provided
        if nonce:
            token_nonce = claims.get("nonce")
            if not token_nonce:
                logger.error("nonce_claim_missing")
                raise InvalidTokenError("Token missing 'nonce' claim")

            if token_nonce != nonce:
                logger.error(
                    "nonce_validation_failed",
                    expected_nonce=nonce[:10] + "...",
                    actual_nonce=token_nonce[:10] + "...",
                )
                raise InvalidTokenError("Nonce validation failed")

        # Verify required claims are present
        required_claims = ["sub", "iat", "exp"]
        missing_claims = [claim for claim in required_claims if claim not in claims]
        if missing_claims:
            logger.error("required_claims_missing", missing_claims=missing_claims)
            raise InvalidTokenError(f"Token missing required claims: {missing_claims}")

        logger.info(
            "claims_verification_successful",
            issuer=issuer,
            audience=audience,
            subject=claims.get("sub"),
            exp=exp,
        )

        return True

    async def extract_user_info(self, claims: Dict) -> Dict:
        """Extract user information from ID token claims.

        Maps OIDC standard claims and McKinsey-specific claims to user profile fields.

        Standard OIDC claims:
        - sub: Subject (unique user identifier)
        - email: Email address
        - name: Full name
        - given_name: First name
        - family_name: Last name
        - preferred_username: Preferred username

        McKinsey-specific claims (may vary):
        - employee_id: McKinsey employee ID
        - office_location: Office location
        - department: Department

        Args:
            claims: Validated ID token claims

        Returns:
            Dictionary containing extracted user information
        """
        user_info = {
            # Required claims
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            # Optional standard claims
            "name": claims.get("name"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "preferred_username": claims.get("preferred_username"),
            # McKinsey-specific claims (optional)
            "employee_id": claims.get("employee_id"),
            "office_location": claims.get("office_location"),
            "department": claims.get("department"),
            # Token metadata
            "iat": claims.get("iat"),
            "exp": claims.get("exp"),
        }

        # Remove None values
        user_info = {k: v for k, v in user_info.items() if v is not None}

        logger.info(
            "user_info_extracted",
            subject=user_info.get("sub"),
            email=user_info.get("email"),
            has_name=bool(user_info.get("name")),
            has_employee_id=bool(user_info.get("employee_id")),
            num_claims=len(user_info),
        )

        return user_info


# Global validator instance
_mckinsey_validator: Optional[McKinseyTokenValidator] = None


async def get_mckinsey_validator() -> McKinseyTokenValidator:
    """Get or create global McKinsey token validator instance.

    Returns:
        Singleton instance of McKinseyTokenValidator
    """
    global _mckinsey_validator
    if _mckinsey_validator is None:
        from backend.services.mckinsey_oidc import get_mckinsey_provider

        provider = await get_mckinsey_provider()
        _mckinsey_validator = McKinseyTokenValidator(provider)
    return _mckinsey_validator
