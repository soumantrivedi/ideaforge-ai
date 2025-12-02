#!/usr/bin/env python3
"""
Simple standalone test for token encryption without config dependencies.
"""

from cryptography.fernet import Fernet


def test_fernet_encryption():
    """Test basic Fernet encryption/decryption."""
    print("Testing Fernet encryption/decryption...")
    
    # Generate a key
    key = Fernet.generate_key()
    print(f"Generated key: {key.decode()}")
    
    # Create cipher
    cipher = Fernet(key)
    
    # Test data
    original = "test_refresh_token_12345"
    print(f"Original: {original}")
    
    # Encrypt
    encrypted = cipher.encrypt(original.encode('utf-8'))
    print(f"Encrypted: {encrypted.decode()}")
    
    # Decrypt
    decrypted = cipher.decrypt(encrypted).decode('utf-8')
    print(f"Decrypted: {decrypted}")
    
    # Verify
    assert decrypted == original, "Decryption failed!"
    print("✓ Test passed!")
    
    return True


def test_token_encryption_class():
    """Test the TokenEncryptionService class directly."""
    print("\nTesting TokenEncryptionService class...")
    
    # Import only what we need
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Mock the settings to avoid config loading
    class MockSettings:
        mckinsey_token_encryption_key = Fernet.generate_key().decode('utf-8')
    
    # Temporarily replace settings
    import backend.services.token_encryption as te_module
    original_settings = None
    try:
        # Import and patch
        from backend import config
        original_settings = config.settings
        config.settings = MockSettings()
        
        # Now import the service
        from backend.services.token_encryption import TokenEncryptionService, TokenEncryptionError
        
        # Test basic encryption
        service = TokenEncryptionService()
        original = "test_refresh_token_12345"
        
        encrypted = service.encrypt_token(original)
        print(f"Encrypted: {encrypted[:50]}...")
        
        decrypted = service.decrypt_token(encrypted)
        print(f"Decrypted: {decrypted}")
        
        assert decrypted == original, "Decryption failed!"
        print("✓ TokenEncryptionService test passed!")
        
        # Test error cases
        print("\nTesting error cases...")
        
        # Empty token
        try:
            service.encrypt_token("")
            print("✗ Should have raised error for empty token")
            return False
        except TokenEncryptionError:
            print("✓ Empty token rejected")
        
        # Invalid encrypted token
        try:
            service.decrypt_token("invalid_encrypted_data")
            print("✗ Should have raised error for invalid token")
            return False
        except TokenEncryptionError:
            print("✓ Invalid token rejected")
        
        print("\n✓ All tests passed!")
        return True
        
    finally:
        # Restore original settings
        if original_settings:
            config.settings = original_settings


if __name__ == "__main__":
    try:
        test_fernet_encryption()
        test_token_encryption_class()
        print("\n" + "=" * 60)
        print("All tests PASSED! ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
