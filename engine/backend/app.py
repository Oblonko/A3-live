"""
Bidimention A-3 — Backend Application Root

This module defines the FastAPI application instance and
global concerns ONLY.

Responsibilities:
- App initialization
- Middleware
- Global error handling
- Health & lifecycle hooks
- Route registration

This file MUST NOT:
- Execute trades
- Call exchange APIs
- Manage private keys
- Contain business logic
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# =====================================================
# INTERNAL IMPORTS
# =====================================================

from backend.routes import register_routes
from core.engine_state import engine_state
from logging.cloudwatch import get_logger

# =====================================================
# ENV / CONFIG
# =====================================================

APP_NAME = "Bidimention A-3 API"
APP_VERSION = "1.0.0"

ENV = os.getenv("ENV", "production")

ALLOWED_ORIGINS = [
    "https://bidimention.com",
    "https://app.bidimention.com",
    "http://localhost:3000",
]

# =====================================================
# LOGGER
# =====================================================

logger = get_logger("backend.app")

# =====================================================
# FASTAPI INIT
# =====================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    docs_url="/docs" if ENV != "production" else None,
    redoc_url=None,
)

# =====================================================
# MIDDLEWARE
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# GLOBAL ERROR HANDLER
# =====================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )

# =====================================================
# HEALTH / STATUS
# =====================================================

@app.get("/health", tags=["system"])
def health() -> Dict[str, Any]:
    """
    Lightweight health endpoint.
    Used for:
    - Load balancers
    - Uptime checks
    - CI smoke tests
    """
    return {
        "status": "ok",
        "service": "bidimention-backend",
        "engine": engine_state.status(),
        "env": ENV,
        "time": int(time.time()),
    }

# =====================================================
# ROUTES REGISTRATION
# =====================================================

register_routes(app)

# =====================================================
# STARTUP / SHUTDOWN
# =====================================================

@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "Backend startup complete",
        extra={
            "env": ENV,
            "version": APP_VERSION,
        },
    )

@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("Backend shutdown initiated")
