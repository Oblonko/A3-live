"""
Bidimention A-3 — Google OAuth Verification (Backend)

Responsibilities:
- Verify Google ID tokens issued to frontend
- Enforce Gmail-only policy
- Return normalized user identity
- CONNECT identity to JWT issuer (Cognito)
- NO session handling
- NO JWT issuance
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger("auth.google")

# =====================================================
# ENV
# =====================================================

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
COGNITO_JWT_ISSUER = os.getenv("COGNITO_JWT_ISSUER")

if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID is not set")

if not COGNITO_JWT_ISSUER:
    raise RuntimeError("COGNITO_JWT_ISSUER is not set")

# =====================================================
# DATA MODEL
# =====================================================

@dataclass(frozen=True)
class GoogleUser:
    """
    Normalized Google identity payload
    (issuer-connected, JWT-ready)
    """
    sub: str
    email: str
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]
    issuer: str        # downstream JWT issuer (Cognito)
    provider: str      # explicit auth source


# =====================================================
# CORE VERIFICATION
# =====================================================

def validate_google_user(id_token_str: str) -> GoogleUser:
    """
    Validate a Google ID token sent by the frontend.

    Steps:
    1. Verify token signature & audience
    2. Ensure email is verified
    3. Enforce Gmail-only policy
    4. Normalize identity
    5. Attach JWT issuer context (Cognito)

    Raises:
        ValueError on invalid token
    """

    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        logger.warning("Invalid Google ID token", exc_info=exc)
        raise ValueError("Invalid Google ID token")

    # -------------------------------------------------
    # Required fields
    # -------------------------------------------------

    email = payload.get("email")
    email_verified = payload.get("email_verified", False)

    if not email or not email_verified:
        raise ValueError("Unverified Google account")

    email = email.lower()

    # -------------------------------------------------
    # Gmail-only enforcement
    # -------------------------------------------------

    if not email.endswith("@gmail.com"):
        raise ValueError("Only Gmail accounts are allowed")

    # -------------------------------------------------
    # Build normalized identity (issuer-connected)
    # -------------------------------------------------

    user = GoogleUser(
        sub=payload.get("sub"),
        email=email,
        email_verified=email_verified,
        name=payload.get("name"),
        picture=payload.get("picture"),
        issuer=COGNITO_JWT_ISSUER,
        provider="google",
    )

    logger.info(
        "Google OAuth validated",
        extra={
            "email": user.email,
            "sub": user.sub,
            "issuer": user.issuer,
            "provider": user.provider,
        },
    )

    return user
