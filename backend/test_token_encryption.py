"""
Tests for token encryption service.

This test file verifies the basic functionality of the token encryption service
to ensure it can encrypt and decrypt tokens correctly.
"""

import pytest
from cryptography.fernet import Fernet
from backend.services.token_encryption import (
    TokenEncryptionService,
    TokenEncryptionError,
    encrypt_refresh_token,
    decrypt_refresh_token,
)


def test_token_encryption_round_trip():
    """Test that encrypting and decrypting a token returns the original value."""
    # Generate a valid Fernet key for testing
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    original_token = "test_refresh_token_12345"
    
    # Encrypt the token
    encrypted = service.encrypt_token(original_token)
    
    # Verify encrypted token is different from original
    assert encrypted != original_token
    assert len(encrypted) > len(original_token)
    
    # Decrypt the token
    decrypted = service.decrypt_token(encrypted)
    
    # Verify we get back the original token
    assert decrypted == original_token


def test_token_encryption_different_keys():
    """Test that tokens encrypted with one key cannot be decrypted with another."""
    key1 = Fernet.generate_key().decode('utf-8')
    key2 = Fernet.generate_key().decode('utf-8')
    
    service1 = TokenEncryptionService(encryption_key=key1)
    service2 = TokenEncryptionService(encryption_key=key2)
    
    original_token = "test_refresh_token_12345"
    
    # Encrypt with key1
    encrypted = service1.encrypt_token(original_token)
    
    # Try to decrypt with key2 - should fail
    with pytest.raises(TokenEncryptionError, match="Invalid token or wrong encryption key"):
        service2.decrypt_token(encrypted)


def test_token_encryption_empty_token():
    """Test that encrypting an empty token raises an error."""
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    with pytest.raises(TokenEncryptionError, match="Cannot encrypt empty token"):
        service.encrypt_token("")


def test_token_decryption_empty_token():
    """Test that decrypting an empty token raises an error."""
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    with pytest.raises(TokenEncryptionError, match="Cannot decrypt empty token"):
        service.decrypt_token("")


def test_token_encryption_invalid_key():
    """Test that initializing with an invalid key raises an error."""
    with pytest.raises(TokenEncryptionError, match="Invalid encryption key format"):
        TokenEncryptionService(encryption_key="invalid_key")


def test_token_encryption_missing_key():
    """Test that initializing without a key raises an error when not in settings."""
    # This test assumes MCKINSEY_TOKEN_ENCRYPTION_KEY is not set in test environment
    # If it is set, this test will pass but won't test the error case
    import os
    original_key = os.environ.get("MCKINSEY_TOKEN_ENCRYPTION_KEY")
    
    try:
        # Temporarily remove the key
        if "MCKINSEY_TOKEN_ENCRYPTION_KEY" in os.environ:
            del os.environ["MCKINSEY_TOKEN_ENCRYPTION_KEY"]
        
        # Force reload of settings
        from backend import config
        config.settings.mckinsey_token_encryption_key = ""
        
        with pytest.raises(TokenEncryptionError, match="Token encryption key not configured"):
            TokenEncryptionService()
    finally:
        # Restore original key
        if original_key:
            os.environ["MCKINSEY_TOKEN_ENCRYPTION_KEY"] = original_key


def test_convenience_functions():
    """Test the convenience functions for encryption/decryption."""
    # Set a test key in environment
    import os
    test_key = Fernet.generate_key().decode('utf-8')
    os.environ["MCKINSEY_TOKEN_ENCRYPTION_KEY"] = test_key
    
    # Force reload of settings
    from backend import config
    config.settings.mckinsey_token_encryption_key = test_key
    
    # Reset global instance
    from backend.services import token_encryption
    token_encryption._token_encryption_service = None
    
    original_token = "test_refresh_token_12345"
    
    # Test convenience functions
    encrypted = encrypt_refresh_token(original_token)
    decrypted = decrypt_refresh_token(encrypted)
    
    assert decrypted == original_token


def test_token_encryption_unicode():
    """Test that encryption works with unicode characters."""
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    original_token = "test_token_with_unicode_🔐_characters"
    
    encrypted = service.encrypt_token(original_token)
    decrypted = service.decrypt_token(encrypted)
    
    assert decrypted == original_token


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
