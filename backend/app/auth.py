"""
Clerk Authentication for Karma Backend.
Provides JWT verification for protected routes.
"""

import os
import httpx
import time
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, jwk
from jose.utils import base64url_decode

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from backend directory
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

# Get Clerk configuration from environment
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN")  # e.g., "moving-flamingo-53.clerk.accounts.dev"
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")

# Construct JWKS URL if domain is provided but JWKS URL is not
if CLERK_DOMAIN and not CLERK_JWKS_URL:
    domain = CLERK_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/")
    CLERK_JWKS_URL = f"https://{domain}/.well-known/jwks.json"

CLERK_ENABLED = bool(CLERK_SECRET_KEY and (CLERK_JWKS_URL or CLERK_DOMAIN))

# Security scheme
security = HTTPBearer(auto_error=False)

class AuthUser:
    """Represents an authenticated user."""
    def __init__(self, user_id: str, email: Optional[str] = None, name: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.name = name
        self._is_admin: Optional[bool] = None
    
    def is_admin(self) -> bool:
        """Check if this user is an admin."""
        if self._is_admin is None:
            from app.config import get_settings
            settings = get_settings()
            self._is_admin = settings.is_admin(user_id=self.user_id, email=self.email)
        return self._is_admin

# Cache for JWKS keys to avoid fetching on every request
_jwks_cache: Dict[str, Any] = {}
_last_jwks_fetch = 0

async def get_jwks():
    """Fetch and cache JWKS from Clerk."""
    global _jwks_cache, _last_jwks_fetch
    
    # Refresh cache every hour
    if not _jwks_cache or (time.time() - _last_jwks_fetch > 3600):
        try:
            print(f"🔄 Fetching JWKS from: {CLERK_JWKS_URL}")
            async with httpx.AsyncClient() as client:
                response = await client.get(CLERK_JWKS_URL)
                response.raise_for_status()
                _jwks_cache = response.json()
                _last_jwks_fetch = time.time()
                print("✅ JWKS fetched successfully")
        except Exception as e:
            print(f"❌ Failed to fetch JWKS: {e}")
            if not _jwks_cache:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not verify authentication: JWKS unavailable"
                )
    return _jwks_cache

async def verify_token(token: str) -> Dict[str, Any]:
    """Verify a Clerk JWT token manually."""
    try:
        # Get public keys
        jwks = await get_jwks()
        
        # Unverified header to find the correct key (kid)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("No kid in token header")
        
        # Find matching key in JWKS
        key_data = next((key for key in jwks["keys"] if key["kid"] == kid), None)
        if not key_data:
            raise ValueError(f"No matching key for kid: {kid}")
            
        # Verify signature and standard claims
        # IMPORTANT: We skip 'aud' (audience) verification because Clerk session tokens don't include it
        # We still verify issuer (iss) and expiration (exp)
        issuer = f"https://{CLERK_DOMAIN}" if "https://" not in CLERK_DOMAIN else CLERK_DOMAIN
        
        decoded = jwt.decode(
            token,
            key_data,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Skip audience check
                "verify_iss": True,   # Verify issuer
                "verify_exp": True,   # Verify expiration
                "at_hash": False,
            },
            issuer=issuer
        )
        return decoded
        
    except Exception as e:
        print(f"❌ Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid authentication: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def _auth_dependency(request: Request) -> Optional[Dict[str, Any]]:
    """Dependency that handles token extraction and custom verification."""
    if not CLERK_ENABLED:
        return None
        
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = auth_header.split(" ")[1]
    return await verify_token(token)

async def require_auth(
    decoded: Optional[dict] = Depends(_auth_dependency)
) -> AuthUser:
    """
    Require authentication for a route.
    """
    if not CLERK_ENABLED:
        return AuthUser(user_id="legacy-user", email="legacy@karma.local", name="Legacy User")
    
    if decoded:
        try:
            user_id = decoded.get("sub")
            if not user_id:
                raise ValueError("No user ID (sub) in JWT payload")
            
            email = decoded.get("email")
            if not email and decoded.get("email_addresses"):
                email = decoded["email_addresses"][0].get("email_address")
            
            name = decoded.get("name")
            if not name:
                first = decoded.get("first_name", "")
                last = decoded.get("last_name", "")
                name = f"{first} {last}".strip() or None
            
            auth_user = AuthUser(user_id=user_id, email=email, name=name)
            print(f"🔐 [AUTH] Authenticated user: user_id={user_id}, email={email}")
            return auth_user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid user payload: {str(e)}",
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )

async def get_current_user(
    request: Request
) -> Optional[AuthUser]:
    """Optional authentication."""
    if not CLERK_ENABLED:
        return AuthUser(user_id="legacy-user", email="legacy@karma.local", name="Legacy User")
        
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    try:
        token = auth_header.split(" ")[1]
        decoded = await verify_token(token)
        return AuthUser(
            user_id=decoded.get("sub", "unknown"),
            email=decoded.get("email"),
            name=decoded.get("name")
        )
    except:
        return None

def is_auth_enabled() -> bool:
    return CLERK_ENABLED

