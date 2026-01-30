from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

import httpx
from jose import jwt, JWTError


# =====================================================
# ENV CONFIG (COGNITO)
# =====================================================

COGNITO_ENABLED = os.getenv("COGNITO_ENABLED", "false").lower() == "true"

COGNITO_REGION = os.getenv("COGNITO_REGION")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

COGNITO_JWT_ISSUER = os.getenv("COGNITO_JWT_ISSUER")
COGNITO_JWT_ALGORITHM = os.getenv("COGNITO_JWT_ALGORITHM", "RS256")
COGNITO_TOKEN_USE = os.getenv("COGNITO_TOKEN_USE", "access")

JWT_LEEWAY_SECONDS = 30  # clock skew tolerance


# =====================================================
# PAYLOAD MODEL (Cognito-derived)
# =====================================================

@dataclass(frozen=True)
class JWTPayload:
    uid: str              # derived UID (stable)
    sub: str              # Cognito subject
    email: Optional[str]
    scope: Optional[str]
    iat: int
    exp: int
    iss: str


# =====================================================
# JWKS CACHE
# =====================================================

_JWKS: Dict[str, Any] | None = None
_JWKS_TS: float = 0
_JWKS_TTL = 3600  # 1 hour


def _jwks_url() -> str:
    return (
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )


def _get_jwks() -> Dict[str, Any]:
    global _JWKS, _JWKS_TS

    now = time.time()
    if _JWKS and (now - _JWKS_TS) < _JWKS_TTL:
        return _JWKS

    resp = httpx.get(_jwks_url(), timeout=5)
    resp.raise_for_status()

    _JWKS = resp.json()
    _JWKS_TS = now
    return _JWKS


# =====================================================
# UID BUILDER (CLONED LOGIC STYLE)
# =====================================================
def _build_uid(payload: Dict[str, Any]) -> str:
    """
    Stable internal UID derived from Cognito identity.
    This replaces the old uid issued by HS256 tokens.
    """
    # Prefer Cognito username if present
    if "username" in payload:
        return f"cognito:{payload['username']}"

    # Fallback to subject (always present)
    return f"cognito:{payload['sub']}"


# =====================================================
# TOKEN VERIFICATION
# =====================================================

def decode_jwt(token: str) -> Optional[JWTPayload]:
    """
    Decode and validate a Cognito access token.

    Validation:
    - RS256 signature (JWKS)
    - expiration
    - issuer
    - token_use=access

    Returns:
      JWTPayload if valid
      None if invalid
    """
    if not COGNITO_ENABLED:
        return None

    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        return None

    jwks = _get_jwks()
    key = next((k for k in jwks["keys"] if k["kid"] == header["kid"]), None)

    if not key:
        return None

    try:
        decoded: Dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[COGNITO_JWT_ALGORITHM],
            issuer=COGNITO_JWT_ISSUER,
            leeway=JWT_LEEWAY_SECONDS,
            options={
                "verify_aud": False,  # access tokens do not require aud
                "require": ["exp", "iat", "iss", "sub"],
            },
        )
    except JWTError:
        return None

    # Cognito-specific enforcement
    if decoded.get("token_use") != COGNITO_TOKEN_USE:
        return None

    uid = _build_uid(decoded)

    return JWTPayload(
        uid=uid,
        sub=decoded["sub"],
        email=decoded.get("email"),
        scope=decoded.get("scope"),
        iat=int(decoded["iat"]),
        exp=int(decoded["exp"]),
        iss=decoded["iss"],
    )


# =====================================================
# OPTIONAL HELPERS (UNCHANGED SEMANTICS)
# =====================================================

def is_expired(payload: JWTPayload) -> bool:
    return payload.exp < int(time.time())


def remaining_seconds(payload: JWTPayload) -> int:
    return max(payload.exp - int(time.time()), 0)
