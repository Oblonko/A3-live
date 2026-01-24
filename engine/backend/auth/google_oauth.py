"""
Bidimention A-3 — Google OAuth Verification (Backend)

Responsibilities:
- Verify Google ID tokens issued to frontend
- Enforce Gmail-only policy
- Return normalized user identity
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

if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID is not set")

# =====================================================
# DATA MODEL
# =====================================================

@dataclass(frozen=True)
class GoogleUser:
    """
    Normalized Google identity payload
    """
    sub: str
    email: str
    email_verified: bool
    name: Optional[str]
    picture: Optional[str]


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
    # Build normalized identity
    # -------------------------------------------------

    user = GoogleUser(
        sub=payload.get("sub"),
        email=email,
        email_verified=email_verified,
        name=payload.get("name"),
        picture=payload.get("picture"),
    )

    logger.info(
        "Google OAuth validated",
        extra={
            "email": user.email,
            "sub": user.sub,
        },
    )

    return user
