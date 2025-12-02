#!/usr/bin/env python3
"""
Simple test for OAuthStateManager to verify basic functionality.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.oauth_state import OAuthStateManager


async def test_oauth_state_manager():
    """Test OAuthStateManager basic functionality."""
    print("🔵 Testing OAuthStateManager...")
    print()
    
    # Initialize state manager
    state_manager = OAuthStateManager(ttl=600)
    
    # Test 1: Create state
    print("✅ Test 1: Create state")
    state = await state_manager.create_state({"user_id": "test_user"})
    print(f"   Generated state: {state[:20]}...")
    print(f"   State length: {len(state)}")
    assert len(state) > 20, "State should be sufficiently long"
    print()
    
    # Test 2: Validate state (should succeed)
    print("✅ Test 2: Validate state (should succeed)")
    user_data = await state_manager.validate_state(state)
    print(f"   Validation result: {user_data}")
    assert user_data is not None, "State validation should succeed"
    assert user_data.get("user_id") == "test_user", "User data should match"
    print()
    
    # Test 3: Validate same state again (should fail - single use)
    print("✅ Test 3: Validate same state again (should fail - single use)")
    user_data = await state_manager.validate_state(state)
    print(f"   Validation result: {user_data}")
    assert user_data is None, "State should not be reusable (single-use enforcement)"
    print()
    
    # Test 4: Validate invalid state
    print("✅ Test 4: Validate invalid state")
    user_data = await state_manager.validate_state("invalid_state_12345")
    print(f"   Validation result: {user_data}")
    assert user_data is None, "Invalid state should fail validation"
    print()
    
    # Test 5: Create nonce
    print("✅ Test 5: Create nonce")
    nonce = await state_manager.create_nonce()
    print(f"   Generated nonce: {nonce[:20]}...")
    print(f"   Nonce length: {len(nonce)}")
    assert len(nonce) > 20, "Nonce should be sufficiently long"
    print()
    
    # Test 6: Validate nonce (should succeed)
    print("✅ Test 6: Validate nonce (should succeed)")
    is_valid = await state_manager.validate_nonce(nonce)
    print(f"   Validation result: {is_valid}")
    assert is_valid is True, "Nonce validation should succeed"
    print()
    
    # Test 7: Validate same nonce again (should fail - single use)
    print("✅ Test 7: Validate same nonce again (should fail - single use)")
    is_valid = await state_manager.validate_nonce(nonce)
    print(f"   Validation result: {is_valid}")
    assert is_valid is False, "Nonce should not be reusable (single-use enforcement)"
    print()
    
    # Test 8: Validate invalid nonce
    print("✅ Test 8: Validate invalid nonce")
    is_valid = await state_manager.validate_nonce("invalid_nonce_12345")
    print(f"   Validation result: {is_valid}")
    assert is_valid is False, "Invalid nonce should fail validation"
    print()
    
    # Test 9: State uniqueness
    print("✅ Test 9: State uniqueness")
    states = set()
    for i in range(100):
        state = await state_manager.create_state()
        states.add(state)
    print(f"   Generated 100 states, unique count: {len(states)}")
    assert len(states) == 100, "All states should be unique"
    print()
    
    # Test 10: Nonce uniqueness
    print("✅ Test 10: Nonce uniqueness")
    nonces = set()
    for i in range(100):
        nonce = await state_manager.create_nonce()
        nonces.add(nonce)
    print(f"   Generated 100 nonces, unique count: {len(nonces)}")
    assert len(nonces) == 100, "All nonces should be unique"
    print()
    
    # Cleanup
    await state_manager.close()
    
    print("✅ All tests passed!")
    return True


async def main():
    """Run tests."""
    try:
        success = await test_oauth_state_manager()
        if success:
            print("\n✅ OAuthStateManager tests completed successfully")
            sys.exit(0)
        else:
            print("\n❌ OAuthStateManager tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
