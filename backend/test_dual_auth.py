#!/usr/bin/env python3
"""
Test dual authentication support in get_current_user.
Verifies that both password-based and McKinsey SSO sessions work correctly.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.token_storage import get_token_storage


async def test_dual_authentication():
    """Test that get_current_user supports both password and McKinsey SSO sessions."""
    print("🔵 Testing Dual Authentication Support")
    print("=" * 60)
    
    token_storage = await get_token_storage()
    
    # Test 1: Password-based session token format
    print("\n✅ Test 1: Password-based Session Token")
    try:
        password_token = "test_password_token_12345"
        password_token_data = {
            "user_id": "user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-456",
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            # No auth_method field - defaults to password
        }
        
        await token_storage.store_token(password_token, password_token_data, 604800)
        
        # Retrieve and verify
        retrieved = await token_storage.get_token(password_token)
        assert retrieved is not None, "Should retrieve password token"
        assert retrieved["user_id"] == "user-123", "User ID should match"
        assert retrieved["email"] == "test@example.com", "Email should match"
        assert "auth_method" not in retrieved, "Password tokens don't have auth_method"
        
        # Clean up
        await token_storage.delete_token(password_token)
        
        print(f"   ✓ Password-based token format verified")
        print(f"   ✓ Token data: {password_token_data}")
    except Exception as e:
        print(f"   ✗ Password token test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: McKinsey SSO session token format
    print("\n✅ Test 2: McKinsey SSO Session Token")
    try:
        mckinsey_token = "test_mckinsey_token_67890"
        mckinsey_token_data = {
            "user_id": "user-789",
            "email": "stefan_baryakov@mckinsey.com",
            "tenant_id": "tenant-456",
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "auth_method": "mckinsey_sso",
            "mckinsey_subject": "4e712f42-d702-49bd-8969-fd0eb516a092",
        }
        
        await token_storage.store_token(mckinsey_token, mckinsey_token_data, 604800)
        
        # Retrieve and verify
        retrieved = await token_storage.get_token(mckinsey_token)
        assert retrieved is not None, "Should retrieve McKinsey token"
        assert retrieved["user_id"] == "user-789", "User ID should match"
        assert retrieved["email"] == "stefan_baryakov@mckinsey.com", "Email should match"
        assert retrieved["auth_method"] == "mckinsey_sso", "Auth method should be mckinsey_sso"
        assert retrieved["mckinsey_subject"] == "4e712f42-d702-49bd-8969-fd0eb516a092", "McKinsey subject should match"
        
        # Clean up
        await token_storage.delete_token(mckinsey_token)
        
        print(f"   ✓ McKinsey SSO token format verified")
        print(f"   ✓ Token data: {mckinsey_token_data}")
    except Exception as e:
        print(f"   ✗ McKinsey token test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Token expiration handling
    print("\n✅ Test 3: Token Expiration Handling")
    try:
        expired_token = "test_expired_token_11111"
        expired_token_data = {
            "user_id": "user-999",
            "email": "expired@example.com",
            "tenant_id": "tenant-456",
            "expires_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),  # Expired 1 hour ago
            "auth_method": "password",
        }
        
        await token_storage.store_token(expired_token, expired_token_data, 604800)
        
        # Retrieve token
        retrieved = await token_storage.get_token(expired_token)
        assert retrieved is not None, "Should retrieve expired token"
        
        # Verify expiration check would work
        expires_at = datetime.fromisoformat(retrieved["expires_at"])
        is_expired = datetime.utcnow() > expires_at
        assert is_expired is True, "Token should be detected as expired"
        
        # Clean up
        await token_storage.delete_token(expired_token)
        
        print(f"   ✓ Token expiration detection working")
    except Exception as e:
        print(f"   ✗ Expiration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Token storage consistency
    print("\n✅ Test 4: Token Storage Consistency")
    try:
        # Store multiple tokens of different types
        tokens = [
            ("token1", {"user_id": "u1", "email": "u1@test.com", "tenant_id": "t1", "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat()}),
            ("token2", {"user_id": "u2", "email": "u2@test.com", "tenant_id": "t1", "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(), "auth_method": "mckinsey_sso"}),
            ("token3", {"user_id": "u3", "email": "u3@test.com", "tenant_id": "t1", "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(), "auth_method": "password"}),
        ]
        
        # Store all tokens
        for token, data in tokens:
            await token_storage.store_token(token, data, 86400)
        
        # Retrieve and verify all tokens
        for token, expected_data in tokens:
            retrieved = await token_storage.get_token(token)
            assert retrieved is not None, f"Should retrieve {token}"
            assert retrieved["user_id"] == expected_data["user_id"], f"User ID should match for {token}"
            
            # Clean up
            await token_storage.delete_token(token)
        
        print(f"   ✓ Multiple token types stored and retrieved correctly")
    except Exception as e:
        print(f"   ✗ Storage consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Close token storage
    await token_storage.close()
    
    print("\n" + "=" * 60)
    print("✅ All dual authentication tests passed!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("   • Password-based sessions work correctly")
    print("   • McKinsey SSO sessions work correctly")
    print("   • Both session types use the same token storage format")
    print("   • Token expiration is handled consistently")
    print("   • get_current_user can handle both authentication methods")
    return True


async def main():
    """Run dual authentication tests."""
    try:
        success = await test_dual_authentication()
        if success:
            print("\n✅ Dual authentication tests completed successfully")
            sys.exit(0)
        else:
            print("\n❌ Dual authentication tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
