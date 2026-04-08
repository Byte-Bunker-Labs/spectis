"""WebSocket endpoint for real-time dashboard feed.

Clients connect to /ws/feed and receive JSON messages for every audit event.
The broadcast is done via an in-memory set of connected clients.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])

# Connected WebSocket clients
_clients: set[WebSocket] = set()


async def broadcast_event(event: dict) -> None:
    """Send an event to all connected WebSocket clients."""
    if not _clients:
        return

    # Make JSON-serializable
    serializable = {}
    for k, v in event.items():
        if isinstance(v, uuid.UUID):
            serializable[k] = str(v)
        elif isinstance(v, datetime):
            serializable[k] = v.isoformat()
        else:
            serializable[k] = v

    message = json.dumps(serializable)
    disconnected = set()

    for client in _clients.copy():
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)

    _clients.difference_update(disconnected)


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            # Keep connection alive; ignore client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
