"""
Clerk Authentication for Karma Backend.
Provides JWT verification for protected routes.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Try to import Clerk auth, but make it optional
try:
    from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
    CLERK_AVAILABLE = True
except ImportError:
    CLERK_AVAILABLE = False
    ClerkConfig = None
    ClerkHTTPBearer = None

# Get Clerk configuration from environment
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# Check if Clerk is configured
CLERK_ENABLED = bool(CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY and CLERK_AVAILABLE)

# Security scheme for optional auth
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Represents an authenticated user."""
    def __init__(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.name = name


# Set up Clerk auth guard if available
clerk_auth_guard = None
if CLERK_ENABLED and ClerkHTTPBearer:
    try:
        # Extract the frontend API from publishable key
        # Format: pk_test_xxx or pk_live_xxx
        clerk_config = ClerkConfig(
            secret_key=CLERK_SECRET_KEY,
        )
        clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)
        print("✅ Clerk authentication enabled")
    except Exception as e:
        print(f"⚠️ Clerk setup failed: {e}")
        CLERK_ENABLED = False
else:
    if not CLERK_AVAILABLE:
        print("⚠️ fastapi-clerk-auth not installed - auth disabled")
    elif not CLERK_SECRET_KEY:
        print("⚠️ CLERK_SECRET_KEY not set - auth disabled")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthUser]:
    """
    Get the current authenticated user.
    Returns None if not authenticated (for optional auth routes).
    """
    if not CLERK_ENABLED:
        # Auth disabled - return a dummy user for development
        return AuthUser(user_id="dev-user", email="dev@karma.local", name="Dev User")
    
    if not credentials:
        return None
    
    try:
        if clerk_auth_guard:
            # Verify the token with Clerk
            decoded = await clerk_auth_guard.verify(credentials)
            return AuthUser(
                user_id=decoded.get("sub", "unknown"),
                email=decoded.get("email"),
                name=decoded.get("name")
            )
    except Exception as e:
        print(f"Auth error: {e}")
        return None
    
    return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """
    Require authentication for a route.
    Raises 401 if not authenticated.
    """
    if not CLERK_ENABLED:
        # Auth disabled - return a dummy user for development
        return AuthUser(user_id="dev-user", email="dev@karma.local", name="Dev User")
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        if clerk_auth_guard:
            decoded = await clerk_auth_guard.verify(credentials)
            return AuthUser(
                user_id=decoded.get("sub", "unknown"),
                email=decoded.get("email"),
                name=decoded.get("name")
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return CLERK_ENABLED

