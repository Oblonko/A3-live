"""
Gate.io Spot WebSocket Execution Listener
-----------------------------------------

- Spot-only
- Read-only (no trading decisions)
- Deterministic reconciliation into A-3 engine
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Dict, Any

from engine.exchange.gateio.websocket import GateIOWebSocketClient
from engine.exchange.gateio.exceptions import GateIOWSException

from engine.core.event_bus import emit_glyph
from engine.core.orders import record_order
from engine.core.ledger import append_ledger_event

log = logging.getLogger("a3.gateio_ws")


class GateIOExecutionWS:
    """
    Listens to Gate.io spot WS and forwards
    execution events into the A-3 engine.
    """

    def __init__(self, uid: str):
        self.uid = uid
        self.ws = GateIOWebSocketClient(
            on_message=self._on_message,
            on_error=self._on_error,
        )

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    def start(self):
        log.info("Starting Gate.io WS execution listener", extra={"uid": self.uid})
        thread = threading.Thread(target=self.ws.run, daemon=True)
        thread.start()

    def stop(self):
        log.info("Stopping Gate.io WS execution listener", extra={"uid": self.uid})
        self.ws.close()

    # -------------------------------------------------
    # WebSocket handlers
    # -------------------------------------------------

    def _on_error(self, error: Exception):
        log.error("Gate.io WS error", exc_info=error)

    def _on_message(self, raw: str):
        """
        Entry point for all WS messages.
        """
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Invalid JSON from Gate.io WS")
            return

        if msg.get("channel") == "spot.usertrades":
            self._handle_trade(msg)

        elif msg.get("channel") == "spot.orders":
            self._handle_order(msg)

    # -------------------------------------------------
    # Trade events (fills)
    # -------------------------------------------------

    def _handle_trade(self, msg: Dict[str, Any]):
        """
        Handles actual fills (authoritative).
        """
        for trade in msg.get("result", []):
            pair = trade["currency_pair"].replace("_", "/")
            order_id = trade["order_id"]
            side = trade["side"]          # buy / sell
            qty = float(trade["amount"])
            price = float(trade["price"])
            ts = trade["create_time_ms"]

            # ---- Record order execution (DynamoDB) ----
            record_order(
                order_id=order_id,
                uid=self.uid,
                pair=pair,
                side=side,
                qty=qty,
                price=price,
                status="filled",
            )

            # ---- Ledger impact (spot rules) ----
            if side == "buy":
                append_ledger_event(
                    uid=self.uid,
                    event_type="ENTRY_ALLOC",
                    amount=-(qty * price),
                    reference=f"ORDER#{order_id}",
                )

            elif side == "sell":
                append_ledger_event(
                    uid=self.uid,
                    event_type="TP_FILL",
                    amount=(qty * price),
                    reference=f"ORDER#{order_id}",
                )

            # ---- Emit glyph (engine decides TP index) ----
            emit_glyph(
                {
                    "uid": self.uid,
                    "pair": pair,
                    "trade_id": order_id,
                    "g": "G_TP_EXEC",  # engine resolves to G_TP_i / G_P_i_j
                    "t": ts,
                }
            )

    # -------------------------------------------------
    # Order lifecycle events
    # -------------------------------------------------

    def _handle_order(self, msg: Dict[str, Any]):
        """
        Handles order status changes (open, canceled, done).
        """
        for order in msg.get("result", []):
            order_id = order["id"]
            status = order["status"]
            pair = order["currency_pair"].replace("_", "/")

            record_order(
                order_id=order_id,
                uid=self.uid,
                pair=pair,
                side=order["side"],
                qty=float(order["amount"]),
                price=float(order["price"]),
                status=status,
      )
