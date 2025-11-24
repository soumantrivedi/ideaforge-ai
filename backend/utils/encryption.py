"""Encryption utilities for API keys using Fernet (symmetric encryption)."""
import os
import base64
from cryptography.fernet import Fernet
from typing import Optional
import structlog

logger = structlog.get_logger()


class APIKeyEncryption:
    """Encrypt and decrypt API keys using Fernet symmetric encryption."""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        # In production, this should be set via environment variable
        encryption_key = os.getenv("API_KEY_ENCRYPTION_KEY")
        
        if not encryption_key:
            # Generate a key if not set (for development only)
            # In production, this MUST be set via environment variable
            logger.warning("API_KEY_ENCRYPTION_KEY not set, generating temporary key (not secure for production)")
            encryption_key = Fernet.generate_key().decode()
            os.environ["API_KEY_ENCRYPTION_KEY"] = encryption_key
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        # Fernet requires a 32-byte key, base64-encoded
        # If the key is not in the right format, generate from it
        try:
            self.cipher = Fernet(encryption_key)
        except ValueError:
            # Key format is wrong, derive a proper key from it
            import hashlib
            key_hash = hashlib.sha256(encryption_key).digest()
            self.cipher = Fernet(base64.urlsafe_b64encode(key_hash))
    
    def encrypt(self, api_key: str) -> str:
        """Encrypt an API key."""
        if not api_key:
            return ""
        try:
            encrypted = self.cipher.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise ValueError(f"Failed to encrypt API key: {e}")
    
    def decrypt(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
        if not encrypted_key:
            return ""
        try:
            decrypted = self.cipher.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise ValueError(f"Failed to decrypt API key: {e}")


# Global instance
_encryption = None


def get_encryption() -> APIKeyEncryption:
    """Get the global encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = APIKeyEncryption()
    return _encryption

