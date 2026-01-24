from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import jwt
from jwt import PyJWTError


# =====================================================
# ENV CONFIG
# =====================================================

JWT_SECRET = os.getenv("JWT_SECRET", "dev_jwt_secret_do_not_use_in_prod")
JWT_ISSUER = os.getenv("JWT_ISSUER", "bidimention")
JWT_ALGO = "HS256"
JWT_EXP_MINUTES = int(os.getenv("JWT_EXP_MINUTES", "1440"))  # 24h default
JWT_LEEWAY_SECONDS = 30  # clock skew tolerance


# =====================================================
# PAYLOAD MODEL
# =====================================================

@dataclass(frozen=True)
class JWTPayload:
    uid: str
    session_id: str
    iat: int
    exp: int
    iss: str


# =====================================================
# TOKEN ISSUANCE
# =====================================================

def issue_jwt(uid: str, session_id: str) -> str:
    """
    Issue a signed JWT bound to a user + session.

    Called ONLY after:
    - Google OAuth validation
    - Email whitelist check
    - Session creation
    """

    now = int(time.time())
    exp = now + JWT_EXP_MINUTES * 60

    payload = {
        "uid": uid,
        "sid": session_id,
        "iat": now,
        "exp": exp,
        "iss": JWT_ISSUER,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )

    return token


# =====================================================
# TOKEN DECODE / VALIDATION
# =====================================================

def decode_jwt(token: str) -> Optional[JWTPayload]:
    """
    Decode and validate a JWT.

    Validation:
    - signature
    - expiration
    - issuer
    - required claims

    Returns:
      JWTPayload if valid
      None if invalid
    """
    try:
        decoded: Dict[str, Any] = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGO],
            issuer=JWT_ISSUER,
            leeway=JWT_LEEWAY_SECONDS,
            options={
                "require": ["exp", "iat", "iss", "uid", "sid"],
            },
        )

        return JWTPayload(
            uid=decoded["uid"],
            session_id=decoded["sid"],
            iat=int(decoded["iat"]),
            exp=int(decoded["exp"]),
            iss=decoded["iss"],
        )

    except PyJWTError:
        return None


# =====================================================
# OPTIONAL HELPERS
# =====================================================

def is_expired(payload: JWTPayload) -> bool:
    """Check if token is expired (defensive)"""
    return payload.exp < int(time.time())


def remaining_seconds(payload: JWTPayload) -> int:
    """Seconds until expiration"""
    return max(payload.exp - int(time.time()), 0)
