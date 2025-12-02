# McKinsey SSO Logout Implementation

## Overview

This document describes the implementation of McKinsey SSO logout functionality in the IdeaForge AI application, completing task 15.1 from the OAuth2/OIDC authentication specification.

## Changes Made

### 1. Frontend Changes (src/contexts/AuthContext.tsx)

#### Updated User Interface
Added `mckinsey_subject` field to the User interface to detect McKinsey SSO users:

```typescript
interface User {
  id: string;
  email: string;
  full_name?: string;
  tenant_id: string;
  tenant_name: string;
  persona: string;
  avatar_url?: string;
  mckinsey_subject?: string; // Present if user logged in via McKinsey SSO
}
```

#### Enhanced Logout Function
Updated the `logout()` function to support both McKinsey SSO and password-based authentication:

**Key Features:**
- **SSO Detection**: Checks if `user.mckinsey_subject` is present to determine if user logged in via McKinsey SSO
- **Dual Flow Support**:
  - **McKinsey SSO Users**: Calls `/api/auth/mckinsey/logout` and redirects to McKinsey's RP-initiated logout URL
  - **Password Users**: Calls `/api/auth/logout` (existing behavior)
- **Session Cleanup**: Clears local storage, session storage, and cookies for both flows
- **Backward Compatibility**: Maintains existing logout behavior for password-based users

**Implementation:**
```typescript
const logout = async () => {
  try {
    // Detect if user logged in via McKinsey SSO
    const isMcKinseyUser = user?.mckinsey_subject !== undefined && user?.mckinsey_subject !== null;

    if (isMcKinseyUser) {
      // McKinsey SSO logout flow
      const response = await apiFetch('/api/auth/mckinsey/logout', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });

      if (response.ok) {
        const data = await response.json();
        
        // Clear session storage and local auth data first
        clearAllSessionStorage();
        handleUnauthorized();

        // Redirect to McKinsey logout URL for RP-initiated logout
        if (data.logout_url) {
          window.location.href = data.logout_url;
          return; // Don't continue execution after redirect
        }
      } else {
        // If McKinsey logout fails, still clear local session
        console.error('McKinsey logout failed, clearing local session');
      }
    } else {
      // Regular password-based logout flow
      await apiFetch('/api/auth/logout', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Clear session storage before clearing auth
    // (only reached if not redirected to McKinsey logout)
    clearAllSessionStorage();
    handleUnauthorized();
  }
};
```

### 2. Backend Changes (backend/api/auth.py)

#### Updated UserInfo Model
Added `mckinsey_subject` field to the UserInfo response model:

```python
class UserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    tenant_id: str
    tenant_name: str
    persona: str
    avatar_url: Optional[str]
    mckinsey_subject: Optional[str] = None  # Present if user logged in via McKinsey SSO
```

#### Enhanced get_current_user Dependency
Updated the database query to include `mckinsey_subject`:

```python
query = text(
    """
    SELECT id, email, full_name, tenant_id, is_active, persona, avatar_url, mckinsey_subject
    FROM user_profiles
    WHERE id = :user_id AND is_active = true
"""
)

# Return includes mckinsey_subject
return {
    "id": str(row[0]),
    "email": row[1],
    "full_name": row[2],
    "tenant_id": str(row[3]),
    "persona": row[5],
    "avatar_url": row[6],
    "mckinsey_subject": row[7],  # Include McKinsey subject for SSO detection
    "auth_method": auth_method,
}
```

#### Updated /api/auth/me Endpoint
Modified the endpoint to return `mckinsey_subject`:

```python
return UserInfo(
    id=current_user["id"],
    email=current_user["email"],
    full_name=current_user["full_name"],
    tenant_id=current_user["tenant_id"],
    tenant_name=tenant_name,
    persona=current_user["persona"],
    avatar_url=current_user.get("avatar_url"),
    mckinsey_subject=current_user.get("mckinsey_subject"),
)
```

## Logout Flow

### McKinsey SSO Logout Flow

1. **User initiates logout** from the frontend
2. **Frontend detects SSO user** by checking `user.mckinsey_subject`
3. **Frontend calls** `/api/auth/mckinsey/logout` endpoint
4. **Backend performs**:
   - Invalidates session token in Redis
   - Clears refresh token from database
   - Constructs RP-initiated logout URL for McKinsey
   - Clears session cookie
5. **Backend returns** `logout_url` to frontend
6. **Frontend clears** local storage and session storage
7. **Frontend redirects** to McKinsey logout URL
8. **McKinsey terminates** user's SSO session
9. **McKinsey redirects** back to application login page

### Password-Based Logout Flow

1. **User initiates logout** from the frontend
2. **Frontend detects non-SSO user** (no `mckinsey_subject`)
3. **Frontend calls** `/api/auth/logout` endpoint (existing)
4. **Backend invalidates** session token
5. **Frontend clears** local storage and session storage
6. **User redirected** to login page

## Requirements Satisfied

This implementation satisfies the following requirements from the specification:

- **Requirement 4.4**: Session invalidation on logout
- **Requirement 11.1**: Backend invalidates session token in Redis
- **Requirement 11.2**: RP-initiated logout URL construction for McKinsey

## Testing Recommendations

### Manual Testing

1. **McKinsey SSO Logout**:
   - Log in using McKinsey SSO
   - Verify `mckinsey_subject` is present in user data
   - Click logout
   - Verify redirect to McKinsey logout page
   - Verify redirect back to login page
   - Verify session is cleared (cannot access protected routes)

2. **Password-Based Logout**:
   - Log in using email/password
   - Verify `mckinsey_subject` is not present
   - Click logout
   - Verify redirect to login page (no McKinsey redirect)
   - Verify session is cleared

3. **Session Cleanup**:
   - Verify local storage is cleared after logout
   - Verify session storage is cleared after logout
   - Verify cookies are cleared after logout

### Integration Testing

Consider adding integration tests for:
- McKinsey SSO logout flow end-to-end
- Password-based logout flow
- Session cleanup verification
- RP-initiated logout URL construction

## Security Considerations

1. **Session Cleanup**: Both logout flows properly clear all session data
2. **RP-Initiated Logout**: McKinsey SSO users are redirected to IdP logout to terminate SSO session
3. **Fallback Handling**: If McKinsey logout fails, local session is still cleared
4. **Backward Compatibility**: Existing password-based logout continues to work

## Future Enhancements

1. **ID Token Storage**: Store ID token for full RP-initiated logout (currently using client_id only)
2. **Logout Confirmation**: Add user confirmation before logout
3. **Logout Analytics**: Track logout events for monitoring
4. **Error Handling**: Enhanced error messages for logout failures

## Conclusion

The McKinsey SSO logout functionality has been successfully implemented with full backward compatibility for password-based authentication. The implementation follows OAuth 2.0 and OIDC best practices for RP-initiated logout.
