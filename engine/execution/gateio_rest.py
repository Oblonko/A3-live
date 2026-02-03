from __future__ import annotations

import os
import time
import hmac
import json
import hashlib
import logging
import requests
from typing import Dict, Any

log = logging.getLogger("a3.gateio.rest")

# ============================================================
# CONFIG
# ============================================================

GATE_API_KEY = os.getenv("GATE_API_KEY")
GATE_API_SECRET = os.getenv("GATE_API_SECRET")

if not GATE_API_KEY or not GATE_API_SECRET:
    raise RuntimeError("GATE_API_KEY and GATE_API_SECRET must be set")

BASE_URL = "https://api.gateio.ws/api/v4"

# Spot endpoints only
SPOT_ORDERS = "/spot/orders"
SPOT_ACCOUNTS = "/spot/accounts"

TIMEOUT = 10  # seconds


# ============================================================
# AUTH SIGNING (NO PASSPHRASE)
# ============================================================

def _sign(method: str, path: str, query: str, body: str, ts: str) -> Dict[str, str]:
    """
    Gate.io v4 signing — key + secret ONLY
    """
    payload = "\n".join([method, path, query, body, ts])
    signature = hmac.new(
        GATE_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha512,
    ).hexdigest()

    return {
        "KEY": GATE_API_KEY,
        "Timestamp": ts,
        "SIGN": signature,
    }


def _headers(method: str, path: str, query: str = "", body: str = "") -> Dict[str, str]:
    ts = str(int(time.time()))
    signed = _sign(method, path, query, body, ts)
    return {
        **signed,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ============================================================
# LOW-LEVEL REQUEST
# ============================================================

def _request(
    method: str,
    path: str,
    query: str = "",
    body: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    url = BASE_URL + path
    body_json = json.dumps(body) if body else ""
    headers = _headers(method, path, query, body_json)

    resp = requests.request(
        method=method,
        url=url,
        params=query if query else None,
        data=body_json,
        headers=headers,
        timeout=TIMEOUT,
    )

    if resp.status_code >= 300:
        log.error("Gate.io REST error", extra={
            "status": resp.status_code,
            "body": resp.text,
            "path": path,
        })
        raise RuntimeError(f"Gate.io REST error {resp.status_code}: {resp.text}")

    return resp.json()


# ============================================================
# SPOT EXECUTION API (ENGINE-FACING)
# ============================================================

class GateIOSpotREST:
    """
    Deterministic SPOT execution adapter.
    No retries. No state. No futures.
    """

    # ------------------------
    # Balances
    # ------------------------

    def get_balances(self) -> Dict[str, float]:
        """
        Returns free balances only.
        """
        data = _request("GET", SPOT_ACCOUNTS)
        balances = {}
        for row in data:
            balances[row["currency"]] = float(row["available"])
        return balances

    # ------------------------
    # Market Buy (USDT → Asset)
    # ------------------------

    def market_buy(self, pair: str, usdt_amount: float) -> str:
        """
        Place a spot market BUY using quote currency (USDT).

        Returns: order_id
        """
        symbol = pair.replace("/", "_")

        body = {
            "currency_pair": symbol,
            "type": "market",
            "side": "buy",
            "amount": str(usdt_amount),  # quote amount
            "account": "spot",
            "time_in_force": "ioc",
        }

        resp = _request("POST", SPOT_ORDERS, body=body)

        order_id = resp.get("id")
        if not order_id:
            raise RuntimeError("Gate.io market buy failed: no order id")

        return order_id

    # ------------------------
    # Limit Sell (TP ladder)
    # ------------------------

    def limit_sell(self, pair: str, qty: float, price: float) -> str:
        """
        Place a spot LIMIT SELL.

        Returns: order_id
        """
        symbol = pair.replace("/", "_")

        body = {
            "currency_pair": symbol,
            "type": "limit",
            "side": "sell",
            "price": str(price),
            "amount": str(qty),
            "account": "spot",
            "time_in_force": "gtc",
        }

        resp = _request("POST", SPOT_ORDERS, body=body)

        order_id = resp.get("id")
        if not order_id:
            raise RuntimeError("Gate.io limit sell failed: no order id")

        return order_id

    # ------------------------
    # Order Query (Fallback)
    # ------------------------

    def get_order(self, order_id: str, pair: str) -> Dict[str, Any]:
        """
        Read-only order query.
        Used only if WS confirmation is delayed.
        """
        symbol = pair.replace("/", "_")
        path = f"{SPOT_ORDERS}/{order_id}"
        query = f"currency_pair={symbol}"

        return _request("GET", path, query=query)
