"""WebSocket manager for real-time notifications."""

import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages active WebSocket connections per tenant."""

    def __init__(self):
        # {tenant_id: {user_id: [websocket, ...]}}
        self._connections: dict[str, dict[str, list[WebSocket]]] = {}

    async def connect(self, ws: WebSocket, tenant_id: str, user_id: str):
        await ws.accept()
        self._connections.setdefault(tenant_id, {}).setdefault(user_id, []).append(ws)
        logger.info("ws_connected", tenant_id=tenant_id, user_id=user_id)

    def disconnect(self, ws: WebSocket, tenant_id: str, user_id: str):
        conns = self._connections.get(tenant_id, {}).get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("ws_disconnected", tenant_id=tenant_id, user_id=user_id)

    async def send_to_tenant(self, tenant_id: str, event: dict):
        """Broadcast to all users of a tenant."""
        users = self._connections.get(tenant_id, {})
        dead = []
        for user_id, conns in users.items():
            for ws in conns:
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            self.disconnect(ws, tenant_id, user_id)

    async def send_to_user(self, tenant_id: str, user_id: str, event: dict):
        """Send to a specific user."""
        conns = self._connections.get(tenant_id, {}).get(user_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, tenant_id, user_id)


    async def broadcast(self, event: dict) -> int:
        """Broadcast to ALL connected users across ALL tenants."""
        sent = 0
        dead = []
        for tenant_id, users in self._connections.items():
            for user_id, conns in users.items():
                for ws in conns:
                    try:
                        await ws.send_json(event)
                        sent += 1
                    except Exception:
                        dead.append((tenant_id, user_id, ws))
        for tenant_id, user_id, ws in dead:
            self.disconnect(ws, tenant_id, user_id)
        return sent

    def active_connections_count(self) -> dict:
        """Return stats about active connections."""
        total = 0
        per_tenant = {}
        for tenant_id, users in self._connections.items():
            count = sum(len(conns) for conns in users.values())
            per_tenant[tenant_id] = count
            total += count
        return {"total": total, "per_tenant": per_tenant}


ws_manager = ConnectionManager()


async def notify(tenant_id: str, event_type: str, data: dict, user_id: str | None = None):
    """Send a notification to a tenant (or specific user).

    event_type: "new_message", "post_published", "approval_needed", "escalation", etc.
    """
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if user_id:
        await ws_manager.send_to_user(tenant_id, user_id, event)
    else:
        await ws_manager.send_to_tenant(tenant_id, event)
