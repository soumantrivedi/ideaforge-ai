#!/usr/bin/env python3
"""
Integration test for McKinsey SSO implementation.
Tests all core services: token encryption, OAuth state, OIDC provider, token validator, and profile mapper.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.token_encryption import TokenEncryptionService, encrypt_refresh_token, decrypt_refresh_token
from backend.services.oauth_state import OAuthStateManager
from backend.services.mckinsey_oidc import McKinseyOIDCProvider
from backend.services.token_validator import McKinseyTokenValidator
from backend.services.mckinsey_profile_mapper import McKinseyProfileMapper


async def test_integration():
    """Run integration tests for all McKinsey SSO services."""
    print("🔵 McKinsey SSO Integration Tests")
    print("=" * 60)
    
    # Test 1: Token Encryption Service
    print("\n✅ Test 1: Token Encryption Service")
    try:
        test_token = "test_refresh_token_12345"
        encrypted = encrypt_refresh_token(test_token)
        decrypted = decrypt_refresh_token(encrypted)
        assert decrypted == test_token, "Token encryption/decryption failed"
        print(f"   ✓ Token encryption/decryption working")
    except Exception as e:
        print(f"   ✗ Token encryption failed: {e}")
        return False
    
    # Test 2: OAuth State Manager
    print("\n✅ Test 2: OAuth State Manager")
    try:
        state_manager = OAuthStateManager(ttl=600)
        
        # Create and validate state
        state = await state_manager.create_state({"user_id": "test_user"})
        assert len(state) > 20, "State should be sufficiently long"
        
        user_data = await state_manager.validate_state(state)
        assert user_data is not None, "State validation should succeed"
        assert user_data.get("user_id") == "test_user", "User data should match"
        
        # Verify single-use
        user_data = await state_manager.validate_state(state)
        assert user_data is None, "State should not be reusable"
        
        # Create and validate nonce
        nonce = await state_manager.create_nonce()
        assert len(nonce) > 20, "Nonce should be sufficiently long"
        
        is_valid = await state_manager.validate_nonce(nonce)
        assert is_valid is True, "Nonce validation should succeed"
        
        # Verify single-use
        is_valid = await state_manager.validate_nonce(nonce)
        assert is_valid is False, "Nonce should not be reusable"
        
        await state_manager.close()
        print(f"   ✓ OAuth state and nonce management working")
    except Exception as e:
        print(f"   ✗ OAuth state manager failed: {e}")
        return False
    
    # Test 3: McKinsey OIDC Provider
    print("\n✅ Test 3: McKinsey OIDC Provider")
    try:
        provider = McKinseyOIDCProvider()
        
        # Test authorization URL generation
        state = "test_state_12345"
        nonce = "test_nonce_12345"
        auth_url = await provider.get_authorization_url(state, nonce)
        
        assert "https://auth.mckinsey.id" in auth_url, "Authorization URL should point to mckinsey.id"
        assert f"state={state}" in auth_url, "Authorization URL should include state"
        assert f"nonce={nonce}" in auth_url, "Authorization URL should include nonce"
        assert "response_type=code" in auth_url, "Authorization URL should use code flow"
        assert "scope=openid" in auth_url, "Authorization URL should include openid scope"
        
        print(f"   ✓ Authorization URL generation working")
        print(f"   ✓ URL: {auth_url[:80]}...")
    except Exception as e:
        print(f"   ✗ McKinsey OIDC provider failed: {e}")
        return False
    
    # Test 4: McKinsey Token Validator
    print("\n✅ Test 4: McKinsey Token Validator")
    try:
        validator = McKinseyTokenValidator(provider)
        
        # Note: We can't test actual token validation without a real token
        # But we can verify the validator is properly initialized
        assert validator.provider == provider, "Validator should have provider reference"
        assert validator.EXPECTED_ISSUER == "https://auth.mckinsey.id/auth/realms/r", "Issuer should be set"
        assert len(validator.ALLOWED_ALGORITHMS) > 0, "Allowed algorithms should be configured"
        
        print(f"   ✓ Token validator initialized correctly")
        print(f"   ✓ Expected issuer: {validator.EXPECTED_ISSUER}")
        print(f"   ✓ Allowed algorithms: {validator.ALLOWED_ALGORITHMS}")
    except Exception as e:
        print(f"   ✗ Token validator failed: {e}")
        return False
    
    # Test 5: McKinsey Profile Mapper
    print("\n✅ Test 5: McKinsey Profile Mapper")
    try:
        # Test with sample McKinsey token claims
        sample_claims = {
            "sub": "4e712f42-d702-49bd-8969-fd0eb516a092",
            "email": "Stefan_Baryakov@MCKINSEY.COM",
            "email_verified": True,
            "name": "Stefan Baryakov",
            "given_name": "Stefan",
            "family_name": "Baryakov",
            "preferred_username": "cc4c2f863e37dbbd",
            "fmno": "84115",
            "session_state": "91063aa4-f2e0-4ee7-8ae7-0e83a5bcfa64",
            "iss": "https://auth.mckinsey.id/auth/realms/r",
            "aud": "test-client-id",
            "exp": 1764708974,
            "iat": 1764672974,
            "auth_time": 1764672974
        }
        
        # Note: McKinseyProfileMapper requires a database session for full functionality
        # We'll just verify the class can be imported and has the expected methods
        assert hasattr(McKinseyProfileMapper, 'extract_claims'), "Should have extract_claims method"
        assert hasattr(McKinseyProfileMapper, 'create_or_update_user'), "Should have create_or_update_user method"
        assert hasattr(McKinseyProfileMapper, 'assign_tenant'), "Should have assign_tenant method"
        assert hasattr(McKinseyProfileMapper, 'get_default_values'), "Should have get_default_values method"
        
        print(f"   ✓ Profile mapper class structure verified")
        print(f"   ✓ Has extract_claims method")
        print(f"   ✓ Has create_or_update_user method")
        print(f"   ✓ Has assign_tenant method")
        print(f"   ✓ Has get_default_values method")
    except Exception as e:
        print(f"   ✗ Profile mapper failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Database Migration Verification
    print("\n✅ Test 6: Database Migration Verification")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy import text
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://agentic_pm:devpassword@postgres:5432/agentic_pm_db")
        if not database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        engine = create_async_engine(database_url, echo=False)
        
        async with engine.begin() as conn:
            session = AsyncSession(conn, expire_on_commit=False)
            
            # Verify all McKinsey SSO columns exist
            expected_columns = [
                'mckinsey_subject',
                'mckinsey_email',
                'mckinsey_refresh_token_encrypted',
                'mckinsey_token_expires_at',
                'mckinsey_fmno',
                'mckinsey_preferred_username',
                'mckinsey_session_state'
            ]
            
            for column in expected_columns:
                result = await session.execute(
                    text("""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'user_profiles' AND column_name = :column_name
                    """),
                    {"column_name": column}
                )
                if result.fetchone() is None:
                    print(f"   ✗ Column missing: {column}")
                    return False
            
            # Verify indexes exist
            expected_indexes = [
                'idx_user_profiles_mckinsey_subject',
                'idx_user_profiles_mckinsey_email',
                'idx_user_profiles_mckinsey_fmno'
            ]
            
            for index in expected_indexes:
                result = await session.execute(
                    text("""
                        SELECT 1 FROM pg_indexes 
                        WHERE tablename = 'user_profiles' AND indexname = :index_name
                    """),
                    {"index_name": index}
                )
                if result.fetchone() is None:
                    print(f"   ✗ Index missing: {index}")
                    return False
        
        await engine.dispose()
        print(f"   ✓ All McKinsey SSO database columns and indexes verified")
    except Exception as e:
        print(f"   ✗ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ All McKinsey SSO integration tests passed!")
    print("=" * 60)
    return True


async def main():
    """Run integration tests."""
    try:
        success = await test_integration()
        if success:
            print("\n✅ McKinsey SSO integration tests completed successfully")
            sys.exit(0)
        else:
            print("\n❌ McKinsey SSO integration tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
