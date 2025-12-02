"""
Token encryption service for McKinsey SSO refresh tokens.

This module provides Fernet-based symmetric encryption for securely storing
McKinsey refresh tokens in Redis. Fernet guarantees that a message encrypted
using it cannot be manipulated or read without the key.

Requirements: 3.4
"""

from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import structlog
from backend.config import settings

logger = structlog.get_logger(__name__)


class TokenEncryptionError(Exception):
    """Raised when token encryption or decryption fails."""

    pass


class TokenEncryptionService:
    """
    Service for encrypting and decrypting McKinsey refresh tokens.

    Uses Fernet symmetric encryption (AES 128 in CBC mode with HMAC for authentication).
    The encryption key must be a 32-byte URL-safe base64-encoded string.

    Example:
        service = TokenEncryptionService()
        encrypted = service.encrypt_token("my_refresh_token")
        decrypted = service.decrypt_token(encrypted)
        assert decrypted == "my_refresh_token"
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the token encryption service.

        Args:
            encryption_key: Optional 32-byte URL-safe base64-encoded encryption key.
                          If not provided, loads from settings.mckinsey_token_encryption_key.

        Raises:
            TokenEncryptionError: If encryption key is missing or invalid.
        """
        self._encryption_key = encryption_key or settings.mckinsey_token_encryption_key

        if not self._encryption_key:
            logger.error(
                "token_encryption_key_missing",
                message="MCKINSEY_TOKEN_ENCRYPTION_KEY environment variable not set",
            )
            raise TokenEncryptionError(
                "Token encryption key not configured. "
                "Set MCKINSEY_TOKEN_ENCRYPTION_KEY environment variable."
            )

        try:
            # Validate the key by attempting to create a Fernet instance
            self._fernet = Fernet(self._encryption_key.encode("utf-8"))
            logger.info(
                "token_encryption_initialized",
                message="Token encryption service initialized successfully",
            )
        except Exception as e:
            logger.error(
                "token_encryption_init_failed",
                error=str(e),
                message="Failed to initialize Fernet cipher",
            )
            raise TokenEncryptionError(
                f"Invalid encryption key format. Key must be a 32-byte URL-safe base64-encoded string. "
                f"Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            ) from e

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a McKinsey refresh token.

        Args:
            token: The plaintext refresh token to encrypt.

        Returns:
            str: The encrypted token as a URL-safe base64-encoded string.

        Raises:
            TokenEncryptionError: If encryption fails.

        Example:
            encrypted = service.encrypt_token("my_refresh_token")
        """
        if not token:
            raise TokenEncryptionError("Cannot encrypt empty token")

        try:
            encrypted_bytes = self._fernet.encrypt(token.encode("utf-8"))
            encrypted_token = encrypted_bytes.decode("utf-8")

            logger.debug(
                "token_encrypted",
                token_length=len(token),
                encrypted_length=len(encrypted_token),
            )

            return encrypted_token
        except Exception as e:
            logger.error(
                "token_encryption_failed",
                error=str(e),
                message="Failed to encrypt token",
            )
            raise TokenEncryptionError(f"Token encryption failed: {str(e)}") from e

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a McKinsey refresh token.

        Args:
            encrypted_token: The encrypted token (URL-safe base64-encoded string).

        Returns:
            str: The decrypted plaintext token.

        Raises:
            TokenEncryptionError: If decryption fails (invalid token or wrong key).

        Example:
            decrypted = service.decrypt_token(encrypted_token)
        """
        if not encrypted_token:
            raise TokenEncryptionError("Cannot decrypt empty token")

        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_token.encode("utf-8"))
            decrypted_token = decrypted_bytes.decode("utf-8")

            logger.debug(
                "token_decrypted",
                encrypted_length=len(encrypted_token),
                decrypted_length=len(decrypted_token),
            )

            return decrypted_token
        except InvalidToken as e:
            logger.error(
                "token_decryption_invalid",
                error=str(e),
                message="Invalid token or wrong encryption key",
            )
            raise TokenEncryptionError(
                "Token decryption failed: Invalid token or wrong encryption key"
            ) from e
        except Exception as e:
            logger.error(
                "token_decryption_failed",
                error=str(e),
                message="Failed to decrypt token",
            )
            raise TokenEncryptionError(f"Token decryption failed: {str(e)}") from e


# Global instance for convenience
_token_encryption_service: Optional[TokenEncryptionService] = None


def get_token_encryption_service() -> TokenEncryptionService:
    """
    Get or create the global token encryption service instance.

    Returns:
        TokenEncryptionService: The global token encryption service.

    Raises:
        TokenEncryptionError: If service initialization fails.
    """
    global _token_encryption_service

    if _token_encryption_service is None:
        _token_encryption_service = TokenEncryptionService()

    return _token_encryption_service


def encrypt_refresh_token(token: str) -> str:
    """
    Convenience function to encrypt a refresh token using the global service.

    Args:
        token: The plaintext refresh token to encrypt.

    Returns:
        str: The encrypted token.

    Raises:
        TokenEncryptionError: If encryption fails.
    """
    service = get_token_encryption_service()
    return service.encrypt_token(token)


def decrypt_refresh_token(encrypted_token: str) -> str:
    """
    Convenience function to decrypt a refresh token using the global service.

    Args:
        encrypted_token: The encrypted token.

    Returns:
        str: The decrypted plaintext token.

    Raises:
        TokenEncryptionError: If decryption fails.
    """
    service = get_token_encryption_service()
    return service.decrypt_token(encrypted_token)
