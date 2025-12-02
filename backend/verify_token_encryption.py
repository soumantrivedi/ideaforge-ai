#!/usr/bin/env python3
"""
Standalone verification script for token encryption service.
This script can be run without pytest to verify basic functionality.
"""

import sys
import os

# Add parent directory to path to allow backend imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.fernet import Fernet
from backend.services.token_encryption import (
    TokenEncryptionService,
    TokenEncryptionError,
)


def test_basic_encryption():
    """Test basic encryption and decryption."""
    print("Test 1: Basic encryption/decryption round trip...")
    
    # Generate a valid Fernet key for testing
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    original_token = "test_refresh_token_12345"
    
    # Encrypt the token
    encrypted = service.encrypt_token(original_token)
    print(f"  Original: {original_token}")
    print(f"  Encrypted: {encrypted[:50]}...")
    
    # Decrypt the token
    decrypted = service.decrypt_token(encrypted)
    print(f"  Decrypted: {decrypted}")
    
    assert decrypted == original_token, "Decrypted token doesn't match original!"
    print("  ✓ PASSED\n")


def test_different_keys():
    """Test that different keys produce different results."""
    print("Test 2: Different keys cannot decrypt each other's tokens...")
    
    key1 = Fernet.generate_key().decode('utf-8')
    key2 = Fernet.generate_key().decode('utf-8')
    
    service1 = TokenEncryptionService(encryption_key=key1)
    service2 = TokenEncryptionService(encryption_key=key2)
    
    original_token = "test_refresh_token_12345"
    
    # Encrypt with key1
    encrypted = service1.encrypt_token(original_token)
    
    # Try to decrypt with key2 - should fail
    try:
        service2.decrypt_token(encrypted)
        print("  ✗ FAILED: Should have raised TokenEncryptionError")
        sys.exit(1)
    except TokenEncryptionError as e:
        print(f"  Expected error: {e}")
        print("  ✓ PASSED\n")


def test_empty_token():
    """Test that empty tokens are rejected."""
    print("Test 3: Empty tokens are rejected...")
    
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    try:
        service.encrypt_token("")
        print("  ✗ FAILED: Should have raised TokenEncryptionError")
        sys.exit(1)
    except TokenEncryptionError as e:
        print(f"  Expected error: {e}")
        print("  ✓ PASSED\n")


def test_invalid_key():
    """Test that invalid keys are rejected."""
    print("Test 4: Invalid encryption keys are rejected...")
    
    try:
        TokenEncryptionService(encryption_key="invalid_key")
        print("  ✗ FAILED: Should have raised TokenEncryptionError")
        sys.exit(1)
    except TokenEncryptionError as e:
        print(f"  Expected error: {e}")
        print("  ✓ PASSED\n")


def test_unicode():
    """Test that unicode characters work."""
    print("Test 5: Unicode characters in tokens...")
    
    test_key = Fernet.generate_key().decode('utf-8')
    service = TokenEncryptionService(encryption_key=test_key)
    
    original_token = "test_token_with_unicode_🔐_characters"
    
    encrypted = service.encrypt_token(original_token)
    decrypted = service.decrypt_token(encrypted)
    
    assert decrypted == original_token, "Unicode token doesn't match!"
    print(f"  Original: {original_token}")
    print(f"  Decrypted: {decrypted}")
    print("  ✓ PASSED\n")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Token Encryption Service Verification")
    print("=" * 60)
    print()
    
    try:
        test_basic_encryption()
        test_different_keys()
        test_empty_token()
        test_invalid_key()
        test_unicode()
        
        print("=" * 60)
        print("All tests PASSED! ✓")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
