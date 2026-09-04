"""WebSocket Connection Manager for Notifications."""

import asyncio
import logging
from typing import Dict, Optional, Union
from fastapi import WebSocket, status, WebSocketDisconnect

from app.common.events.schemas import (
    NotificationInAppPushEvent,
    NotificationMulticastPushEvent,
)

logger = logging.getLogger(__name__)


class NotificationWebSocketManager:
    """
    Manager for real-time WebSocket connections mapped to user IDs.

    Maintains a 1-to-1 mapping from user_id (int) to active WebSocket connection.
    Listens to the application event bus and forwards real-time notification
    events directly to connected users.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """
        Accept an incoming WebSocket connection for a given user.
        If a connection already exists for user_id, close the old connection gracefully.
        """
        await websocket.accept()

        async with self._lock:
            existing_ws = self.active_connections.get(user_id)
            if existing_ws is not None and existing_ws != websocket:
                try:
                    await existing_ws.close(
                        code=status.WS_1000_NORMAL_CLOSURE,
                        reason="Replaced by a new connection from user",
                    )
                except Exception as e:
                    logger.warning(
                        f"Error closing existing WebSocket for user {user_id}: {e}"
                    )

            self.active_connections[user_id] = websocket

        logger.info(f"WebSocket connected for user {user_id}")

    async def disconnect(
        self, user_id: int, websocket: Optional[WebSocket] = None
    ) -> None:
        """
        Remove a user's WebSocket connection from active connections.
        If a specific websocket is provided, only remove if it matches current connection.
        """
        async with self._lock:
            current_ws = self.active_connections.get(user_id)
            if current_ws is not None:
                if websocket is None or current_ws == websocket:
                    self.active_connections.pop(user_id, None)
                    logger.info(f"WebSocket disconnected for user {user_id}")

    async def send(self, user_id: int, message: Union[dict, str]) -> bool:
        """
        Send a message (dict or str) to a specific user's WebSocket connection.

        Returns True if sent successfully, False otherwise.
        Automatically cleans up connection if sending fails due to socket closure.
        """
        websocket = self.active_connections.get(user_id)
        if not websocket:
            return False

        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
            return True
        except (WebSocketDisconnect, RuntimeError, ConnectionResetError, OSError) as e:
            logger.warning(
                f"Failed to send WebSocket message to user {user_id}, disconnecting: {e}"
            )
            await self.disconnect(user_id, websocket)
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending WebSocket message to user {user_id}: {e}"
            )
            await self.disconnect(user_id, websocket)
            return False

    async def broadcast(self, message: Union[dict, str]) -> None:
        """
        Broadcast a message to all connected WebSocket clients.
        """
        async with self._lock:
            connections_snapshot = list(self.active_connections.items())

        for user_id, websocket in connections_snapshot:
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                else:
                    await websocket.send_text(str(message))
            except Exception as e:
                logger.warning(
                    f"Error broadcasting to user {user_id}, cleaning up socket: {e}"
                )
                await self.disconnect(user_id, websocket)

    async def handle_in_app_push_event(
        self, event: NotificationInAppPushEvent
    ) -> None:
        """
        Event handler triggered when a NotificationInAppPushEvent is published to event_bus.
        Forwards the notification to the target user if connected.
        """
        if not event.user_id:
            return

        user_id = int(event.user_id)
        if user_id not in self.active_connections:
            return

        payload = {
            "id": event.notification_id,
            "title": event.title,
            "message": event.message,
            "type": event.type or "info",
            "in_app_event": (
                event.in_app_event.value
                if hasattr(event.in_app_event, "value")
                else event.in_app_event
            ),
            "data": event.data or {},
            "created_at": event.created_at,
        }

        sent = await self.send(user_id, payload)
        if sent:
            logger.debug(
                f"Forwarded notification event {event.notification_id} to user {user_id} via WS"
            )

    async def handle_multicast_push_event(
        self, event: NotificationMulticastPushEvent
    ) -> None:
        """
        Event handler triggered when a NotificationMulticastPushEvent is published to event_bus.
        Forwards the notification to each connected user in user_ids.
        """
        if not event.user_ids:
            return

        payload = {
            "title": event.title,
            "message": event.message,
            "type": event.type or "info",
            "data": event.data or {},
        }

        for uid in event.user_ids:
            user_id = int(uid)
            if user_id in self.active_connections:
                await self.send(user_id, payload)


# Global instance of WebSocket Manager
notification_ws_manager = NotificationWebSocketManager()
