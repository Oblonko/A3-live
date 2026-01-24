"""
Bidimention (A-3) — Backend Route Registry (Complete)

This module registers ALL HTTP + Stream routes exposed by the backend.

It intentionally contains:
- no business logic
- no engine execution
- no exchange access

Every endpoint listed in the spec is represented here.
"""

from fastapi import FastAPI

# =========================
# ROUTE MODULE IMPORTS
# =========================

# --- Auth ---
from engine.backend.routes.auth import router as auth_router

# --- Wallet ---
from engine.backend.routes.wallet import router as wallet_router

# --- Ledger ---
from engine.backend.routes.ledger import router as ledger_router

# --- Withdrawals ---
from engine.backend.routes.withdraw import router as withdraw_router

# --- Security / Sessions ---
from engine.backend.routes.security import router as security_router

# --- Audit / Proofs ---
from engine.backend.routes.audit import router as audit_router

# --- Admin ---
from engine.backend.routes.admin import router as admin_router

# --- Engine / Status ---
from engine.backend.routes.status import router as status_router
from engine.backend.routes.pairs import router as pairs_router

# --- Streams ---
from engine.backend.routes.stream import router as stream_router

# --- Internal / Trade ---
from engine.backend.routes.trade import router as trade_router


# =========================
# ROUTE REGISTRATION
# =========================

def register_routes(app: FastAPI) -> None:
    """
    Register all Bidimention backend routes.

    Prefix policy:
    - /api        → public + user APIs
    - /api/admin  → admin-only APIs
    - /api/stream → streaming endpoints
    - /trade      → internal engine control
    """

    # -------------------------
    # AUTH
    # -------------------------
    # POST /api/auth/cognito/exchange
    app.include_router(
        auth_router,
        prefix="/api/auth",
        tags=["auth"],
    )

    # -------------------------
    # WALLET
    # -------------------------
    # GET /api/wallet
    app.include_router(
        wallet_router,
        prefix="/api/wallet",
        tags=["wallet"],
    )

    # -------------------------
    # LEDGER
    # -------------------------
    # GET /api/ledger
    # GET /api/ledger?limit=100
    app.include_router(
        ledger_router,
        prefix="/api/ledger",
        tags=["ledger"],
    )

    # -------------------------
    # WITHDRAW
    # -------------------------
    # POST /api/withdraw/request
    # POST /api/withdraw/confirm
    app.include_router(
        withdraw_router,
        prefix="/api/withdraw",
        tags=["withdraw"],
    )

    # -------------------------
    # SECURITY / SESSIONS
    # -------------------------
    # GET  /api/security/logins
    # GET  /api/security/sessions
    # POST /api/security/sessions/revoke
    app.include_router(
        security_router,
        prefix="/api/security",
        tags=["security"],
    )

    # -------------------------
    # AUDIT
    # -------------------------
    # GET /api/audit/proof?leaf=HASH
    # GET /api/audit/attestation
    app.include_router(
        audit_router,
        prefix="/api/audit",
        tags=["audit"],
    )

    # -------------------------
    # STATUS / PAIRS
    # -------------------------
    # GET /api/status
    # GET /api/pairs
    app.include_router(
        status_router,
        prefix="/api",
        tags=["status"],
    )

    app.include_router(
        pairs_router,
        prefix="/api",
        tags=["pairs"],
    )

    # -------------------------
    # STREAMS
    # -------------------------
    # GET /api/stream/glyphs
    app.include_router(
        stream_router,
        prefix="/api/stream",
        tags=["stream"],
    )

    # -------------------------
    # ADMIN
    # -------------------------
    # GET  /api/admin/security/logins
    # GET  /api/admin/ledger
    # POST /api/admin/kill-switch
    # POST /api/admin/reset
    app.include_router(
        admin_router,
        prefix="/api/admin",
        tags=["admin"],
    )

    # -------------------------
    # INTERNAL TRADE CONTROL
    # -------------------------
    # POST /trade/run
    app.include_router(
        trade_router,
        prefix="/trade",
        tags=["trade"],
  )
